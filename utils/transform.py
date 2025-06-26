import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "data/tx.sqlite"

def _load_data(network: str, contract: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        query = """
        SELECT timestamp, from_address, to_address, value, tx_hash
        FROM transactions
        WHERE network = ? AND contract_address = ?
        """
        df = pd.read_sql(query, conn, params=(network, contract))
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    return df


def get_metrics(network: str, contract: str) -> dict:
    df = _load_data(network, contract)
    now = datetime.utcnow()

    total_mint_volume = len(df)
    unique_wallets = df['from_address'].nunique()

    daily = df[df['timestamp'] >= now - timedelta(days=1)]
    weekly = df[df['timestamp'] >= now - timedelta(days=7)]
    monthly = df[df['timestamp'] >= now - timedelta(days=30)]

    return {
        "total_mint_volume": total_mint_volume,
        "unique_wallets_all_time": unique_wallets,

        "mint_volume_day": len(daily),
        "mint_volume_week": len(weekly),
        "mint_volume_month": len(monthly),

        "DAU": daily['from_address'].nunique(),
        "WAU": weekly['from_address'].nunique(),
        "MAU": monthly['from_address'].nunique(),
    }


def get_time_series(network: str, contract: str, period: str = 'daily') -> pd.DataFrame:
    df = _load_data(network, contract)

    if period == "daily":
        df['period'] = df['timestamp'].dt.date
    elif period == "weekly":
        df['period'] = df['timestamp'].dt.to_period('W').apply(lambda r: r.start_time)
    elif period == "monthly":
        df['period'] = df['timestamp'].dt.to_period('M').apply(lambda r: r.start_time)
    else:
        raise ValueError("Invalid period. Use daily / weekly / monthly.")

    result = df.groupby('period').agg(
        tx_count=('tx_hash', 'count'),
        unique_wallets=('from_address', 'nunique')
    ).reset_index()

    return result


def get_wallet_stats(network: str, contract: str, wallet: str) -> dict:
    df = _load_data(network, contract)
    wallet_df = df[df['from_address'].str.lower() == wallet.lower()]
    return {
        "tx_count": len(wallet_df),
        "total_value": wallet_df['value'].sum(),
        "last_tx": wallet_df['timestamp'].max() if not wallet_df.empty else None,
    }
