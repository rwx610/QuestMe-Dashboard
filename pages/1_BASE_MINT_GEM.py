# pages/3_TON_Contracts.py
"""
GEM Mint analytics on the TON network
"""
import streamlit as st
import plotly.express as px
from utils.transform import get_metrics, get_time_series, get_wallet_stats

# ─────────────────────────────────────────  конфиг
NETWORK = "BASE"
CONTRACT = "0xa69a396c45Bd525f8516a43242580c4E88BbA401"
TYPE = "mintGem"  # если фильтруете по type
PAGE_TITLE = "💎 Mint GEM — BASE"
BASE_COLOR = "#3a6da3"  # единый цвет графиков

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)
st.markdown(f"CONTRACT: {CONTRACT}")

wallet_filter = st.text_input("🔍 Minter (address)", "")


# ─────────────────────────────────────────  метрики
@st.cache_data(ttl=10)
def _contract_metrics(network, contract, type_):
    return get_metrics(network, contract, type_)


m = _contract_metrics(NETWORK, CONTRACT, TYPE)

# CSS‑тюнинг, чтобы карточки не растягивались
st.markdown(
    """
    <style>
      div[data-testid="metric-container"] {
        width: 100% !important;
        min-width: 160px;
        border: 1px solid #DDD;
        border-radius: 6px;
        padding: 10px;
        background: #fafafa;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

cols1 = st.columns([1, 1, 1, 1])
metric_map = [
    ("Mint / Day", "volume_day"),
    ("Mint / Week", "volume_week"),
    ("Mint / Month", "volume_month"),
    ("Mint / Total", "total_volume"),
]
for col, (label, key) in zip(cols1, metric_map):
    col.metric(label, f"{m[key]:,}")

cols2 = st.columns([1, 3])
cols2[0].metric("Unique minters", f"{m['unique_wallets']:,}")
cols2[1].metric("Total mint GEM", f"{m['total_volume']:,}")

dau, wau, mau = st.columns([1, 1, 2])
dau.metric("DAU", f"{m['DAU']:,}")
wau.metric("WAU", f"{m['WAU']:,}")
mau.metric("MAU", f"{m['MAU']:,}")

st.markdown("---")


# ─────────────────────────────────────────  графики в табах
@st.cache_data(ttl=10)
def _series(network, contract, type_, period: str):
    return get_time_series(network, contract, type_, period)


tab_day, tab_week, tab_month, tab_all = st.tabs(
    ["📅 Daily", "📅 Weekly", "📅 Monthly", "📅 All Time"]
)


def _draw_chart(df, title, x_dtick=None, x_format=None):
    fig = px.bar(df, x="period", y="tx_count", title=title)
    fig.update_traces(marker_color=BASE_COLOR, hovertemplate="%{x}<br>%{y} tx")
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
    if x_dtick:
        fig.update_xaxes(dtick=x_dtick, tickformat=x_format)
    st.plotly_chart(fig, use_container_width=True)


with tab_day:
    _draw_chart(
        _series(NETWORK, CONTRACT, TYPE, "daily"), "🕒 Mint in Last 24 Hours", x_dtick="H1", x_format="%H:%M"
    )
with tab_week:
    _draw_chart(
        _series(NETWORK, CONTRACT, TYPE, "weekly"), "📅 Mint in Last 7 Days", x_dtick="D1", x_format="%b %d"
    )
with tab_month:
    _draw_chart(
        _series(NETWORK, CONTRACT, TYPE, "monthly"), "📅 Mint in Last 30 Days", x_dtick="D1", x_format="%b %d"
    )
with tab_all:
    _draw_chart(
        _series(NETWORK, CONTRACT, TYPE, "all"), "🕰️ Mint — All Time (Daily)", x_dtick="D1", x_format="%b %d %Y"
    )


# ─────────────────────────────────────────  таблица
st.subheader("🧾 Tx list")


@st.cache_data(ttl=10)
def _raw_daily(network, contract, type_):
    # daily series содержит все колонки, хватает для таблицы
    return get_time_series(network, contract, type_, period="all")


raw_df = _raw_daily(NETWORK, CONTRACT, TYPE)

if wallet_filter:
    filt = raw_df[raw_df["from"].str.contains(wallet_filter, case=False)]
    stats = get_wallet_stats(NETWORK, CONTRACT, wallet_filter, TYPE)
    st.info(
        f"Tx у **{wallet_filter}**: {stats['tx_count']:,} • "
        f"Total GEM: {stats['total_value']}"
    )
    st.dataframe(filt, use_container_width=True)
else:
    st.dataframe(raw_df.head(500), use_container_width=True)
