from eth_account import Account

from .db import db
from config import *
from utils.utils import *
from core.user_agent_provider import UserAgentProvider
from core.key_manager import cipher


def create_db():
    ua = UserAgentProvider()

    accounts = read_csv(ACCOUNTS_FILE)

    used_proxies = set(
        db.get_many("data", column_name="proxy")
        + db.get_many("dead_proxy", column_name="proxy")
    )

    proxies = [
        proxy
        for sublist in read_csv(PROXIES_FILE, has_header=False)
        for proxy in sublist
        if proxy not in used_proxies
    ]

    for account in accounts:
        address = Account.from_key(account["key"]).address

        if not db.get("keys", {"address": address}):
            encrypted_key = cipher.encrypt(account["key"].encode()).decode()
            db.insert(
                "keys",
                {
                    "address": address,
                    "key": encrypted_key,
                },
            )

        if not db.get("data", {"address": address}):
            data = {
                "id": account["id"],
                "address": address,
                "headers": ua.get_ua(),
                "proxy": proxies.pop() if proxies else "",
            }
            db.insert("data", data)

        elif proxies:
            # Если адрес есть, но нет прокси — назначаем свободный
            record = db.get("data", {"address": address})
            if not record.proxy:
                db.update("data", {"address": address}, {"proxy": proxies.pop()})

        # Добавляем в task или перезаписываем при флаге OVERWRITE_TASK
        if OVERWRITE_TASK or not db.get(TASK_TABLE, {"address": address}):
            task = {
                "address": address,
                "total": random.randint(*TASK_TOTAL),
                "faucet": 0,
                "deposit": 0,
                "completed": False,
            }
            if db.get(TASK_TABLE, {"address": address}):
                db.update(TASK_TABLE, {"address": address}, task)
            else:
                db.insert(TASK_TABLE, task)

    if proxies:
        open_proxy = set(db.get_many("open_proxy", column_name="proxy") + proxies)
        db.delete("open_proxy")
        db.insert_many("open_proxy", open_proxy)

    db.export()
