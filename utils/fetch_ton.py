import time
from typing import List, Dict, Optional
import httpx
import sys


def fetch_ton_transactions(address: str, limit: int = 100, max_pages: int = 10_000) -> List[Dict]:
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




# Пример вызова
if __name__ == "__main__":
    ton_address = (
        "EQCfcwvBP2cnD8UwWLKtX1pcAqEDFwFyXzuZ0seyPBdocPHu"  # подставьте свой адрес
    )
    txs = fetch_ton_transactions(ton_address)
    print(f"\n🔹 Всего транзакций получено: {len(txs)}")

    import json

    out_file = f"ton_transactions.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(txs, f, ensure_ascii=False, indent=2, default=str)