# pages/2_BASE_Contracts.py
"""
Streamlit-страница: аналитика GEM Mint в сети Base
"""

import streamlit as st
import plotly.express as px
from utils.transform import (
    get_metrics,
    get_time_series,
    get_wallet_stats,
)

# ──────────────────────────────────────────────────────────────
# Константы для сети Base
NETWORK  = "BASE"
CONTRACT = "0x7D5aCbAEE4aCcAA4c6fF9ca3F663DD9C28F5df6E"   # GEM minter на Base
PAGE_TITLE = "🔷 GEM Mint — Base"

# ──────────────────────────────────────────────────────────────
# Настройки страницы и ввод кошелька
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)

wallet_filter = st.text_input(
    "🔍 Адрес минтера (необязательно, для детальной статистики)", ""
)

# ──────────────────────────────────────────────────────────────
# Метрики по контракту
@st.cache_data(ttl=120)
def _contract_metrics():
    return get_metrics(NETWORK, CONTRACT)

metrics = _contract_metrics()

col_day, col_week, col_month, col_all = st.columns(4)
col_day.metric("Mint Volume / день",   metrics["mint_volume_day"])
col_week.metric("неделя",              metrics["mint_volume_week"])
col_month.metric("месяц",              metrics["mint_volume_month"])
col_all.metric("всего",                metrics["total_mint_volume"])

c1, c2 = st.columns(2)
c1.metric("Уникальные минтеры (all-time)", metrics["unique_wallets_all_time"])
c2.metric("Всего сминчено GEM",            metrics["total_mint_volume"])

dau, wau, mau = st.columns(3)
dau.metric("DAU", metrics["DAU"])
wau.metric("WAU", metrics["WAU"])
mau.metric("MAU", metrics["MAU"])

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Графики активности (дни, недели, месяцы)
@st.cache_data(ttl=300)
def _series(period):
    return get_time_series(NETWORK, CONTRACT, period)

for p, ttl in [("daily",   "📅 Mint по дням"),
               ("weekly",  "🗓 Mint по неделям"),
               ("monthly", "📆 Mint по месяцам")]:
    df_ser = _series(p)
    fig = px.bar(
        df_ser,
        x="period",
        y="tx_count",
        title=ttl,
        labels={"tx_count": "Mint Tx"},
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# Таблица транзакций + фильтр по кошельку
st.subheader("🧾 Список транзакций")

@st.cache_data(ttl=120)
def _raw_df():
    # получаем серию «daily» для таблицы со всеми нужными колонками
    return get_time_series(NETWORK, CONTRACT, period="daily")

raw_df = _raw_df()

if wallet_filter:
    filt = raw_df[raw_df["from"].str.contains(wallet_filter, case=False)]
    w_stats = get_wallet_stats(NETWORK, CONTRACT, wallet_filter)
    st.info(
        f"Транзакций у **{wallet_filter}**: {w_stats['tx_count']}, "
        f"всего GEM: {w_stats['total_value']}"
    )
    st.dataframe(filt, use_container_width=True)
else:
    st.dataframe(raw_df.head(500), use_container_width=True)
