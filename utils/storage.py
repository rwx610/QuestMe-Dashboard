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
    con.execute("PRAGMA journal_mode=WAL")   # безопаснее параллельная запись
    try:
        yield con
    finally:
        con.commit()
        con.close()


def init_db():
    with _conn() as c:
        c.execute("""
          CREATE TABLE IF NOT EXISTS tx (
            tx_hash     TEXT PRIMARY KEY,
            block_num   INTEGER,
            block_time  TIMESTAMP,
            from_addr   TEXT,
            to_addr     TEXT,
            amount      REAL,
            network     TEXT
          )""")
        c.execute("""
          CREATE TABLE IF NOT EXISTS progress (
            network   TEXT,
            contract  TEXT,
            last_blk  INTEGER,
            updated_at TIMESTAMP,
            PRIMARY KEY (network, contract)
          )""")
    print("SQLite ready ✨")
init_db()

# ---------- progress helpers ----------
def get_last_block(network: str, contract: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "SELECT last_blk FROM progress WHERE network=? AND contract=?",
            (network, contract),
        ).fetchone()
    return cur[0] if cur else 0

def set_last_block(network: str, contract: str, blk: int):
    with _conn() as c:
        c.execute("""
          INSERT INTO progress (network, contract, last_blk, updated_at)
          VALUES (?,?,?,?)
          ON CONFLICT(network,contract) DO UPDATE
              SET last_blk=excluded.last_blk,
                  updated_at=excluded.updated_at
        """, (network, contract, blk, datetime.utcnow()))


# ---------- tx upsert ----------
def upsert_tx(df: pd.DataFrame):
    if df.empty:
        return
    with _conn() as c:
        df.to_sql("tmp_tx", c, if_exists="replace", index=False)
        c.execute("""
          INSERT INTO tx
          SELECT * FROM tmp_tx
          ON CONFLICT(tx_hash) DO NOTHING
        """)
        c.execute("DROP TABLE tmp_tx")


# ---------- loaders ----------
def load_tx(network: Literal["BASE", "TON", "ALL"] = "ALL",
            contract: str | None = None) -> pd.DataFrame:
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
