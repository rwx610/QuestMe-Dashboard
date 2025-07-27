# pages/7_👥_UNIQUE_USERS_TON_EVM.py

import streamlit as st
import pandas as pd
from datetime import timedelta
from analytics.storage import query_transactions
from ui.display import metric_card, inject_card_styles, draw_chart, fill_missing_dates

# ───────────────────────────────────────── Конфигурация
PAGE_TITLE = "👥 Unique Users — TON + EVM"
BASE_COLOR = "#47A76A"
TYPES = ["reward", "0x76ebc41e", "TextComment", "resetAndSendSponsorship", "mintGem"]  # можно расширить при необходимости

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)

inject_card_styles()


# ───────────────────────────────────────── Получение и агрегация
@st.cache_data(ttl=30)
def load_data():
    df = query_transactions()
    df = df[df["type"].isin(TYPES)]
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def count_unique_wallets(df: pd.DataFrame, since: pd.Timestamp) -> int:
    return df[df["timestamp"] >= since]["from"].nunique()


df = load_data()
now = pd.Timestamp.utcnow()

# ───────────────────────────────────────── Метрики
st.markdown("### 👥 Unique Users — All Chains")

cols = st.columns(4)
metrics = {
    "DAU": count_unique_wallets(df, now - timedelta(days=1)),
    "WAU": count_unique_wallets(df, now - timedelta(days=7)),
    "MAU": count_unique_wallets(df, now - timedelta(days=30)),
    "All Time": df["from"].nunique(),
}
tooltips = {
    "DAU": "Users in the last 24h",
    "WAU": "Users in the last 7d",
    "MAU": "Users in the last 30d",
    "All Time": "Total unique users who interacted with contracts",
}

for col, (label, value) in zip(cols, metrics.items()):
    col.markdown(metric_card(label, f"{value:,}", tooltips[label]), unsafe_allow_html=True)

st.markdown("---")


# ───────────────────────────────────────── Графики
@st.cache_data(ttl=30)
@st.cache_data(ttl=30)
def get_time_series_for_UU(df: pd.DataFrame, period: str) -> pd.DataFrame:
    PERIODS = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30),
        "all": None,
    }

    df_filtered = df.copy()

    if PERIODS[period] is not None:
        cutoff = now - PERIODS[period]
        df_filtered = df_filtered[df_filtered["timestamp"] >= cutoff]

    # Назначаем период (дата без времени)
    df_filtered["period"] = df_filtered["timestamp"].dt.floor("d" if period != "daily" else "h")

    # Убираем дубликаты: один юзер в один период считается один раз
    unique_users = df_filtered.drop_duplicates(subset=["period", "from"])

    # Считаем, сколько уникальных пользователей было в каждом периоде
    grouped = (
        unique_users.groupby("period")
        .agg(users=("from", "count"))
        .reset_index()
        .sort_values("period")
    )

    result = fill_missing_dates(grouped, period)
    result["tx_count"] = result["users"]
    return result

def get_first_time_users_time_series(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["period"] = df["timestamp"].dt.floor("d")  # группировка по дням

    # Берём дату первой активности каждого пользователя
    first_seen = df.groupby("from")["period"].min().reset_index()

    # Считаем количество впервые появившихся пользователей по дням
    new_users = (
        first_seen.groupby("period")
        .size()
        .reset_index(name="tx_count")
        .sort_values("period")
    )

    return fill_missing_dates(new_users, period="all")  # можно поменять на "daily" при желании



tab_day, tab_week, tab_month, tab_all, tab_first_time = st.tabs(
    ["📅 Daily", "📅 Weekly", "📅 Monthly", "📅 All Time", "🧍 First-Time"]
)


with tab_day:
    df_day = get_time_series_for_UU(df, "daily")
    draw_chart(df_day, "📅 Daily Active Users — All Chains", BASE_COLOR, x_format="%H:%M")

with tab_week:
    df_week = get_time_series_for_UU(df, "weekly")
    draw_chart(df_week, "📅 Weekly Active Users — All Chains", BASE_COLOR, x_format="%b %d")

with tab_month:
    df_month = get_time_series_for_UU(df, "monthly")
    draw_chart(df_month, "📅 Monthly Active Users — All Chains", BASE_COLOR, x_format="%b %d")

with tab_all:
    df_all = get_time_series_for_UU(df, "all")
    draw_chart(df_all, "📅 All Time Unique Users", BASE_COLOR, x_format="%b %d")

with tab_first_time:
    df_first = get_first_time_users_time_series(df)
    draw_chart(df_first, "🧍 First-Time Unique Users", BASE_COLOR, x_format="%b %d")


st.markdown("---")
