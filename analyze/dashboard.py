"""SeismoStream — global seismic monitoring console (reads the DuckDB warehouse)."""
from datetime import datetime

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = "warehouse.duckdb"
st.set_page_config(page_title="SeismoStream", page_icon="🛰️", layout="wide")

SEISMIC = [[0.0, "#FFE08A"], [0.4, "#F3A03C"], [0.7, "#E2502E"], [1.0, "#A11226"]]
CLASS_COLORS = {"micro": "#3E7CB1", "minor": "#4DD0C7", "light": "#9BD16B",
                "moderate": "#FFD166", "strong": "#F3A03C", "major": "#E2502E", "great": "#A11226"}
CLASS_ORDER = ["micro", "minor", "light", "moderate", "strong", "major", "great"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500&family=IBM+Plex+Mono:wght@500;600&display=swap');
.stApp { background: radial-gradient(1200px 600px at 72% -12%, #16233A 0%, #0E1726 58%); font-family:'Inter',sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 1320px; }
h2, h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-0.01em; color:#E6ECF5; }
.eyebrow { font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.28em; text-transform:uppercase; color:#4DD0C7; }
.title { font-family:'Space Grotesk',sans-serif; font-size:2.2rem; font-weight:700; color:#E6ECF5; margin:.15rem 0 .2rem; }
.sub { color:#8A9BB5; font-size:.92rem; font-family:'IBM Plex Mono',monospace; }
.pulse { display:inline-block; width:9px; height:9px; border-radius:50%; background:#4DD0C7; margin-right:9px; animation:pulse 1.8s infinite; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(77,208,199,.6);} 70%{box-shadow:0 0 0 10px rgba(77,208,199,0);} 100%{box-shadow:0 0 0 0 rgba(77,208,199,0);} }
@media (prefers-reduced-motion: reduce){ .pulse{animation:none;} }
.kpi-row { display:flex; gap:14px; margin:20px 0 8px; flex-wrap:wrap; }
.kpi-card { flex:1; min-width:150px; background:rgba(22,34,54,.55); border:1px solid #24324A; border-radius:12px; padding:15px 18px; }
.kpi-label { font-family:'IBM Plex Mono',monospace; font-size:.66rem; letter-spacing:.14em; text-transform:uppercase; color:#8A9BB5; }
.kpi-value { font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:1.7rem; color:#E6ECF5; margin-top:7px; line-height:1; }
.kpi-value.hot { color:#F3A03C; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load(query):
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        return con.execute(query).fetchdf()
    finally:
        con.close()


def style(fig, height=320):
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#C7D2E4", family="Inter"),
                      xaxis=dict(gridcolor="#1E2A40"), yaxis=dict(gridcolor="#1E2A40"))
    return fig


fct = load("SELECT * FROM main.fct_earthquakes")
daily = load("SELECT * FROM main.agg_daily_activity ORDER BY activity_date")
classes = load("SELECT * FROM main.agg_by_magnitude_class")
exposure = load("SELECT * FROM main.quake_exposure")
clusters = load("SELECT * FROM main.quake_clusters")
fct = fct.merge(clusters[["id", "cluster_id"]], on="id", how="left")
n_clusters = int(clusters.loc[clusters.cluster_id != -1, "cluster_id"].nunique())

st.markdown(f"""
<div class="eyebrow"><span class="pulse"></span>Global seismic monitor</div>
<div class="title">SeismoStream</div>
<div class="sub">live USGS feed → custom Meltano tap → DuckDB → dbt → analytics · synced {datetime.now():%Y-%m-%d %H:%M}</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card"><div class="kpi-label">Events tracked</div><div class="kpi-value">{len(fct):,}</div></div>
  <div class="kpi-card"><div class="kpi-label">Strongest</div><div class="kpi-value hot">M{fct['magnitude'].max():.1f}</div></div>
  <div class="kpi-card"><div class="kpi-label">Energy released</div><div class="kpi-value">{fct['energy_joules'].sum():.1e} J</div></div>
  <div class="kpi-card"><div class="kpi-label">M6.0+ alerts</div><div class="kpi-value hot">{int((fct['magnitude'] >= 6).sum())}</div></div>
  <div class="kpi-card"><div class="kpi-label">Active clusters</div><div class="kpi-value">{n_clusters}</div></div>
</div>
""", unsafe_allow_html=True)

st.subheader("Where the planet moved")
m = fct.copy()
m["zone"] = m["cluster_id"].apply(lambda x: "isolated" if pd.isna(x) or x == -1 else f"cluster {int(x)}")
fig = px.scatter_geo(m, lat="latitude", lon="longitude", size="magnitude", color="magnitude",
                     color_continuous_scale=SEISMIC, size_max=18, hover_name="place",
                     hover_data={"magnitude": True, "zone": True, "latitude": False, "longitude": False})
fig.update_geos(bgcolor="rgba(0,0,0,0)", showland=True, landcolor="#1B2638",
                showocean=True, oceancolor="#0E1726", showcountries=True, countrycolor="#243149",
                coastlinecolor="#2E4060", showframe=False, projection_type="natural earth")
style(fig, 520)
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Daily activity")
    f2 = px.bar(daily, x="activity_date", y="quake_count", hover_data=["max_magnitude", "avg_magnitude"])
    f2.update_traces(marker_color="#4DD0C7")
    st.plotly_chart(style(f2), use_container_width=True)
with right:
    st.subheader("By magnitude class")
    classes["magnitude_class"] = pd.Categorical(classes["magnitude_class"], CLASS_ORDER, ordered=True)
    f3 = px.bar(classes.sort_values("magnitude_class"), x="magnitude_class", y="quake_count",
                color="magnitude_class", color_discrete_map=CLASS_COLORS)
    f3.update_layout(showlegend=False)
    st.plotly_chart(style(f3), use_container_width=True)

st.subheader("Population-exposure leaderboard")
st.caption("A moderate quake beside a megacity can out-rank a giant one offshore — magnitude weighted by nearest-city population and distance.")
top = exposure.sort_values("exposure_index", ascending=False).head(10)
st.dataframe(top, use_container_width=True, hide_index=True, column_config={
    "magnitude": st.column_config.NumberColumn("Mag", format="%.1f"),
    "place": "Location", "nearest_city": "Nearest city", "nearest_country": "Country",
    "distance_km": st.column_config.NumberColumn("Distance (km)", format="%.0f"),
    "city_population": st.column_config.NumberColumn("City pop.", format="%d"),
    "exposure_index": st.column_config.ProgressColumn("Exposure", format="%.0f",
                       min_value=0, max_value=float(top["exposure_index"].max())),
})