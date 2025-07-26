# pages/3_TON_Contracts.py
"""
GEM Mint analytics on the TON network
"""
import streamlit as st
from analytics.metrics import get_metrics, get_time_series
from ui.display import inject_card_styles, metric_card, fill_missing_dates, draw_chart

# ─────────────────────────────────────────  конфиг
NETWORK = "TON"
CONTRACT = "UQCn9hCC6tNykDqZisfJvwrE9RQNPalV8VArNWrmI_REtoHz"
TYPE = "TextComment"  # если фильтруете по type
PAGE_TITLE = "Mint GEM — TON"
BASE_COLOR = "#3a6da3"  # единый цвет графиков

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)
st.markdown(f"CONTRACT: `{CONTRACT}`")


# ─────────────────────────────────────────  Стили и метрики
inject_card_styles()

@st.cache_data(ttl=10)
def _contract_metrics(network, contract, type_):
    return get_metrics(network, contract, type_)

m = _contract_metrics(NETWORK, CONTRACT, TYPE)

# ─────────────────────────────────────────  Группа 1: Mint Volume
st.markdown("### 🧪 Mint Volume")
cols1 = st.columns(4)
metric_map = [
    ("Mint / Day", "tx_day", "The number of gems minted in the last 24 hours"),
    ("Mint / Week", "tx_week", "The number of gems minted in the last 7 days"),
    ("Mint / Month", "tx_month", "The number of gems minted in the last 30 days"),
    ("Mint / Total", "total_tx_count", "Total gems minted"),
]
for col, (label, key, tooltip) in zip(cols1, metric_map):
    col.markdown(metric_card(label, f"{m[key]:,}", tooltip), unsafe_allow_html=True)

# ─────────────────────────────────────────  Группа 2: User Activity
st.markdown("### 🔥 User Activity")
cols2 = st.columns(4)
activity_map = [
    ("DAU", m["dau"], "Daily Active Users — unique addresses for the last 24 hours"),
    ("WAU", m["wau"], "Weekly Active Users — unique addresses for the last 7 days"),
    ("MAU", m["mau"], "Monthly Active Users — unique addresses for the last 30 days"),
    ("UAW (All time)", m["unique_wallets"], "Unique Active Wallets — total unique addresses"),
]
for col, (label, value, tooltip) in zip(cols2, activity_map):
    col.markdown(metric_card(label, f"{value:,}", tooltip), unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────  Графики
@st.cache_data(ttl=10)
def _series(network, contract, type_, period: str):
    df = get_time_series(network, contract, type_, period)
    return fill_missing_dates(df, period)

tab_day, tab_week, tab_month, tab_all = st.tabs(
    ["📅 Daily", "📅 Weekly", "📅 Monthly", "📅 All Time"]
)

with tab_day:
    draw_chart(_series(NETWORK, CONTRACT, TYPE, "daily"), "🕒 Mint in Last 24 Hours", BASE_COLOR, x_format="%H:%M")
with tab_week:
    draw_chart(_series(NETWORK, CONTRACT, TYPE, "weekly"), "📅 Mint in Last 7 Days", BASE_COLOR, x_format="%b %d")
with tab_month:
    draw_chart(_series(NETWORK, CONTRACT, TYPE, "monthly"), "📅 Mint in Last 30 Days", BASE_COLOR, x_format="%b %d")
with tab_all:
    draw_chart(_series(NETWORK, CONTRACT, TYPE, "all"), "🕰️ Mint — All Time (Daily)", BASE_COLOR, x_format="%b %d %Y")