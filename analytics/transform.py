import pandas as pd

from analytics.constants import CONTRACTS
from analytics.ton_utils import extract_operation_type, body_is_jetton_transfer
from analytics.base_utils import extract_amount_from_data


CONTRACTS_WITH_CUSTOM_VALUE = {
    "0x1f735280c83f13c6d40aa2ef213eb507cb4c1ec7": {"index": 2, "decimals": 6},
    "0x252683e292d7e36977de92a6bf779d6bc35176d4": {"index": 2, "decimals": 6},
    # добавь свои контракты сюда
}


def transform_raw_base(raw_txs, contract_addr) -> pd.DataFrame:
    rows = []
    contract_addr = contract_addr.lower()

    # если контракт требует кастомной обработки — достаём параметры
    extract_cfg = CONTRACTS_WITH_CUSTOM_VALUE.get(contract_addr, None)

    for tx in raw_txs:
        try:
            # значение по умолчанию — стандартное из поля "value"
            raw_value = int(tx["value"]) / 1e18

            

            # если нужно — заменим на извлечённое из data
            if extract_cfg:
                raw_value = extract_amount_from_data(
                    tx["input"],
                    index=extract_cfg["index"],
                    decimals=extract_cfg["decimals"]
                ) or 0.0

            rows.append(
                {
                    "tx_hash": tx["hash"],
                    "timestamp": tx["timeStamp"],
                    "block": tx["blockNumber"],
                    "from": tx["from"],
                    "to": tx["to"],
                    "value": raw_value,
                    "network": "BASE",
                    "contract": contract_addr,
                    "type": tx["functionName"].split('(')[0],
                    "data": tx["input"]
                }
            )
        except Exception:
            continue

    return pd.DataFrame(rows)


def transform_raw_ton(raw_txs, contract_addr: str) -> pd.DataFrame:
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
                    "data": tx["data"],
                }
            )
        except Exception:
            continue
    return pd.DataFrame(rows)


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
