import sys
import time
import httpx
import requests
from typing import List, Dict, Union, Optional


def fetch_base_transactions(
    chainid: int,
    address: str,
    from_block: Union[int, str] = 0,
    to_block: Union[int, str] = "latest",
    apikey: str = None,
    offset: int = 1000,
    timeout: int = 20,
    sort: str = "asc",
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


def fetch_ton_transactions(
    address: str, limit: int = 100, max_pages: int = 10_000
) -> List[Dict]:
    BASE_URL = "https://toncenter.com/api/v2/getTransactions"
    all_txs: List[Dict] = []
    from_lt: Optional[str] = None
    from_hash: Optional[str] = None
    seen_lts = set()
    page = 0

    try:
        with httpx.Client(timeout=15) as client:
            while page < max_pages:
                params = {
                    "address": address,
                    "limit": limit,
                    "archival": True,
                }
                if from_lt and from_hash:
                    params["lt"] = from_lt
                    params["hash"] = from_hash

                try:
                    resp = client.get(BASE_URL, params=params)

                    if resp.status_code == 429:
                        time.sleep(5)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    print(f"Request error: {e}", file=sys.stderr)
                    break

                if not data.get("ok"):
                    print(f"API error: {data.get('error')}", file=sys.stderr)
                    break

                txs = data.get("result", [])
                if not txs:
                    break

                new_txs = []
                for tx in txs:
                    lt = tx["transaction_id"]["lt"]
                    if lt not in seen_lts:
                        seen_lts.add(lt)
                        new_txs.append(tx)

                if not new_txs:
                    break

                all_txs.extend(new_txs)

                last_tx = txs[-1]["transaction_id"]
                from_lt = last_tx["lt"]
                from_hash = last_tx["hash"]
                page += 1

                time.sleep(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)

    return all_txs
