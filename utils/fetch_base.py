from web3 import Web3
import os

RPC_URL = "https://base-rpc.publicnode.com"  # твой RPC URL
MAX_BLOCK_RANGE = 50000
LAST_BLOCK_FILE = "last_block.txt"

w3 = Web3(Web3.HTTPProvider(RPC_URL))


def save_last_processed_block(block_number):
    with open(LAST_BLOCK_FILE, "w") as f:
        f.write(str(block_number))


def fetch_base_transactions_rpc(address: str, from_block: int, to_block: int):
    all_logs = []
    current_from = from_block
    while current_from <= to_block:
        current_to = min(current_from + MAX_BLOCK_RANGE - 1, to_block)
        print(f"Запрашиваю блоки с {current_from} по {current_to}")

        try:
            logs = w3.eth.get_logs({
                'fromBlock': current_from,
                'toBlock': current_to,
                'address': Web3.to_checksum_address(address)
            })
            all_logs.extend(logs)
        except Exception as e:
            print(f"Ошибка RPC запроса: {e}")
            break

        # Сохраняем последний обработанный блок (конец текущего диапазона)
        save_last_processed_block(current_to)
        current_from = current_to + 1

    return all_logs


if __name__ == "__main__":
    address = "0x1f735280C83f13c6D40aA2eF213eb507CB4c1eC7"  # адрес контракта BASE

    # Считаем последний обработанный блок, чтобы не начинать с нуля
    last_processed = 31212443
    # Текущий последний блок в сети
    current_block = w3.eth.block_number

    print(f"Начинаем сканирование с блока {last_processed} до {current_block}")

    logs = fetch_base_transactions_rpc(address, last_processed, current_block)
    print(f"Найдено логов: {len(logs)}")
