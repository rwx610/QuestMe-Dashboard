from web3 import Web3
import requests
from typing import List, Dict, Union
import streamlit as st


RPC_URL = "https://base-rpc.publicnode.com"  # твой RPC URL
MAX_BLOCK_RANGE = 50000


w3 = Web3(Web3.HTTPProvider(RPC_URL))


def fetch_base_transactions_rpc(address: str, from_block: int, to_block: int):
    all_logs = []
    current_from = from_block
    while current_from <= to_block:
        current_to = min(current_from + MAX_BLOCK_RANGE - 1, to_block)
        print(f"Запрашиваю блоки с {current_from} по {current_to}")

        try:
            logs = w3.eth.get_logs(
                {
                    "fromBlock": current_from,
                    "toBlock": current_to,
                    "address": Web3.to_checksum_address(address),
                }
            )
            all_logs.extend(logs)
        except Exception as e:
            print(f"Ошибка RPC запроса: {e}")
            break

        current_from = current_to + 1

    return all_logs


def fetch_logs(
    chainid: int,
    address: str,
    from_block: Union[int, str] = 0,
    to_block: Union[int, str] = "latest",
    apikey: str = st.secrets['etherscan']['key'],
    offset: int = 1000,
    timeout: int = 20,
    
) -> List[Dict]:

    base_url = "https://api.etherscan.io/v2/api"
    page = 1
    all_logs = []

    while True:
        params = {
            "chainid": chainid,
            "module": "logs",
            "action": "getLogs",
            "address": address,
            "fromBlock": from_block,
            "toBlock": to_block,
            "page": page,
            "offset": offset,
            "apikey": apikey,
        }
        response = requests.get(base_url, params=params, timeout=timeout)
        response.raise_for_status()

        payload = response.json()

        logs = payload.get("result", []) if payload.get("status") == "1" else []

        all_logs.extend(logs)

        if len(logs) < offset:
            break
        page += 1

    return all_logs


import time
import requests
from typing import Optional, Literal


def get_block_by_time(
    chainid: int,
    apikey: str,
    timestamp: Optional[int] = None,
    closest: Literal["before", "after"] = "before",
    timeout: int = 10,
) -> int:

    if timestamp is None:
        timestamp = int(time.time())

    base_url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": chainid,
        "module": "block",
        "action": "getblocknobytime",
        "timestamp": timestamp,
        "closest": closest,
        "apikey": apikey,
    }

    resp = requests.get(base_url, params=params, timeout=timeout)
    resp.raise_for_status()  # 4xx/5xx → исключение

    payload = resp.json()
    if payload.get("status") != "1":
        raise RuntimeError(
            f"Etherscan error: status={payload.get('status')}, "
            f"message={payload.get('message')}"
        )

    return int(payload["result"])


if __name__ == "__main__":
    import streamlit as st
    chainid = 8453
    address = "0x252683e292d7E36977de92a6BF779d6Bc35176D4"  # адрес контракта BASE
    apikey = st.secrets['etherscan']['key']


    from_block = 31343717


    logs = fetch_logs(chainid=chainid, address=address, apikey=apikey, from_block=from_block)

    print(f"Найдено логов: {len(logs)}")
    for log in logs:
        print(log)
