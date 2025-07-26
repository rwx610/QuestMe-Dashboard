# analytics/storage.py
import os
import sqlite3
from contextlib import contextmanager
import pandas as pd
from typing import Literal, Optional
from config import DB_PATH

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
                timestamp   INTEGER,
                block       INTEGER,
                "from"      TEXT,
                "to"        TEXT,
                value       REAL,
                network     TEXT,
                contract    TEXT,
                type        TEXT,
                data        TEXT
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_net_ctr ON transactions (network, contract)"
        )
    print("SQLite ready ✨")


def get_last_block(network: str, contract: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "SELECT last_block FROM progress WHERE network=? AND contract=?",
            (network, contract),
        ).fetchone()
    return cur[0] if cur else 0


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


def query_transactions(
    network: Optional[str] = None,
    contract: Optional[str] = None,
    type_: Optional[str] = None,
    wallet: Optional[str] = None,
) -> pd.DataFrame:
    q = 'SELECT timestamp, contract, type, "from", "to", value, tx_hash FROM transactions WHERE 1=1'
    params = []
    if network:
        q += " AND network = ?"
        params.append(network)
    if contract:
        q += " AND contract = ?"
        params.append(contract)
    if type_:
        q += " AND type = ?"
        params.append(type_)
    if wallet:
        q += ' AND "from" = ? COLLATE NOCASE'
        params.append(wallet)

    with _conn() as c:
        df = pd.read_sql(q, c, params=params)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    return df


def load_transactions(network: str, contract: str, type_: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        query = """
        SELECT timestamp, type, "from", "to", value, tx_hash, data
        FROM transactions
        WHERE network = ? AND contract = ? AND type = ?
        """
        df = pd.read_sql(query, conn, params=(network, contract, type_))
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    return df


# Инициализация БД при запуске
init_db()
