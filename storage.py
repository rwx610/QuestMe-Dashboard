# utils/storage.py
import os, sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Literal

import pandas as pd

DB_PATH = "data/tx.sqlite"
os.makedirs("data", exist_ok=True)


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")  # безопаснее параллельная запись
    try:
        yield con
    finally:
        con.commit()
        con.close()


def init_db():
    with _conn() as c:
        c.execute(
            """
        CREATE TABLE IF NOT EXISTS transactions (
            tx_hash     TEXT PRIMARY KEY,
            timestamp   INTEGER,              -- unix-time (сек)
            block       INTEGER,
            "from"        TEXT,
            "to"          TEXT,
            value       REAL,
            network     TEXT,
            contract    TEXT,
            type        TEXT,                 -- mint | withdraw | deposit
            data        TEXT
        )"""
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_net_ctr ON transactions (network, contract)"
        )
    print("SQLite ready ✨")


init_db()


# ---------- progress helpers ----------
def get_last_block(network: str, contract: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "SELECT last_block FROM progress WHERE network=? AND contract=?",
            (network, contract),
        ).fetchone()
    return cur[0] if cur else 0



# ---------- tx upsert ----------
def upsert_tx(df: pd.DataFrame):
    if df.empty:
        return
    with _conn() as c:
        df.to_sql("tmp_tx", c, if_exists="replace", index=False)
        c.execute(
            """
          INSERT OR IGNORE INTO transactions
          SELECT * FROM tmp_tx;
        """
        )
        c.execute("DROP TABLE tmp_tx")


# ---------- loaders ----------
def load_tx(
    network: Literal["BASE", "TON", "ALL"] = "ALL", contract: str | None = None
) -> pd.DataFrame:
    q = "SELECT * FROM tx"
    params = []
    if network != "ALL":
        q += " WHERE network=?"
        params.append(network)
        if contract:
            q += " AND to_addr=?"
            params.append(contract)
    elif contract:
        q += " WHERE to_addr=?"
        params.append(contract)

    with _conn() as c:
        df = pd.read_sql(q, c, params=params)
    df["block_time"] = pd.to_datetime(df["block_time"], utc=True)
    return df
