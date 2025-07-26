# pages/6_💰_ALL_REWARDS.py

import streamlit as st
import pandas as pd
from analytics.metrics import get_metrics, get_time_series, get_wallet_rewards
from ui.display import inject_card_styles, metric_card, draw_chart, fill_missing_dates

# ─────────────────────────────────────────  Конфигурация
PAGE_TITLE = "Total Rewards Withdrawn — All Chains"
BASE_COLOR = "#3a6da3"

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)

NETWORKS = {
    "BASE": {
        "contract": "0x1f735280C83f13c6D40aA2eF213eb507CB4c1eC7",
        "type": "reward",
        "symbol": "USDC"
    },
    "TON": {
        "contract": "EQCfcwvBP2cnD8UwWLKtX1pcAqEDFwFyXzuZ0seyPBdocPHu",
        "type": "0x76ebc41e",
        "symbol": "USDT"
    }
}

# ─────────────────────────────────────────  Стили
inject_card_styles()

# ─────────────────────────────────────────  Получение и агрегация метрик
@st.cache_data(ttl=30)
def _get_all_metrics():
    totals = {
        "tx_day": 0,
        "tx_week": 0,
        "tx_month": 0,
        "total_tx_count": 0,
        "total_volume": 0,
        "unique_wallets": 0
    }

    for net, data in NETWORKS.items():
        m = get_metrics(net, data["contract"], data["type"])
        totals["tx_day"] += m.get("tx_day", 0)
        totals["tx_week"] += m.get("tx_week", 0)
        totals["tx_month"] += m.get("tx_month", 0)
        totals["total_tx_count"] += m.get("total_tx_count", 0)
        totals["total_volume"] += m.get("total_volume", 0)
        totals["unique_wallets"] += m.get("unique_wallets", 0)

    return totals

metrics = _get_all_metrics()

# ─────────────────────────────────────────  Метрики
st.markdown("### 💰 Total Rewards Withdrawn (All Chains)")
cols = st.columns(4)
metric_map = [
    ("Withdraw / Day", "tx_day", "Total withdrawn in last 24h"),
    ("Withdraw / Week", "tx_week", "Total withdrawn in last 7d"),
    ("Withdraw / Month", "tx_month", "Total withdrawn in last 30d"),
    ("Total Withdrawn", "total_volume", "All-time rewards withdrawn")
]
for col, (label, key, tooltip) in zip(cols, metric_map):
    col.markdown(metric_card(label, f"${metrics[key]:,.2f}", tooltip), unsafe_allow_html=True)

# ─────────────────────────────────────────  Сводка
st.markdown("---")
st.markdown("### 👥 & 💰 Summary")

col1, col2 = st.columns(2)

col1.markdown(
    metric_card("Unique Wallets", f"{metrics['unique_wallets']:,}", "Total unique reward recipients across chains"),
    unsafe_allow_html=True
)

col2.markdown(
    metric_card("Total Withdrawn Volume", f"${metrics['total_volume']:,.2f}", "Sum of all rewards withdrawn (USDC + USDT)"),
    unsafe_allow_html=True
)

st.markdown("---")

# ─────────────────────────────────────────  Графики по периодам
@st.cache_data(ttl=30)
def _get_combined_series(period: str) -> pd.DataFrame:
    dfs = []
    for net, data in NETWORKS.items():
        df = get_time_series(net, data["contract"], data["type"], period)
        df["tx_count"] = 1  # ✅ Добавлено
        df = df[["period", "amount", "tx_count"]].rename(columns={
            "amount": f"amount_{net}",
            "tx_count": f"tx_count_{net}"
        })
        dfs.append(df.set_index("period"))

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, axis=1).fillna(0)

    df_all["amount"] = df_all[[col for col in df_all.columns if col.startswith("amount_")]].sum(axis=1)
    df_all["tx_count"] = df_all[[col for col in df_all.columns if col.startswith("tx_count_")]].sum(axis=1)

    df_all = df_all.reset_index()
    return fill_missing_dates(df_all, period)

tab_day, tab_week, tab_month, tab_all = st.tabs(["📅 Daily", "📅 Weekly", "📅 Monthly", "📅 All Time"])

with tab_day:
    df = _get_combined_series("daily")
    draw_chart(df, "💸 Total Withdrawals by Day", BASE_COLOR, x_format="%H:%M")

with tab_week:
    df = _get_combined_series("weekly")
    draw_chart(df, "📅 Total Withdrawals by Week", BASE_COLOR, x_format="%b %d")

with tab_month:
    df = _get_combined_series("monthly")
    draw_chart(df, "📅 Total Withdrawals by Month", BASE_COLOR, x_format="%b %d")

with tab_all:
    df = _get_combined_series("all")
    draw_chart(df, "📅 Total Withdrawals — All Time", BASE_COLOR, x_format="%b %Y")

st.markdown("---")

# ─────────────────────────────────────────  Поиск по кошельку
st.markdown("### 🔍 Wallet Lookup: Total Rewards Withdrawn")
wallet_input = st.text_input("Введите адрес кошелька", placeholder="Например: 0:abc...")

CONTRACTS = [
    "0x1f735280c83f13c6d40aa2ef213eb507cb4c1ec7",
    "EQCfcwvBP2cnD8UwWLKtX1pcAqEDFwFyXzuZ0seyPBdocPHu",
]
TYPES = [
    "reward",
    "0x76ebc41e",
]

if wallet_input:
    try:
        summary = get_wallet_rewards(wallet_input, CONTRACTS, TYPES)

        # Форматирование даты
        last_tx_str = summary["last_tx"]
        if last_tx_str:
            last_tx_str = pd.to_datetime(last_tx_str).strftime("%Y-%m-%d %H:%M:%S")
        else:
            last_tx_str = "Нет транзакций"

        st.subheader("📊 Статистика по кошельку")
        st.table({
            "Общая сумма вывода (TON)": [round(summary["total_value"], 4)],
            "Количество транзакций": [summary["tx_count"]],
            "Последняя транзакция": [last_tx_str],
        })

    except Exception as e:
        st.error(f"Ошибка при получении данных: {e}")