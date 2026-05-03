import streamlit as st
import pandas as pd
from data_loader import (
    load_batting, load_pitching, load_fielding,
    load_sprint, get_player_data, detect_role, SEASON
)
from components import build_radar, build_comparison_table, build_comparison_image, build_sprint_row

# ── Config ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vision 360 — Baseball Comparison",
    page_icon="⚾",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    h1 { font-size: 2rem; }
    .advantage-p1 { color: #E63946; font-weight: bold; }
    .advantage-p2 { color: #457B9D; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Carga de datos ───────────────────────────────────────────────────────────
with st.spinner("Cargando datos FanGraphs / Statcast..."):
    bat_df    = load_batting()
    pit_df    = load_pitching()
    field_df  = load_fielding()
    sprint_df = load_sprint()

all_batters  = sorted(bat_df["Name"].dropna().unique().tolist()) if not bat_df.empty else []
all_pitchers = sorted(pit_df["Name"].dropna().unique().tolist()) if not pit_df.empty else []
all_players  = sorted(set(all_batters + all_pitchers))

if not all_players:
    st.error(
        "No se pudieron cargar jugadores de FanGraphs. "
        "Posibles causas: FanGraphs no es accesible desde este servidor, "
        "o aun no hay suficientes PA/IP acumulados en la temporada. "
        "Revisa los logs de la app (Manage app → Logs) para el detalle del error."
    )
    st.stop()

# ── Header ───────────────────────────────────────────────────────────────────
st.title("⚾ Vision 360 — Player Comparison")
st.caption(f"Temporada MLB {SEASON} · Datos: FanGraphs + Baseball Savant")

# ── Selección de jugadores ───────────────────────────────────────────────────
col1, col_vs, col2 = st.columns([5, 1, 5])

with col1:
    p1 = st.selectbox("Jugador 1", all_players, index=0, key="p1")

with col_vs:
    st.markdown("<br><br><h3 style='text-align:center'>VS</h3>", unsafe_allow_html=True)

with col2:
    default_idx = min(1, len(all_players) - 1)
    p2 = st.selectbox("Jugador 2", all_players, index=default_idx, key="p2")

if p1 == p2:
    st.warning("Selecciona dos jugadores distintos.")
    st.stop()

# ── Obtener datos ─────────────────────────────────────────────────────────────
d1 = get_player_data(p1, bat_df, pit_df, field_df, sprint_df)
d2 = get_player_data(p2, bat_df, pit_df, field_df, sprint_df)

role1 = d1["role"]
role2 = d2["role"]

# Determinar vista comparativa
if role1 == role2 and role1 != "two-way":
    compare_role = role1
elif role1 == "two-way" or role2 == "two-way":
    compare_role = st.radio(
        "Vista de comparación para jugador two-way:",
        ["batter", "pitcher"], horizontal=True
    )
else:
    st.info(f"**{p1}** es {role1} y **{p2}** es {role2}. "
            "Mostrando dimensiones disponibles para cada uno.")
    compare_role = "mixed"

# ── Badges de rol ─────────────────────────────────────────────────────────────
c1, _, c2 = st.columns([5, 1, 5])
with c1:
    st.markdown(f"### 🔴 {p1}")
    d1_stats = d1.get("batting", {}) or d1.get("pitching", {})
    st.caption(f"{d1_stats.get('Team','—')} · {role1.upper()}")
with c2:
    st.markdown(f"### 🔵 {p2}")
    d2_stats = d2.get("batting", {}) or d2.get("pitching", {})
    st.caption(f"{d2_stats.get('Team','—')} · {role2.upper()}")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_radar, tab_stats, tab_field, tab_speed = st.tabs([
    "🕸️ Radar 360", "📊 Stats Comparados", "🧤 Defensa", "💨 Velocidad"
])

# ── TAB 1: Radar ──────────────────────────────────────────────────────────────
with tab_radar:
    if compare_role not in ("mixed",):
        fig = build_radar(d1, d2, p1, p2, compare_role)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Valores normalizados a percentil 0–100 dentro del rango histórico de la métrica.")
    else:
        st.info("Radar disponible solo cuando ambos jugadores comparten rol. "
                "Revisa el tab de Stats Comparados.")

# ── TAB 2: Stats ──────────────────────────────────────────────────────────────
with tab_stats:
    if compare_role != "mixed":
        df_comp = build_comparison_table(d1, d2, p1, p2, compare_role)

        def highlight_winner(row):
            styles = ["", "", "", ""]
            if row["Ventaja"] == p1:
                styles[1] = "color: #E63946; font-weight: bold"
            elif row["Ventaja"] == p2:
                styles[2] = "color: #457B9D; font-weight: bold"
            return styles

        st.dataframe(
            df_comp.style.apply(highlight_winner, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        img_bytes = build_comparison_image(d1, d2, p1, p2, compare_role, df_comp)
        st.download_button(
            label="⬇ Descargar imagen",
            data=img_bytes,
            file_name=f"{p1.replace(' ', '_')}_vs_{p2.replace(' ', '_')}.png",
            mime="image/png",
        )
    else:
        # Mostrar cada uno por separado
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**{p1} — {role1}**")
            role_key = "batting" if role1 == "batter" else "pitching"
            st.json(d1.get(role_key, {}))
        with c2:
            st.markdown(f"**{p2} — {role2}**")
            role_key = "batting" if role2 == "batter" else "pitching"
            st.json(d2.get(role_key, {}))

# ── TAB 3: Defensa ────────────────────────────────────────────────────────────
with tab_field:
    c1, c2 = st.columns(2)
    for col, player, data in [(c1, p1, d1), (c2, p2, d2)]:
        with col:
            st.markdown(f"**{player}**")
            frows = data.get("fielding", [])
            if frows:
                st.dataframe(pd.DataFrame(frows), use_container_width=True, hide_index=True)
            else:
                st.caption("Sin datos defensivos disponibles.")

# ── TAB 4: Sprint Speed ───────────────────────────────────────────────────────
with tab_speed:
    df_sprint = build_sprint_row(d1, d2, p1, p2)
    st.dataframe(df_sprint, use_container_width=True, hide_index=True)

    # Gauge visual simple
    s1 = d1.get("sprint", {}).get("sprint_speed")
    s2 = d2.get("sprint", {}).get("sprint_speed")
    if s1 and s2:
        import plotly.graph_objects as go
        fig_speed = go.Figure()
        fig_speed.add_trace(go.Bar(
            x=[p1, p2], y=[s1, s2],
            marker_color=["#E63946", "#457B9D"],
            text=[f"{s1} ft/s", f"{s2} ft/s"],
            textposition="outside"
        ))
        fig_speed.update_layout(
            title="Sprint Speed (ft/s) — promedio temporada",
            yaxis=dict(range=[25, 32]),
            height=350,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_speed, use_container_width=True)
        st.caption("Promedio MLB ≈ 27.0 ft/s · Elite: 30+ ft/s")