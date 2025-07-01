from apscheduler.schedulers.background import BackgroundScheduler
from utils.storage import get_last_block, set_last_block, upsert_tx
from utils.fetch_base import fetch_logs
from utils.fetch_ton import fetch_ton_transactions
from utils.transform import transform_raw_base, transform_raw_ton
from web3 import Web3
import sys

from utils.contracts import Contracts

# Список отслеживаемых адресов
BASE_CONTRACTS = {
    "GemMinter": "0x1f735280C83f13c6D40aA2eF213eb507CB4c1eC7",  # Пример адреса
    # можно добавить ещё
}
TON_CONTRACTS = {
    "GemMinter": "UQCn9hCC6tNykDqZisfJvwrE9RQNPalV8VArNWrmI_REtoHz",
    # можно добавить ещё
}

# Web3-провайдер для BASE
w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))  # заменишь на свой


def update_base_data():
    for name, addr in BASE_CONTRACTS.items():
        try:
            last = get_last_block("BASE", addr)
            head = w3.eth.block_number
            if last >= head:
                continue
            logs = fetch_logs(chainid=Contracts.base.chain_id, address=addr, from_block=31343717)
            df = transform_raw_base(logs, addr)  # addr передай, если нужно фильтровать
            print("TRANSFORM", len(df), df.head(1))
            upsert_tx(df)
            set_last_block("BASE", addr, head)
            print(f"[BASE] Updated {name}: {len(df)} tx")
        except Exception as e:
            print(f"[BASE] Error updating {name}: {e}")


def update_ton_data():
    print(f"[TON] update_ton_data")
    for name, addr in TON_CONTRACTS.items():
        try:
            txs = fetch_ton_transactions(addr)
            df = transform_raw_ton(txs, addr)
            print("TRANSFORM", len(df), df.head(1), file=sys.stderr)
            upsert_tx(df)
            if not df.empty:
                new_max = df["block"].max()
                print(f"[NEW_MAX] {new_max}")
                set_last_block("TON", addr, new_max)
            print(f"[TON] Updated {name}: {len(df)} tx")
        except Exception as e:
            print(f"[TON] Error updating {name}: {e}")


def start():
    scheduler = BackgroundScheduler()

    scheduler.add_job(update_base_data, "interval", minutes=1)
    scheduler.add_job(update_ton_data, "interval", minutes=1)

    # выполняем первую синхронную итерацию
    update_base_data()
    update_ton_data()

    scheduler.start()
    print("[Scheduler] First run done, subsequent runs every 1 minute")
