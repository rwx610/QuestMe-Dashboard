import httpx
import time

API_KEY = "ВАШ_API_КЛЮЧ"  # лучше вынести в config.py или secrets.toml
BASE_URL = "https://toncenter.com/api/v2"

def fetch_ton_transactions(address: str, limit=100):
    """
    Получить список транзакций по адресу в TON.

    :param address: адрес контракта/кошелька в TON
    :param limit: сколько транзакций получить (максимум 100)
    :return: список транзакций (JSON)
    """
    url = f"{BASE_URL}/getTransactions"
    params = {
        "address": address,
        "limit": 100,
        "archival": True  # позволяет получить и старые транзакции
    }
    headers = {
        "X-API-Key": API_KEY
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
            else:
                print(f"Ошибка API: {data.get('error')}")
                return []
    except Exception as e:
        print(f"Ошибка при запросе транзакций: {e}")
        return []

# Пример вызова
if __name__ == "__main__":
    address = "EQCfcwvBP2cnD8UwWLKtX1pcAqEDFwFyXzuZ0seyPBdocPHu"
    txs = fetch_ton_transactions(address)
    print(f"Получено транзакций: {len(txs)}")
    for tx in txs[:3]:
        print(tx)
