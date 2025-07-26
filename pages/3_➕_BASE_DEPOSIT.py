# pages/3_➕_BASE_PROJECT_DEPOSITS.py

import streamlit as st
from analytics.metrics import get_metrics, get_time_series
from ui.display import inject_card_styles, metric_card, fill_missing_dates, draw_chart

# ────────────────────────────────  config
NETWORK = "BASE"
CONTRACT = "0x252683e292d7e36977de92a6bf779d6bc35176d4"
TYPE = "resetAndSendSponsorship"
PAGE_TITLE = "Deposits — BASE"
BASE_COLOR = "#3a6da3"

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)
st.markdown(f"CONTRACT: `{CONTRACT}`")

# ────────────────────────────────  styles
inject_card_styles()

# ────────────────────────────────  metrics
@st.cache_data(ttl=10)
def _contract_metrics(network, contract, type_):
    return get_metrics(network, contract, type_)

m = _contract_metrics(NETWORK, CONTRACT, TYPE)

st.markdown("### ➕ Deposits")
cols = st.columns(2)

cols[0].markdown(
    metric_card(
        "💰 Total Deposit Volume (USDC)",
        f"${m.get('total_volume', 0):,.2f}",
        "Общая сумма депозитов, выраженная в USDC"
    ),
    unsafe_allow_html=True
)

cols[1].markdown(
    metric_card(
        "➕ Number of Deposits",
        f"{m.get('total_tx_count', 0):,}",
        "Общее количество транзакций-депозитов"
    ),
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
    draw_chart(df, "➕ Deposits in Last 24 Hours", BASE_COLOR, x_format="%H:%M")

with tab_week:
    df = _series(NETWORK, CONTRACT, TYPE, "weekly")
    draw_chart(df, "➕ Deposits in Last 7 Days", BASE_COLOR, x_format="%b %d")

with tab_month:
    df = _series(NETWORK, CONTRACT, TYPE, "monthly")
    draw_chart(df, "➕ Deposits in Last 30 Days", BASE_COLOR, x_format="%b %d")

with tab_all:
    df = _series(NETWORK, CONTRACT, TYPE, "all")
    draw_chart(df, "➕ Deposits — All Time (Daily)", BASE_COLOR, x_format="%b %d")

st.markdown("---")