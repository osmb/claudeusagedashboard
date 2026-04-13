"""Streamlit dashboard — rendering only. All data logic lives in data.py."""

from datetime import date, timedelta
from typing import cast

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ccusage.config import load_config
from ccusage.data import (
    apply_filters,
    cache_hit_rate,
    cache_savings_usd,
    load_data,
    projected_month_cost,
)

st.set_page_config(page_title="Claude Insights", layout="wide", page_icon="🤖")

st.markdown(
    """
<style>
  html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
  [data-testid="metric-container"] {
    background: #161827; border: 1px solid #2a2d45;
    border-radius: 12px; padding: 20px 24px;
  }
  [data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: #8b8fad !important;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.9rem; font-weight: 700; color: #E8E8F4 !important;
  }
  [data-testid="stSidebar"] { background: #0f1120; border-right: 1px solid #1e2035; }
  [data-testid="stSidebar"] .stRadio label,
  [data-testid="stSidebar"] .stSelectbox label {
    font-size: 0.8rem; font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; color: #8b8fad;
  }
  hr { border-color: #1e2035 !important; margin: 1.5rem 0; }
  h2, h3 { font-weight: 700 !important; letter-spacing: -0.01em; }
  [data-testid="stPopover"] button {
    background: transparent !important; border: 1px solid #2a2d45 !important;
    border-radius: 6px !important; color: #8b8fad !important;
    font-size: 0.75rem !important; padding: 2px 6px !important;
  }
  [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
  .stButton button {
    background: #7C6AF7 !important; color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important; width: 100%;
  }
</style>
""",
    unsafe_allow_html=True,
)

CHART_COLORS = ["#7C6AF7", "#38BDF8", "#34D399", "#FB923C", "#F472B6"]
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, Segoe UI, sans-serif", color="#E8E8F4"),
    margin=dict(t=16, b=0, l=0, r=0),
)
AXIS_STYLE = dict(gridcolor="#1e2035", linecolor="#1e2035")


def section_header(title: str, info_md: str) -> None:
    c1, c2 = st.columns([18, 1])
    c1.subheader(title)
    with c2, st.popover("i️"):
        st.markdown(info_md)


# ── Load data ─────────────────────────────────────────────────────────────────
config = load_config()
df = load_data(config.db_path)

st.markdown("## 🤖 &nbsp;Claude Usage Dashboard")
st.markdown(
    "<p style='color:#8b8fad;margin-top:-12px;margin-bottom:24px;'>"
    "API-Kosten · Cache-Effizienz · Verbrauchstrends</p>",
    unsafe_allow_html=True,
)

if df.empty:
    st.info("Noch keine Daten vorhanden. Starte `just collect`.")
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filter")
    zeitraum = st.radio(
        "Zeitraum", ["Gesamt", "Diesen Monat", "Diese Woche", "Heute", "Benutzerdefiniert"]
    )
    today_ts = pd.Timestamp(date.today())

    if zeitraum == "Heute":
        start_date, end_date = today_ts, today_ts
    elif zeitraum == "Diese Woche":
        start_date = today_ts - timedelta(days=today_ts.weekday())
        end_date = today_ts
    elif zeitraum == "Diesen Monat":
        start_date = today_ts.replace(day=1)
        end_date = today_ts
    elif zeitraum == "Benutzerdefiniert":
        min_d, max_d = df["date"].dt.date.min(), df["date"].dt.date.max()
        # st.date_input returns date | list[date]; pd.Timestamp() stubs include NaTType —
        # cast tells ty we know the result is a proper Timestamp when raw_* is truthy.
        raw_start = st.date_input("Von", value=min_d, min_value=min_d, max_value=max_d)
        raw_end = st.date_input("Bis", value=max_d, min_value=min_d, max_value=max_d)
        start_date: pd.Timestamp | None = (
            cast("pd.Timestamp", pd.Timestamp(raw_start)) if raw_start else None
        )
        end_date: pd.Timestamp | None = (
            cast("pd.Timestamp", pd.Timestamp(raw_end)) if raw_end else None
        )
    else:
        start_date = end_date = None

    models = ["Alle", *sorted(df["model"].unique().tolist())]
    selected_model = st.selectbox("Modell", models)

# cast: pd.Timestamp() stubs include NaTType; we guarantee Timestamp | None here
fdf = apply_filters(
    df,
    cast("pd.Timestamp | None", start_date),
    cast("pd.Timestamp | None", end_date),
    selected_model,
)

if fdf.empty:
    st.info("Keine Daten für den gewählten Zeitraum.")
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Gesamtkosten",
    f"${fdf['total_cost'].sum():.2f}",
    help="Summe aller API-Kosten im gewählten Zeitraum.",
)
k2.metric(
    "Cache-Ersparnis",
    f"${cache_savings_usd(fdf):.2f}",
    help="Geschätzte Ersparnis durch Prompt-Caching.",
)
k3.metric(
    "Monatsprojektion",
    f"${projected_month_cost(df):.2f}",
    help="Hochrechnung auf Basis des täglichen Durchschnitts im laufenden Monat.",
)
k4.metric(
    "Cache-Hit-Rate",
    f"{cache_hit_rate(fdf):.1f} %",
    help="Anteil der Cache-Read-Tokens an allen Tokens.",
)

st.markdown("---")

# ── Kostenverlauf + Modell-Mix ─────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    section_header(
        "Kostenverlauf",
        "**Was wird gezeigt?** Tägliche API-Kosten nach Modell eingefärbt.\n\n"
        "**Warum wichtig?** Zeigt Verbrauchsspitzen und welches Modell dein Budget dominiert.",
    )
    daily_cost = fdf.groupby([fdf["date"].dt.date, "model"])["total_cost"].sum().reset_index()
    daily_cost.columns = ["Datum", "Modell", "Kosten"]
    fig_cost = px.bar(
        daily_cost,
        x="Datum",
        y="Kosten",
        color="Modell",
        color_discrete_sequence=CHART_COLORS,
        height=300,
        labels={"Kosten": "USD"},
    )
    fig_cost.update_layout(
        **PLOTLY_LAYOUT,
        xaxis=AXIS_STYLE,
        yaxis=AXIS_STYLE,
        legend=dict(orientation="h", y=1.12, x=0),
    )
    st.plotly_chart(fig_cost, width="stretch")

with col_right:
    section_header(
        "Modell-Mix",
        "**Was wird gezeigt?** Kostenanteil je Modell.\n\n"
        "**Warum wichtig?** Hilft einzuschätzen ob günstigere Modelle öfter ausreichen.",
    )
    model_cost = fdf.groupby("model")["total_cost"].sum().reset_index()
    fig_donut = go.Figure(
        go.Pie(
            labels=model_cost["model"],
            values=model_cost["total_cost"],
            hole=0.62,
            textinfo="label+percent",
            marker=dict(colors=CHART_COLORS, line=dict(color="#0D0F1A", width=2)),
        )
    )
    fig_donut.update_layout(**PLOTLY_LAYOUT, height=300, legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig_donut, width="stretch")

st.markdown("---")

# ── Cache-Effizienz ────────────────────────────────────────────────────────────
section_header(
    "Cache-Effizienz",
    "**Was wird gezeigt?** Tägliche Cache-Hit-Rate (lila) und Ersparnis in USD (orange).\n\n"
    "**Warum wichtig?** Steigende Hit-Rate = Claude nutzt Kontext effizient wieder.",
)
daily_cache = (
    fdf.groupby(fdf["date"].dt.date)
    .agg(
        input_tokens=("input_tokens", "sum"),
        cache_creation=("cache_creation_tokens", "sum"),
        cache_reads=("cache_read_tokens", "sum"),
    )
    .reset_index()
)
daily_cache.columns = ["Datum", "input_tokens", "cache_creation", "cache_reads"]
total_tok = daily_cache["input_tokens"] + daily_cache["cache_creation"] + daily_cache["cache_reads"]
daily_cache["hit_rate"] = (daily_cache["cache_reads"] / total_tok.replace(0, 1) * 100).round(1)
daily_cache["savings"] = (daily_cache["cache_reads"] * (3.0 - 0.30) / 1_000_000).round(4)

fig_cache = go.Figure()
fig_cache.add_trace(
    go.Bar(
        x=daily_cache["Datum"],
        y=daily_cache["savings"],
        name="Ersparnis (USD)",
        marker_color="#FB923C",
        yaxis="y2",
        opacity=0.7,
    )
)
fig_cache.add_trace(
    go.Scatter(
        x=daily_cache["Datum"],
        y=daily_cache["hit_rate"],
        name="Cache-Hit-Rate (%)",
        line=dict(color="#7C6AF7", width=2.5),
    )
)
fig_cache.update_layout(
    **PLOTLY_LAYOUT,
    height=280,
    xaxis=AXIS_STYLE,
    yaxis=dict(title="Hit-Rate (%)", **AXIS_STYLE),
    yaxis2=dict(title="Ersparnis (USD)", overlaying="y", side="right", **AXIS_STYLE),
    legend=dict(orientation="h", y=1.12, x=0),
)
st.plotly_chart(fig_cache, width="stretch")

st.markdown("---")

# ── Wöchentlicher Trend ────────────────────────────────────────────────────────
section_header(
    "Wöchentlicher Kostentrend",
    "**Was wird gezeigt?** Gesamtkosten pro Kalenderwoche.\n\n"
    "**Warum wichtig?** Zeigt ob dein Verbrauch steigt oder stabil bleibt.",
)
week_df = df.copy()
week_df["KW"] = week_df["date"].dt.isocalendar().week.astype(int)
week_df["Jahr"] = week_df["date"].dt.year
weekly = week_df.groupby(["Jahr", "KW"])["total_cost"].sum().reset_index()
weekly["Label"] = weekly["Jahr"].astype(str) + " · KW " + weekly["KW"].astype(str)
fig_wow = px.bar(
    weekly,
    x="Label",
    y="total_cost",
    color_discrete_sequence=["#38BDF8"],
    height=260,
    labels={"total_cost": "USD", "Label": ""},
)
fig_wow.update_layout(**PLOTLY_LAYOUT, xaxis=AXIS_STYLE, yaxis=AXIS_STYLE)
fig_wow.update_traces(marker_line_width=0)
st.plotly_chart(fig_wow, width="stretch")

st.markdown("---")

with st.expander("Rohdaten"):
    st.info("Alle Einträge im gewählten Zeitraum.", icon="i")
    st.dataframe(fdf.sort_values(by="date", ascending=False), width="stretch")

st.markdown(
    "<p style='text-align:center;color:#3a3d55;font-size:0.8rem;"
    "padding-top:1rem;'>Made in Berlin</p>",
    unsafe_allow_html=True,
)
