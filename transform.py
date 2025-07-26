# transform.py
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import base64, struct
from tonsdk.boc import Cell

from config import CONTRACTS


DB_PATH = "data/tx.sqlite"


def _load_data(network: str, contract: str, type_: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        query = """
        SELECT 
            timestamp, 
            type, 
            "from", 
            "to", 
            value, 
            tx_hash
        FROM transactions
        WHERE network = ? AND contract = ? AND type = ?
        """
        df = pd.read_sql(query, conn, params=(network, contract, type_))
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    return df


def get_metrics(network: str, contract: str, type_) -> dict:
    df = _load_data(network, contract, type_)
    now = datetime.utcnow()

    total_mint_volume = len(df)
    unique_wallets = df["from"].nunique()

    daily = df[df["timestamp"] >= now - timedelta(days=1)]
    weekly = df[df["timestamp"] >= now - timedelta(days=7)]
    monthly = df[df["timestamp"] >= now - timedelta(days=30)]

    return {
        "total_volume": total_mint_volume,
        "unique_wallets": unique_wallets,
        "volume_day": len(daily),
        "volume_week": len(weekly),
        "volume_month": len(monthly),
        "DAU": daily["from"].nunique(),
        "WAU": weekly["from"].nunique(),
        "MAU": monthly["from"].nunique(),
    }


def get_time_series(network: str, contract: str, type_, period: str = "daily") -> pd.DataFrame:
    df = _load_data(network, contract, type_)
    now = pd.Timestamp.now()

    if period == "daily":
        # последние 24 часа, группируем по часам
        time_ago = now - pd.Timedelta(hours=24)
        df = df[df["timestamp"] >= time_ago]
        df["period"] = df["timestamp"].dt.floor("h")

    elif period == "weekly":
        # последние 7 дней, группируем по дням
        time_ago = now - pd.Timedelta(days=7)
        df = df[df["timestamp"] >= time_ago]
        df["period"] = df["timestamp"].dt.floor("D")

    elif period == "monthly":
        # последние 30 дней, группируем по дням
        time_ago = now - pd.Timedelta(days=30)
        df = df[df["timestamp"] >= time_ago]
        df["period"] = df["timestamp"].dt.floor("D")

    elif period == "all":
        # вся история по дням
        df["period"] = df["timestamp"].dt.floor("D")

    else:
        raise ValueError("Invalid period. Use: daily, weekly, monthly, all.")

    # Группируем и агрегируем
    result = (
        df.groupby("period")
        .agg(tx_count=("tx_hash", "count"), unique_wallets=("from", "nunique"))
        .reset_index()
        .sort_values("period")  # чтобы гарантировать правильный порядок
    )

    return result





def get_wallet_stats(network: str, contract: str, wallet: str, type_) -> dict:
    df = _load_data(network, contract, type_)
    wallet_df = df[df["from"].str.lower() == wallet.lower()]
    return {
        "tx_count": len(wallet_df),
        "total_value": wallet_df["value"].sum(),
        "last_tx": wallet_df["timestamp"].max() if not wallet_df.empty else None,
    }


def extract_operation_type(tx: dict) -> str:
    try:
        in_msg = tx.get("in_msg") or {}
        msg_data = in_msg.get("msg_data") or {}
        data_type = msg_data.get("@type")

        if data_type == "msg.dataText":
            return "TextComment"

        if data_type == "msg.dataRaw":
            body_b64 = msg_data.get("body")
            if not body_b64:
                return "EmptyBody"

            try:
                boc = base64.b64decode(body_b64)
                cell = Cell.one_from_boc(boc)
                sl = cell.begin_parse()
                op_code_int = sl.read_uint(32)
                op_code_hex = hex(op_code_int)

                match op_code_hex:
                    case "0x0" | "0x00000000":
                        return "Transfer"
                    case _:
                        return op_code_hex
            except Exception as e:
                print(f"[Decode error] body BOC: {e}")
                return "InvalidBOC"

        return "Unknown"

    except Exception as e:
        print(f"[Main error] extract_operation_type: {e}")
        return "Unknown"


def transform_raw_base(raw_txs, contract_addr) -> pd.DataFrame:
    rows = []
    for tx in raw_txs:
        try:
            rows.append(
                {
                    "tx_hash": tx["hash"],
                    "timestamp": tx["timeStamp"],
                    "block": tx["blockNumber"],
                    "from": tx["from"],
                    "to": tx["to"],
                    "value": int(tx["value"]) / 1e18,
                    "network": "BASE",
                    "contract": contract_addr,
                    "type": tx["functionName"].split('(')[0],
                }
            )
        except Exception:
            continue
    return pd.DataFrame(rows)


def transform_raw_ton(
    raw_txs, contract_addr: str, action: str = "Received TON"
) -> pd.DataFrame:
    rows = []
    for tx in raw_txs:
        try:
            rows.append(
                {
                    "tx_hash": tx["transaction_id"]["hash"],
                    "timestamp": tx["utime"],
                    "block": int(tx["transaction_id"]["lt"]),
                    "from": tx["in_msg"]["source"],
                    "to": tx["in_msg"]["destination"],
                    "value": float(tx["in_msg"]["value"])
                    / 1e9,  # из нанотонов в TON (REAL)
                    "network": "TON",
                    "contract": contract_addr,
                    "type": extract_operation_type(tx),
                }
            )
        except Exception:
            continue
    return pd.DataFrame(rows)


def body_is_jetton_transfer(b64_body: str) -> bool:
    JETTON_OPCODE_TRANSFER = 0xF8A7EA5
    try:
        data = base64.b64decode(b64_body)
        (op,) = struct.unpack(">I", data[:4])  # big‑endian uint32
        return op == JETTON_OPCODE_TRANSFER
    except Exception:
        return False


def transform_raw_ton_withdraw(
    raw_txs, contract_addr: str, op_type: str = "withdraw"
) -> pd.DataFrame:
    rows = []
    for tx in raw_txs:
        # берём все исходящие сообщения
        for msg in tx.get("out_msgs", []):
            # 1) Jetton‑кошелёк‑source совпадает?
            if msg.get("source") != CONTRACTS["ton"]["reward"]["usdt_reward_wallet"]:
                continue
            # 2) тело содержит op‑code transfer?
            body = msg.get("msg_data", {}).get("body", "")
            if not body_is_jetton_transfer(body):
                continue

            # --- значит, это Reward Withdrawal USDT ---
            tx_id = tx["transaction_id"]
            tx_hash = tx_id["hash"]
            lt = int(tx_id["lt"])
            ts = int(tx["utime"])

            rows.append(
                {
                    "tx_hash": tx_hash,
                    "timestamp": ts,
                    "block_num": lt,
                    "from_addr": msg["source"],
                    "to_addr": msg["destination"],
                    "value": int(msg["value"]) / 1e6,  # 1 USDT = 1e6 nano‑USDT
                    "network": "TON",
                    "contract": contract_addr,
                    "type": op_type,  # 'withdraw'
                }
            )
    return pd.DataFrame(rows)
