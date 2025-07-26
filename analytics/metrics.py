from typing import Optional, Sequence
import pandas as pd
from datetime import datetime

from .storage import query_transactions


def load_df(network: str, contract: str, type_: Optional[str] = None, wallet: Optional[str] = None) -> pd.DataFrame:
    return query_transactions(network=network, contract=contract, type_=type_, wallet=wallet)


def filter_timeframe(df: pd.DataFrame, seconds: int) -> pd.DataFrame:
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(seconds=seconds)
    return df[df["timestamp"] >= cutoff]


def get_metrics(
    network: str,
    contract: str,
    type_: Optional[str] = None,
    wallet: Optional[str] = None,
) -> dict:
    df = query_transactions(network, contract, type_, wallet)

    if df.empty:
        return {
            "unique_wallets": 0,
            "dau": 0,
            "wau": 0,
            "mau": 0,
            "total_tx_count": 0,
            "tx_day": 0,
            "tx_week": 0,
            "tx_month": 0,
            "total_volume": 0.0,
            "volume_day": 0.0,
            "volume_week": 0.0,
            "volume_month": 0.0,
        }

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)

    # Временные окна
    daily = filter_timeframe(df, 86400)
    weekly = filter_timeframe(df, 86400 * 7)
    monthly = filter_timeframe(df, 86400 * 30)

    return {
        "unique_wallets": df["from"].nunique(),
        "dau": daily["from"].nunique(),
        "wau": weekly["from"].nunique(),
        "mau": monthly["from"].nunique(),
        "total_tx_count": len(df),
        "tx_day": len(daily),
        "tx_week": len(weekly),
        "tx_month": len(monthly),
        "total_volume": df["value"].sum(),
        "volume_day": daily["value"].sum(),
        "volume_week": weekly["value"].sum(),
        "volume_month": monthly["value"].sum(),
    }


def get_time_series(
    network: str,
    contract: str,
    type_: Optional[str] = None,
    period: str = "daily",
) -> pd.DataFrame:
    PERIODS_IN_SECONDS = {
        "daily": 86400,
        "weekly": 86400 * 7,
        "monthly": 86400 * 30,
        "all": None,
    }

    if period not in PERIODS_IN_SECONDS:
        raise ValueError(f"Invalid period: {period}")

    df = load_df(network, contract, type_)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    seconds = PERIODS_IN_SECONDS[period]
    if seconds is not None:
        df = filter_timeframe(df, seconds)

    df["period"] = df["timestamp"].dt.floor("h" if period == "daily" else "d")

    return (
        df.groupby("period")
        .agg(
            tx_count=("tx_hash", "count"),
            unique_wallets=("from", "nunique"),
            amount=("value", "sum"),
        )
        .reset_index()
        .sort_values("period")
    )


def get_wallet_rewards(
    wallet: str,
    contracts: Optional[Sequence[str]] = None,
    types: Optional[Sequence[str]] = None,
) -> dict:
    wallet = wallet.lower()
    
    # Получаем все транзакции для указанного кошелька
    df = query_transactions(wallet=wallet)

    if df.empty:
        return {
            "tx_count": 0,
            "total_value": 0.0,
            "last_tx": None
        }

    # Приводим к нижнему регистру, если столбцы существуют
    if "contract" in df.columns:
        df["contract"] = df["contract"].str.lower()
    if "type" in df.columns:
        df["type"] = df["type"].str.lower()

    # Фильтрация по контрактам
    if contracts:
        contracts = [c.lower() for c in contracts]
        df = df[df["contract"].isin(contracts)]

    # Фильтрация по типам
    if types:
        types = [t.lower() for t in types]
        df = df[df["type"].isin(types)]

    if df.empty:
        return {
            "tx_count": 0,
            "total_value": 0.0,
            "last_tx": None
        }

    return {
        "tx_count": len(df),
        "total_value": df["value"].sum(),
        "last_tx": df["timestamp"].max().isoformat()
    }


def get_total_amount(
    contract: str,
    type_: str,
    network: Optional[str] = None,
) -> float:
    if network is None:
        network = "BASE" if contract.lower().startswith("0x") else "TON"

    df = query_transactions(network=network, contract=contract, type_=type_)
    if df.empty:
        return 0.0

    return round(df["value"].sum(), 4)
