# pages/3_TON_Contracts.py
"""
Streamlit-страница: аналитика GEM Mint в сети TON
"""

import streamlit as st
import plotly.express as px
from utils.transform import (
    get_metrics,
    get_time_series,
    get_wallet_stats,
)

# ──────────────────────────────────────────────────────────────
# Константы
NETWORK = "TON"
CONTRACT = "UQCn9hCC6tNykDqZisfJvwrE9RQNPalV8VArNWrmI_REtoHz"
PAGE_TITLE = "💎 GEM Mint — TON"

# ──────────────────────────────────────────────────────────────
# Заголовок и ввод пользовательского кошелька
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)

wallet_filter = st.text_input("🔍 Адрес минтера (опционально для детальной статистики)", "")

# ──────────────────────────────────────────────────────────────
# Метрики по контракту
@st.cache_data(ttl=120)  # пересчитываем раз в 2 мин
def _contract_metrics():
    return get_metrics(NETWORK, CONTRACT)

metrics = _contract_metrics()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Mint Volume / день",  metrics["mint_volume_day"])
m2.metric("неделя",              metrics["mint_volume_week"])
m3.metric("месяц",               metrics["mint_volume_month"])
m4.metric("всего",               metrics["total_mint_volume"])

c1, c2 = st.columns(2)
c1.metric("Уникальные минтеры (all-time)", metrics["unique_wallets_all_time"])
c2.metric("Всего сминчено GEM",            metrics["total_mint_volume"])  # при 1 tx = 1 GEM

dau, wau, mau = st.columns(3)
dau.metric("DAU", metrics["DAU"])
wau.metric("WAU", metrics["WAU"])
mau.metric("MAU", metrics["MAU"])

st.markdown("---")

# ──────────────────────────────────────────────────────────────
# Графики активности
@st.cache_data(ttl=300)
def _load_series(period: str):
    return get_time_series(NETWORK, CONTRACT, period=period)

for period, title in [("daily", "📅 Mint по дням"),
                      ("weekly", "🗓 Mint по неделям"),
                      ("monthly", "📆 Mint по месяцам")]:
    df_series = _load_series(period)
    fig = px.bar(
        df_series,
        x="period",
        y="tx_count",
        title=title,
        labels={"tx_count": "Mint Tx"},
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# Таблица с фильтром кошелька
st.subheader("🧾 Список транзакций")

@st.cache_data(ttl=120)
def _load_raw():
    # Используем тот же helper, но забираем уже агрегацию «daily» и переименуем
    df = get_time_series(NETWORK, CONTRACT, period="daily")  # получим все колонки
    return df

raw_df = _load_raw()

if wallet_filter:
    filt_df = raw_df[raw_df["from"].str.contains(wallet_filter, case=False)]
    stats = get_wallet_stats(NETWORK, CONTRACT, wallet_filter)
    st.info(f"Транзакций у **{wallet_filter}**: {stats['tx_count']}, "
            f"всего GEM: {stats['total_value']}")
    st.dataframe(filt_df, use_container_width=True)
else:
    st.dataframe(raw_df.head(500), use_container_width=True)  # показываем «свежие» 500
