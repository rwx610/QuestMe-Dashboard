# transform.py
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import base64, struct

from utils.contracts import CONTRACTS


DB_PATH = "data/tx.sqlite"


def _load_data(network: str, contract: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        query = """
        SELECT timestamp, "from", "to", value, tx_hash
        FROM transactions
        WHERE network = ? AND contract = ?
        """
        df = pd.read_sql(query, conn, params=(network, contract))
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    return df


def get_metrics(network: str, contract: str) -> dict:
    df = _load_data(network, contract)
    now = datetime.utcnow()

    total_mint_volume = len(df)
    unique_wallets = df["from"].nunique()

    daily = df[df["timestamp"] >= now - timedelta(days=1)]
    weekly = df[df["timestamp"] >= now - timedelta(days=7)]
    monthly = df[df["timestamp"] >= now - timedelta(days=30)]

    return {
        "total_mint_volume": total_mint_volume,
        "unique_wallets_all_time": unique_wallets,
        "mint_volume_day": len(daily),
        "mint_volume_week": len(weekly),
        "mint_volume_month": len(monthly),
        "DAU": daily["from"].nunique(),
        "WAU": weekly["from"].nunique(),
        "MAU": monthly["from"].nunique(),
    }


def get_time_series(network: str, contract: str, period: str = "daily") -> pd.DataFrame:
    df = _load_data(network, contract)

    if period == "daily":
        df["period"] = df["timestamp"].dt.date
    elif period == "weekly":
        df["period"] = df["timestamp"].dt.to_period("W").apply(lambda r: r.start_time)
    elif period == "monthly":
        df["period"] = df["timestamp"].dt.to_period("M").apply(lambda r: r.start_time)
    else:
        raise ValueError("Invalid period. Use daily / weekly / monthly.")

    result = (
        df.groupby("period")
        .agg(tx_count=("tx_hash", "count"), unique_wallets=("from", "nunique"))
        .reset_index()
    )

    return result


def get_wallet_stats(network: str, contract: str, wallet: str) -> dict:
    df = _load_data(network, contract)
    wallet_df = df[df["from"].str.lower() == wallet.lower()]
    return {
        "tx_count": len(wallet_df),
        "total_value": wallet_df["value"].sum(),
        "last_tx": wallet_df["timestamp"].max() if not wallet_df.empty else None,
    }


def transform_raw_base(
    raw_logs, contract_addr: str, op_type: str = "mint"
) -> pd.DataFrame:
    rows = []
    for lg in raw_logs:
        try:
            rows.append(
                {
                    "tx_hash": (
                        lg["transactionHash"].hex()
                        if isinstance(lg["transactionHash"], bytes)
                        else lg["transactionHash"]
                    ),
                    "timestamp": int(
                        lg["timeStamp"]
                    ),  # либо получить из блока через RPC
                    "block": int(lg["blockNumber"]),
                    "from": lg["from"],
                    "to": lg["to"],
                    "value": int(lg["value"]) / 1e18,  # ETH → единицы
                    "network": "BASE",
                    "contract": contract_addr,
                    "type": op_type,
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
                    "type": action,
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
            if msg.get("source") != CONTRACTS.ton.reward.usdt_reward_wallet:
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
