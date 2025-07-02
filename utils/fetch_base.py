import requests
from typing import List, Dict, Union
import streamlit as st


def fetch_transactions(
    chainid: int,
    address: str,
    from_block: Union[int, str] = 0,
    to_block: Union[int, str] = "latest",
    apikey: str = None,
    offset: int = 1000,
    timeout: int = 20,
    sort: str = "asc"
) -> List[Dict]:
    base_url = "https://api.etherscan.io/v2/api"
    page = 1
    all_txs = []

    while True:
        params = {
            "chainid": chainid,
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": from_block,
            "endblock": to_block,
            "page": page,
            "offset": offset,
            "sort": sort,
            "apikey": apikey,
        }

        response = requests.get(base_url, params=params, timeout=timeout)
        response.raise_for_status()

        payload = response.json()

        txs = payload.get("result", []) if payload.get("status") == "1" else []

        all_txs.extend(txs)

        if len(txs) < offset:
            break
        page += 1

    return all_txs



if __name__ == "__main__":
    import streamlit as st
    chainid = 8453
    address = "0xa69a396c45Bd525f8516a43242580c4E88BbA401"  # адрес контракта BASE
    apikey = st.secrets['etherscan']['key']

    from_block = 31343717


    logs = fetch_transactions(chainid=chainid, address=address, apikey=apikey)

    print(f"Найдено логов: {len(logs)}")
    for log in logs:
        print(log)

    import json

    out_file = f"base_transactions.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2, default=str)
