import streamlit as st
import pandas as pd
from data_loader import (
    load_batting, load_pitching, load_fielding, load_sprint,
    load_batting_expected, load_pitching_expected,
    load_batting_exitvelo, load_pitching_exitvelo,
    get_player_data, detect_role, SEASON
)
from components import (
    build_radar, build_comparison_table, build_comparison_image, build_sprint_row
)

# ── Configuración de Página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Vision 360 — Baseball Player Comparison",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .badge-p1 {
        background-color: #E63946;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.95rem;
    }
    .badge-p2 {
        background-color: #457B9D;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.95rem;
    }
    .author-badge {
        font-size: 0.85rem;
        color: #94A3B8;
        padding-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ── Carga de datos ───────────────────────────────────────────────────────────
with st.spinner("Cargando datos MLB (Baseball Reference + Statcast)..."):
    bat_df     = load_batting()
    pit_df     = load_pitching()
    field_df   = load_fielding()
    sprint_df  = load_sprint()
    bat_exp_df = load_batting_expected()
    pit_exp_df = load_pitching_expected()
    bat_ev_df  = load_batting_exitvelo()
    pit_ev_df  = load_pitching_exitvelo()

all_batters  = sorted(bat_df["Name"].dropna().unique().tolist()) if not bat_df.empty else []
all_pitchers = sorted(pit_df["Name"].dropna().unique().tolist()) if not pit_df.empty else []
all_players  = sorted(set(all_batters + all_pitchers))

if not all_players:
    st.error(
        "No se pudieron cargar jugadores de FanGraphs / Baseball Reference. "
        "Verifica la conexión a internet o ejecuta `python refresh_data.py` localmente."
    )
    st.stop()

# ── Sidebar: Filtros y Autoría ───────────────────────────────────────────────
st.sidebar.image("https://midfield.mlbstatic.com/v1/league/103/spots/72", width=65)
st.sidebar.title("⚾ Vision 360")
st.sidebar.caption(f"Temporada MLB {SEASON} · Statcast & Sabermetrics")

st.sidebar.markdown("### 🔍 Filtros de Búsqueda")
role_filter = st.sidebar.selectbox(
    "Filtrar jugadores por rol:",
    ["Todos", "Solo Bateadores", "Solo Lanzadores"],
    index=0
)

# Obtener lista de equipos únicos disponibles
all_teams = set()
if not bat_df.empty and "Team" in bat_df.columns:
    all_teams.update(bat_df["Team"].dropna().unique())
if not pit_df.empty and "Team" in pit_df.columns:
    all_teams.update(pit_df["Team"].dropna().unique())
teams_list = ["Todos los equipos"] + sorted(list(all_teams))

team_filter = st.sidebar.selectbox("Filtrar por equipo:", teams_list, index=0)

# Aplicar filtros a la lista de opciones
filtered_players = all_players.copy()

if role_filter == "Solo Bateadores":
    filtered_players = [p for p in filtered_players if p in all_batters]
elif role_filter == "Solo Lanzadores":
    filtered_players = [p for p in filtered_players if p in all_pitchers]

if team_filter != "Todos los equipos":
    p_teams = set()
    if not bat_df.empty and "Team" in bat_df.columns:
        p_teams.update(bat_df[bat_df["Team"] == team_filter]["Name"].tolist())
    if not pit_df.empty and "Team" in pit_df.columns:
        p_teams.update(pit_df[pit_df["Team"] == team_filter]["Name"].tolist())
    filtered_players = [p for p in filtered_players if p in p_teams]

if not filtered_players:
    st.sidebar.warning("No hay jugadores que coincidan con los filtros seleccionados.")
    filtered_players = all_players

# Acciones de datos en Sidebar
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Recargar Datos (Limpiar Caché)", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Autoría en Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(
    "👨‍💻 **Desarrollado por Jorge Leonardo Loreto**  \n"
    "*Data Scientist & Baseball Analytics*  \n"
    "[GitHub](https://github.com/jloreto9) · [Portafolio](https://jloreto9.github.io)"
)

# ── Header ───────────────────────────────────────────────────────────────────
st.title("⚾ Vision 360 — MLB Player Comparison")
st.caption(f"Comparación head-to-head integral · Temporada MLB {SEASON} · Desarrollado por **Jorge Leonardo Loreto**")

# ── Selección de jugadores ───────────────────────────────────────────────────
col1, col_vs, col2 = st.columns([5, 1, 5])

with col1:
    p1 = st.selectbox("🔴 Jugador 1 (Rojo)", filtered_players, index=0, key="p1")

with col_vs:
    st.markdown("<br><h2 style='text-align:center; color:#94A3B8;'>VS</h2>", unsafe_allow_html=True)

with col2:
    default_idx = min(1, len(filtered_players) - 1)
    if len(filtered_players) > 1 and filtered_players[default_idx] == p1:
        default_idx = 1 if len(filtered_players) > 1 else 0
    p2 = st.selectbox("🔵 Jugador 2 (Azul)", filtered_players, index=default_idx, key="p2")

if p1 == p2:
    st.warning("Selecciona dos jugadores distintos para realizar la comparación.")
    st.stop()

# ── Obtener datos ─────────────────────────────────────────────────────────────
d1 = get_player_data(p1, bat_df, pit_df, field_df, sprint_df, bat_exp_df, pit_exp_df, bat_ev_df, pit_ev_df)
d2 = get_player_data(p2, bat_df, pit_df, field_df, sprint_df, bat_exp_df, pit_exp_df, bat_ev_df, pit_ev_df)

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
    st.info(f"**{p1}** ({role1.upper()}) y **{p2}** ({role2.upper()}) tienen roles distintos. Mostrando estadísticas individuales.")
    compare_role = "mixed"

# ── Matchup Header Cards con Headshots oficiales de MLB y Logos de Franquicia ──
c1, _, c2 = st.columns([5, 1, 5])

with c1:
    col_img, col_info = st.columns([1, 3])
    with col_img:
        if d1.get("headshot_url"):
            st.image(d1["headshot_url"], width=95)
        else:
            st.markdown("<div style='font-size:3.5rem;'>👤</div>", unsafe_allow_html=True)
    with col_info:
        st.markdown(f"### <span class='badge-p1'>🔴 {p1}</span>", unsafe_allow_html=True)
        d1_stats = d1.get("batting", {}) or d1.get("pitching", {})
        team1 = d1.get("team") or d1_stats.get("Team", "—")
        pos1 = d1_stats.get("Pos", role1.upper())
        logo1 = d1.get("team_logo_url")
        
        if logo1:
            st.markdown(
                f"<div style='display: flex; align-items: center; gap: 8px; margin-top: -4px; margin-bottom: 4px;'>"
                f"<img src='{logo1}' width='32' height='32' style='object-fit: contain; vertical-align: middle;' />"
                f"<span style='font-size: 1.05rem; font-weight: 600; color: #F1F5F9;'>{team1}</span>"
                f"</div>"
                f"<div style='font-size: 0.88rem; color: #94A3B8; margin-top: 2px;'>"
                f"Posición / Rol: <b style='color: #E2E8F0;'>{pos1}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"**Equipo:** `{team1}`  \n**Posición:** `{pos1}`")

with c2:
    col_img, col_info = st.columns([1, 3])
    with col_img:
        if d2.get("headshot_url"):
            st.image(d2["headshot_url"], width=95)
        else:
            st.markdown("<div style='font-size:3.5rem;'>👤</div>", unsafe_allow_html=True)
    with col_info:
        st.markdown(f"### <span class='badge-p2'>🔵 {p2}</span>", unsafe_allow_html=True)
        d2_stats = d2.get("batting", {}) or d2.get("pitching", {})
        team2 = d2.get("team") or d2_stats.get("Team", "—")
        pos2 = d2_stats.get("Pos", role2.upper())
        logo2 = d2.get("team_logo_url")
        
        if logo2:
            st.markdown(
                f"<div style='display: flex; align-items: center; gap: 8px; margin-top: -4px; margin-bottom: 4px;'>"
                f"<img src='{logo2}' width='32' height='32' style='object-fit: contain; vertical-align: middle;' />"
                f"<span style='font-size: 1.05rem; font-weight: 600; color: #F1F5F9;'>{team2}</span>"
                f"</div>"
                f"<div style='font-size: 0.88rem; color: #94A3B8; margin-top: 2px;'>"
                f"Posición / Rol: <b style='color: #E2E8F0;'>{pos2}</b>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"**Equipo:** `{team2}`  \n**Posición:** `{pos2}`")

st.divider()

# ── Tabs de Análisis ──────────────────────────────────────────────────────────
tab_radar, tab_stats, tab_diff, tab_field, tab_speed = st.tabs([
    "🕸️ Radar 360", "📊 Stats Comparados", "⚡ Statcast & Regresión", "🧤 Defensa", "💨 Velocidad"
])

# ── TAB 1: Radar ──────────────────────────────────────────────────────────────
with tab_radar:
    if compare_role not in ("mixed",):
        fig = build_radar(d1, d2, p1, p2, compare_role)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "💡 **Escala Sabermétrica:** Los valores están normalizados al rango percentil 0–100 de Statcast. "
            "Un valor de 90+ representa rendimiento de élite (top 10% de la MLB)."
        )
    else:
        st.info("El Radar 360 se activa cuando ambos jugadores comparten rol (Bateador vs Bateador o Lanzador vs Lanzador).")

# ── TAB 2: Stats Comparados ───────────────────────────────────────────────────
with tab_stats:
    if compare_role != "mixed":
        df_comp = build_comparison_table(d1, d2, p1, p2, compare_role)

        # Conteo de ventajas
        p1_wins = (df_comp["Ventaja"] == p1).sum()
        p2_wins = (df_comp["Ventaja"] == p2).sum()
        ties = (df_comp["Ventaja"] == "Igual").sum()

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric(f"Ventajas {p1}", f"{p1_wins} métricas", delta=f"{p1_wins - p2_wins:+d}" if p1_wins != p2_wins else None)
        with k2:
            st.metric("Empates / Similares", f"{ties} métricas")
        with k3:
            st.metric(f"Ventajas {p2}", f"{p2_wins} métricas", delta=f"{p2_wins - p1_wins:+d}" if p2_wins != p1_wins else None)

        def highlight_winner(row):
            styles = ["", "", "", "", ""]
            if row["Ventaja"] == p1:
                styles[2] = "color: #EF4444; font-weight: bold; background-color: rgba(239, 68, 68, 0.1);"
            elif row["Ventaja"] == p2:
                styles[3] = "color: #38BDF8; font-weight: bold; background-color: rgba(56, 189, 248, 0.1);"
            return styles

        st.dataframe(
            df_comp.style.apply(highlight_winner, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        img_bytes = build_comparison_image(d1, d2, p1, p2, compare_role, df_comp)
        st.download_button(
            label="⬇ Descargar Tarjeta Comparativa con Fotos (PNG)",
            data=img_bytes,
            file_name=f"{p1.replace(' ', '_')}_vs_{p2.replace(' ', '_')}.png",
            mime="image/png",
        )
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**{p1} — {role1.upper()}**")
            role_key = "batting" if role1 == "batter" else "pitching"
            st.json(d1.get(role_key, {}))
        with c2:
            st.markdown(f"**{p2} — {role2.upper()}**")
            role_key = "batting" if role2 == "batter" else "pitching"
            st.json(d2.get(role_key, {}))

# ── TAB 3: Statcast & Regresión ───────────────────────────────────────────────
with tab_diff:
    st.markdown("### ⚡ Calidad de Contacto y Métricas Esperadas (Statcast)")
    st.caption("Diferenciales entre resultados observados y rendimiento esperado según Statcast (velocidad de salida y ángulo de lanzamiento).")

    if compare_role == "batter":
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown(f"#### 🔴 {p1}")
            b1 = d1.get("batting", {})
            st.markdown(f"- **AVG:** `{b1.get('AVG', 'N/D')}` vs **xBA:** `{b1.get('V_xBA', 'N/D')}` *(diff: {b1.get('V_diff_BA', 'N/D')})*")
            st.markdown(f"- **SLG:** `{b1.get('SLG', 'N/D')}` vs **xSLG:** `{b1.get('V_xSLG', 'N/D')}` *(diff: {b1.get('V_diff_SLG', 'N/D')})*")
            st.markdown(f"- **OBP:** `{b1.get('OBP', 'N/D')}` vs **xwOBA:** `{b1.get('V_xwOBA', 'N/D')}` *(diff: {b1.get('V_diff_wOBA', 'N/D')})*")
            st.markdown(f"- **Exit Velocity:** `{b1.get('V_EV', 'N/D')}` · **Barrel%:** `{b1.get('V_Barrel', 'N/D')}` · **HardHit%:** `{b1.get('V_HardHit', 'N/D')}`")
        with col_b2:
            st.markdown(f"#### 🔵 {p2}")
            b2 = d2.get("batting", {})
            st.markdown(f"- **AVG:** `{b2.get('AVG', 'N/D')}` vs **xBA:** `{b2.get('V_xBA', 'N/D')}` *(diff: {b2.get('V_diff_BA', 'N/D')})*")
            st.markdown(f"- **SLG:** `{b2.get('SLG', 'N/D')}` vs **xSLG:** `{b2.get('V_xSLG', 'N/D')}` *(diff: {b2.get('V_diff_SLG', 'N/D')})*")
            st.markdown(f"- **OBP:** `{b2.get('OBP', 'N/D')}` vs **xwOBA:** `{b2.get('V_xwOBA', 'N/D')}` *(diff: {b2.get('V_diff_wOBA', 'N/D')})*")
            st.markdown(f"- **Exit Velocity:** `{b2.get('V_EV', 'N/D')}` · **Barrel%:** `{b2.get('V_Barrel', 'N/D')}` · **HardHit%:** `{b2.get('V_HardHit', 'N/D')}`")
    elif compare_role == "pitcher":
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"#### 🔴 {p1}")
            pit1 = d1.get("pitching", {})
            st.markdown(f"- **ERA:** `{pit1.get('ERA', 'N/D')}` vs **xERA:** `{pit1.get('V_xERA', 'N/D')}` *(diff: {pit1.get('V_diff_ERA', 'N/D')})*")
            st.markdown(f"- **xwOBA (permitido):** `{pit1.get('V_xwOBA', 'N/D')}` · **Exit Velo (permitida):** `{pit1.get('V_EV', 'N/D')}`")
        with col_p2:
            st.markdown(f"#### 🔵 {p2}")
            pit2 = d2.get("pitching", {})
            st.markdown(f"- **ERA:** `{pit2.get('ERA', 'N/D')}` vs **xERA:** `{pit2.get('V_xERA', 'N/D')}` *(diff: {pit2.get('V_diff_ERA', 'N/D')})*")
            st.markdown(f"- **xwOBA (permitido):** `{pit2.get('V_xwOBA', 'N/D')}` · **Exit Velo (permitida):** `{pit2.get('V_EV', 'N/D')}`")
    else:
        st.info("Selecciona jugadores con el mismo rol para comparar sus métricas de Statcast y regresión.")

# ── TAB 4: Defensa ────────────────────────────────────────────────────────────
with tab_field:
    c1, c2 = st.columns(2)
    for col, player, data in [(c1, p1, d1), (c2, p2, d2)]:
        with col:
            st.markdown(f"### **{player}**")
            frows = data.get("fielding", [])
            if frows:
                st.dataframe(pd.DataFrame(frows), use_container_width=True, hide_index=True)
            else:
                st.caption("Sin registros defensivos de Statcast OAA disponibles.")

# ── TAB 5: Sprint Speed ───────────────────────────────────────────────────────
with tab_speed:
    df_sprint = build_sprint_row(d1, d2, p1, p2)
    st.dataframe(df_sprint, use_container_width=True, hide_index=True)

    s1 = d1.get("sprint", {}).get("sprint_speed")
    s2 = d2.get("sprint", {}).get("sprint_speed")
    if s1 is not None and s2 is not None and str(s1) != "nan" and str(s2) != "nan":
        try:
            s1_f, s2_f = float(s1), float(s2)
            import plotly.graph_objects as go
            fig_speed = go.Figure()
            fig_speed.add_trace(go.Bar(
                y=[f"🔵 {p2}", f"🔴 {p1}"],
                x=[s2_f, s1_f],
                orientation="h",
                marker=dict(
                    color=["#457B9D", "#E63946"],
                    line=dict(color="rgba(255, 255, 255, 0.2)", width=1)
                ),
                text=[f" {s2_f:.1f} ft/s", f" {s1_f:.1f} ft/s"],
                textposition="outside",
                cliponaxis=False,
            ))
            # Líneas de referencia sabermétrica
            fig_speed.add_vline(x=27.0, line_dash="dash", line_color="rgba(255, 255, 255, 0.4)", annotation_text="Promedio MLB (27.0)", annotation_position="top left", annotation_font_color="#CBD5E1")
            fig_speed.add_vline(x=30.0, line_dash="dash", line_color="#FDB827", annotation_text="Élite (30.0+)", annotation_position="top right", annotation_font_color="#FDB827")

            fig_speed.update_layout(
                title=dict(text="💨 Comparativa de Velocidad de Sprint (Statcast ft/s)", font=dict(size=16, color="#FFFFFF")),
                xaxis=dict(
                    range=[22, 32],
                    dtick=2,
                    gridcolor="rgba(255, 255, 255, 0.12)",
                    title=dict(text="Velocidad (Pies por segundo / ft/s)", font=dict(color="#94A3B8")),
                    tickfont=dict(color="#E2E8F0"),
                ),
                yaxis=dict(
                    tickfont=dict(color="#FFFFFF", size=13, family="sans-serif"),
                    autorange="reversed"  # Muestra P1 arriba y P2 abajo
                ),
                height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.3)",
                font=dict(color="#FFFFFF"),
                margin=dict(l=30, r=50, t=50, b=30),
            )
            st.plotly_chart(fig_speed, use_container_width=True)
        except (ValueError, TypeError):
            st.caption("Datos de Sprint Speed no numéricos.")

# Footer de autoría
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748B; font-size: 0.85rem;'>"
    "⚾ <b>Vision 360</b> · Desarrollado por <b>Jorge Leonardo Loreto</b> · Economista & Data Scientist · MLB Sabermetrics"
    "</div>",
    unsafe_allow_html=True
)