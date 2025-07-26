import calendar
import plotly.express as px
import plotly.colors as pc
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta, timezone


def inject_card_styles():
    st.markdown(
        """
        <style>
        .card {
            background-color: #1e1e1e;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 0 12px rgba(255,255,255,0.05);
            text-align: center;
            color: white;
            margin: 6px 0;
        }
        .card-label {
            font-size: 13px;
            color: #bbbbbb;
        }
        .card-value {
            font-size: 26px;
            font-weight: 600;
            color: #fdfdfd;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, tooltip: str = "") -> str:
    return f"""
    <div class="card">
        <div class="card-label" title="{tooltip}">{label}</div>
        <div class="card-value">{value}</div>
    </div>
    """


def fill_missing_dates(df: pd.DataFrame, period: str) -> pd.DataFrame:
    PERIODS_IN_SECONDS = {
        "daily": 86400,
        "weekly": 86400 * 7,
        "monthly": 86400 * 30,
        "all": None,
    }

    now = datetime.now(timezone.utc)
    df["period"] = pd.to_datetime(df["period"], utc=True)

    seconds = PERIODS_IN_SECONDS.get(period)

    if period == "daily":
        full_range = pd.date_range(
            end=now.replace(minute=0, second=0, microsecond=0),
            periods=24,
            freq="h",
        )
        df["period"] = df["period"].dt.floor("h")
    elif period in {"weekly", "monthly"}:
        days = 7 if period == "weekly" else 30
        start = (now - timedelta(days=days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        full_range = pd.date_range(start=start, end=end, freq="D")
        df["period"] = df["period"].dt.floor("d")
    elif period == "all":
        start = df["period"].min().floor("D")
        end = pd.Timestamp(now).floor("D")  # 👈 исправлено
        full_range = pd.date_range(start=start, end=end, freq="D")
        df["period"] = df["period"].dt.floor("D")
        df["period"] = df["period"].dt.floor("d")
    else:
        raise ValueError(f"Invalid period: {period}")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    df = df.groupby("period")[numeric_cols].sum().reset_index()

    df = (
        df.set_index("period")
        .reindex(full_range, fill_value=0)
        .rename_axis("period")
        .reset_index()
    )

    return df


def draw_chart(df, title, base_color="#3a6da3", x_dtick=None, x_format=None, rotate_threshold=32):
    max_tx = df["tx_count"].max()

    # ─────── Y шаг
    if max_tx <= 5:
        y_dtick = 1
    elif max_tx <= 10:
        y_dtick = 2
    elif max_tx <= 50:
        y_dtick = 5
    elif max_tx <= 100:
        y_dtick = 10
    elif max_tx <= 500:
        y_dtick = 50
    else:
        y_dtick = 100

    df = df.copy()
    df["period"] = pd.to_datetime(df["period"])

    # ─────── Определение группы по месяцу
    if title.lower().startswith("🕰️"):  # All Time
        df["color_group"] = df["period"].dt.to_period("M").astype(str)
    else:
        df["color_group"] = ""

    # ─────── Уникальные даты для X тиков
    unique_dates = df["period"].sort_values().unique()
    num_dates = len(unique_dates)
    x_tick_step = 1 if num_dates <= 90 else (num_dates // 90) + 1
    tickvals = unique_dates[::x_tick_step]
    tick_angle = 90 if num_dates > rotate_threshold else 0

    # ─────── Генерация палитры (если есть цветовая группировка)
    if df["color_group"].nunique() > 1:
        palette = pc.sample_colorscale("Blues", df["color_group"].nunique())
        color_map = dict(zip(sorted(df["color_group"].unique()), palette))
        colors = df["color_group"].map(color_map)
    else:
        colors = base_color

    fig = px.bar(df, x="period", y="tx_count", title=title, color=df["color_group"] if df["color_group"].nunique() > 1 else None, color_discrete_map=color_map if df["color_group"].nunique() > 1 else None)
    fig.update_traces(marker_line_width=0, hovertemplate="%{x}<br>%{y} tx")
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
    fig.update_xaxes(tickvals=tickvals, tickformat=x_format or "%Y-%m-%d", tickangle=tick_angle)
    fig.update_yaxes(dtick=y_dtick, tickformat=".0f")

    st.plotly_chart(fig, use_container_width=True)

def tabs_with_series(*args, **kwargs):
    pass  # или заглушка для тестов
