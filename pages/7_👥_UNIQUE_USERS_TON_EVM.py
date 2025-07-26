# pages/7_👥_UNIQUE_USERS_ALL.py

import streamlit as st
from analytics.metrics import get_metrics, get_time_series
from ui.display import inject_card_styles, metric_card, draw_chart, fill_missing_dates
import pandas as pd

# ─────────────────────────────────────────  Конфигурация
PAGE_TITLE = "Unique Users — TON + BASE"
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)

NETWORKS = {
    "BASE": {
        "contract": "0x1f735280C83f13c6D40aA2eF213eb507CB4c1eC7",  # Пример: reward
        "type": "reward",
    },
    "TON": {
        "contract": "EQCfcwvBP2cnD8UwWLKtX1pcAqEDFwFyXzuZ0seyPBdocPHu",  # Пример
        "type": "0x76ebc41e",
    },
}

BASE_COLOR = "#3a6da3"

# ─────────────────────────────────────────  Стили
inject_card_styles()

# ─────────────────────────────────────────  Метрики
@st.cache_data(ttl=30)
def _get_user_metrics():
    all_wallets = set()
    metrics_by_period = {"dau": set(), "wau": set(), "mau": set()}

    for net, data in NETWORKS.items():
        m = get_metrics(net, data["contract"], data["type"])

        # Обработка unique_wallets
        value = m.get("unique_wallets", [])
        if isinstance(value, set):
            all_wallets.update(value)
        else:
            all_wallets.update([])

        # Обработка dau/wau/mau
        for k in ["dau", "wau", "mau"]:
            value = m.get(k, [])
            if isinstance(value, set):
                metrics_by_period[k].update(value)
            else:
                metrics_by_period[k].update([])

    return {
        "unique_wallets": len(all_wallets),
        "dau": len(metrics_by_period["dau"]),
        "wau": len(metrics_by_period["wau"]),
        "mau": len(metrics_by_period["mau"]),
    }

metrics = _get_user_metrics()

st.markdown("### 👥 Unique Users (All Chains)")
cols = st.columns(4)
cols[0].markdown(metric_card("DAU", f"{metrics['dau']:,}", "Daily Active Users — across all chains"), unsafe_allow_html=True)
cols[1].markdown(metric_card("WAU", f"{metrics['wau']:,}", "Weekly Active Users — across all chains"), unsafe_allow_html=True)
cols[2].markdown(metric_card("MAU", f"{metrics['mau']:,}", "Monthly Active Users — across all chains"), unsafe_allow_html=True)
cols[3].markdown(metric_card("UAW (All time)", f"{metrics['unique_wallets']:,}", "Total unique wallets across all chains"), unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────  Графики
@st.cache_data(ttl=30)
def _get_series(period: str) -> pd.DataFrame:
    dfs = []
    for net, data in NETWORKS.items():
        df = get_time_series(net, data["contract"], data["type"], period)
        if not df.empty:
            df = df[["period", "wallet"]].drop_duplicates()
            df["count"] = 1
            df = df.groupby("period").agg({"wallet": "nunique"}).rename(columns={"wallet": f"users_{net}"})
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, axis=1).fillna(0)
    df_all["users"] = df_all.sum(axis=1)
    df_all = df_all.reset_index()
    return fill_missing_dates(df_all[["period", "users"]], period)

tab_day, tab_week, tab_month = st.tabs(["📅 Daily", "📅 Weekly", "📅 Monthly"])

with tab_day:
    df = _get_series("daily")
    draw_chart(df, "📅 Daily Active Users — All Chains", BASE_COLOR, x_format="%H:%M")

with tab_week:
    df = _get_series("weekly")
    draw_chart(df, "📅 Weekly Active Users — All Chains", BASE_COLOR, x_format="%b %d")

with tab_month:
    df = _get_series("monthly")
    draw_chart(df, "📅 Monthly Active Users — All Chains", BASE_COLOR, x_format="%b %d")
