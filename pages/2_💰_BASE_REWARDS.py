# pages/2_💰_BASE_REWARDS.py
import streamlit as st
import pandas as pd
from analytics.metrics import get_metrics, get_time_series, get_wallet_rewards
from ui.display import inject_card_styles, metric_card, fill_missing_dates, draw_chart

# ─────────────────────────────────────────  Конфиг
NETWORK = "BASE"
CONTRACT = "0x1f735280c83f13c6d40aa2ef213eb507cb4c1ec7"
TYPE = "reward"
PAGE_TITLE = "Rewards Withdrawal — BASE"
BASE_COLOR = "#3a6da3"

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)
st.markdown(f"CONTRACT: `{CONTRACT}`")

# ─────────────────────────────────────────  Стили и метрики
inject_card_styles()

@st.cache_data(ttl=10)
def _contract_metrics(network, contract, type_):
    return get_metrics(network, contract, type_)

m = _contract_metrics(NETWORK, CONTRACT, TYPE)

# ─────────────────────────────────────────  Withdraw Volume
st.markdown("### 💸 Rewards Withdrawn (USDC)")
cols1 = st.columns(4)
metric_map = [
    ("Withdraw / Day", "volume_day", "Withdrawn in the last 24 hours"),
    ("Withdraw / Week", "volume_week", "Withdrawn in the last 7 days"),
    ("Withdraw / Month", "volume_month", "Withdrawn in the last 30 days"),
    ("Total Withdraw", "total_volume", "Total rewards withdrawn (USDC)"),
]
for col, (label, key, tooltip) in zip(cols1, metric_map):
    col.markdown(metric_card(label, f"${m[key]:,.2f}", tooltip), unsafe_allow_html=True)

# ─────────────────────────────────────────  Unique Wallets
st.markdown("### 👥 Unique Recipients")
st.markdown(
    metric_card("Unique Wallets", f"{m['unique_wallets']:,}", "Total number of unique addresses that received rewards"),
    unsafe_allow_html=True
)

st.markdown("---")

# ─────────────────────────────────────────  Графики по периодам
@st.cache_data(ttl=10)
def _series(network, contract, type_, period: str):
    df = get_time_series(network, contract, type_, period)
    return fill_missing_dates(df, period)

tab_day, tab_week, tab_month, tab_all = st.tabs(
    ["📅 Daily", "📅 Weekly", "📅 Monthly", "📅 All Time"]
)

with tab_day:
    df = _series(NETWORK, CONTRACT, TYPE, "daily")
    draw_chart(df, "💸 Withdrawals in Last 24 Hours", BASE_COLOR, x_format="%H:%M")

with tab_week:
    df = _series(NETWORK, CONTRACT, TYPE, "weekly")
    draw_chart(df, "💸 Withdrawals in Last 7 Days", BASE_COLOR, x_format="%b %d")

with tab_month:
    df = _series(NETWORK, CONTRACT, TYPE, "monthly")
    draw_chart(df, "💸 Withdrawals in Last 30 Days", BASE_COLOR, x_format="%b %d")

with tab_all:
    df = _series(NETWORK, CONTRACT, TYPE, "all")
    draw_chart(df, "💸 Withdrawals — All Time (Daily)", BASE_COLOR, x_format="%b %d")

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