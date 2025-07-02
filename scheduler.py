from apscheduler.schedulers.background import BackgroundScheduler
from utils.storage import upsert_tx
from utils.fetch_base import fetch_transactions
from utils.fetch_ton import fetch_ton_transactions
from utils.transform import transform_raw_base, transform_raw_ton
import streamlit as st
import sys

from config import *


def update_base_data():
    print(f"[BASE] update_base_data")
    for name, data in CONTRACTS["base"].items():
        try:
            addr = data.get("address", None)
            apikey = st.secrets['etherscan']['key']
            if not addr:
                continue
            txs = fetch_transactions(chainid=BASE_CHAIN_ID, address=addr, apikey=apikey)
            df = transform_raw_base(txs, addr)  # addr передай, если нужно фильтровать
            print("TRANSFORM", len(df), df.head(1))
            upsert_tx(df)

            print(f"[BASE] Updated {name}: {len(df)} tx")
        except Exception as e:
            print(f"[BASE] Error updating {name}: {e}")


def update_ton_data():
    print(f"[TON] update_ton_data")
    for name, data in CONTRACTS["ton"].items():
        try:
            addr = data.get("address", None)
            if not addr:
                continue
            txs = fetch_ton_transactions(addr)
            df = transform_raw_ton(txs, addr)
            print("TRANSFORM", len(df), df.head(1), file=sys.stderr)
            upsert_tx(df)

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
