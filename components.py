import plotly.graph_objects as go
import pandas as pd
import numpy as np


# Statcast percentile ranks: escala 0-100, mayor = mejor en todos los casos
RADAR_METRICS_BAT = {
    "P_xwOBA":   {"higher_is_better": True, "scale": (0, 100), "label": "xwOBA"},
    "P_Barrel":  {"higher_is_better": True, "scale": (0, 100), "label": "Barrel%"},
    "P_EV":      {"higher_is_better": True, "scale": (0, 100), "label": "Exit Velo"},
    "P_HardHit": {"higher_is_better": True, "scale": (0, 100), "label": "Hard Hit%"},
    "P_Whiff":   {"higher_is_better": True, "scale": (0, 100), "label": "Whiff%"},
    "P_K":       {"higher_is_better": True, "scale": (0, 100), "label": "K% (bat)"},
    "P_BB":      {"higher_is_better": True, "scale": (0, 100), "label": "BB%"},
}

RADAR_METRICS_PIT = {
    "P_xERA":   {"higher_is_better": True, "scale": (0, 100), "label": "xERA"},
    "P_xwOBA":  {"higher_is_better": True, "scale": (0, 100), "label": "xwOBA"},
    "P_FBVelo": {"higher_is_better": True, "scale": (0, 100), "label": "FB Velo"},
    "P_K":      {"higher_is_better": True, "scale": (0, 100), "label": "K%"},
    "P_BB":     {"higher_is_better": True, "scale": (0, 100), "label": "BB%"},
    "P_Whiff":  {"higher_is_better": True, "scale": (0, 100), "label": "Whiff%"},
    "P_Barrel": {"higher_is_better": True, "scale": (0, 100), "label": "Barrel%"},
}

# ── Formateo de valores ─────────────────────────────────────────────────────

_INT_STATS   = {"G", "PA", "HR", "R", "RBI", "SB", "GS", "W", "L", "SV"}
_RATE3_STATS = {"AVG", "OBP", "SLG", "OPS", "ISO", "BABIP"}
_RATE2_STATS = {"ERA", "WHIP", "K/9", "BB/9", "HR/9"}
_PCT_STATS   = {"BB%", "K%"}   # almacenados como fracción (0.085) → mostrar "8.5%"


def _fmt(stat: str, value) -> str:
    """Formatea un valor para mostrar en tabla. INT, float o percentil."""
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "N/D"
        if stat.startswith("P_"):
            return str(int(round(float(value))))
        if stat in _INT_STATS:
            return str(int(round(float(value))))
        if stat in _RATE3_STATS:
            return f"{float(value):.3f}"
        if stat in _PCT_STATS:
            return f"{float(value) * 100:.1f}%"
        if stat in _RATE2_STATS:
            return f"{float(value):.2f}"
        if stat == "IP":
            return f"{float(value):.1f}"
        return str(value)
    except (ValueError, TypeError):
        return "N/D"


# ── Helpers internos ────────────────────────────────────────────────────────

def _normalize(value, low, high, higher_is_better):
    if pd.isna(value):
        return 50
    clipped = max(low, min(high, value))
    pct = (clipped - low) / (high - low) * 100
    return pct if higher_is_better else 100 - pct


def _winner(v1, v2, higher_is_better: bool, name1: str, name2: str) -> str:
    if v1 is None or v2 is None:
        return "—"
    try:
        return name1 if (float(v1) > float(v2)) == higher_is_better else name2
    except (ValueError, TypeError):
        return "—"


# ── Visualizaciones ─────────────────────────────────────────────────────────

def build_radar(p1_data: dict, p2_data: dict, name1: str, name2: str, role: str) -> go.Figure:
    metrics = RADAR_METRICS_BAT if role == "batter" else RADAR_METRICS_PIT
    data_key = "batting" if role == "batter" else "pitching"

    d1 = p1_data.get(data_key, {})
    d2 = p2_data.get(data_key, {})

    labels = [cfg.get("label", m) for m, cfg in metrics.items()]
    vals1, vals2 = [], []

    for m, cfg in metrics.items():
        low, high = cfg["scale"]
        hib = cfg["higher_is_better"]
        vals1.append(_normalize(d1.get(m, np.nan), low, high, hib))
        vals2.append(_normalize(d2.get(m, np.nan), low, high, hib))

    labels += [labels[0]]
    vals1  += [vals1[0]]
    vals2  += [vals2[0]]

    fig = go.Figure()
    for vals, name, color in [
        (vals1, name1, "#E63946"),
        (vals2, name2, "#457B9D"),
    ]:
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=labels, fill="toself",
            name=name, line_color=color,
            fillcolor=color.replace(")", ", 0.15)").replace("rgb", "rgba"),
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
    )
    return fig


def build_comparison_table(p1_data: dict, p2_data: dict,
                            name1: str, name2: str, role: str) -> pd.DataFrame:
    data_key = "batting" if role == "batter" else "pitching"
    metrics_cfg = RADAR_METRICS_BAT if role == "batter" else RADAR_METRICS_PIT

    d1 = p1_data.get(data_key, {})
    d2 = p2_data.get(data_key, {})

    extra_bat = ["G", "PA", "HR", "R", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "BB%", "K%", "ISO"]
    extra_pit = ["G", "GS", "IP", "W", "L", "SV", "ERA", "WHIP", "K/9", "BB/9", "HR/9", "BABIP"]
    extra = extra_bat if role == "batter" else extra_pit

    rows = []
    for k, cfg in metrics_cfg.items():
        label = cfg.get("label", k)
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg.get("higher_is_better", True), name1, name2)
        rows.append({"Stat": label, name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    for k in extra:
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, k not in {"K%"}, name1, name2)
        rows.append({"Stat": k, name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    return pd.DataFrame(rows)


def build_comparison_image(p1_data: dict, p2_data: dict,
                            name1: str, name2: str, role: str,
                            df_comp: pd.DataFrame) -> bytes:
    """Genera PNG descargable con la tarjeta de comparacion."""
    data_key = "batting" if role == "batter" else "pitching"
    d1_stats = p1_data.get(data_key, {})
    d2_stats = p2_data.get(data_key, {})
    team1 = d1_stats.get("Team", "—")
    team2 = d2_stats.get("Team", "—")

    stats   = df_comp["Stat"].tolist()
    vals1   = df_comp[name1].astype(str).replace("nan", "N/D").tolist()
    vals2   = df_comp[name2].astype(str).replace("nan", "N/D").tolist()
    winners = df_comp["Ventaja"].tolist()

    DARK    = "#0e1117"
    ROW_ALT = "#1a1a2e"
    RED     = "#E63946"
    BLUE    = "#457B9D"
    WHITE   = "#ffffff"
    GRAY    = "#888888"

    bg1, bg2, bg_s = [], [], []
    fc1, fc2 = [], []
    for i, w in enumerate(winners):
        bg = ROW_ALT if i % 2 == 0 else DARK
        bg1.append(bg); bg2.append(bg); bg_s.append(bg)
        fc1.append(RED  if w == name1 else WHITE)
        fc2.append(BLUE if w == name2 else WHITE)

    fig = go.Figure(data=[go.Table(
        columnwidth=[2, 2, 2],
        header=dict(
            values=[
                f"<b>{name1}</b><br><span style='font-size:11px'>{team1} · {role.upper()}</span>",
                "<b>STAT</b>",
                f"<b>{name2}</b><br><span style='font-size:11px'>{team2} · {role.upper()}</span>",
            ],
            fill_color=[RED, DARK, BLUE],
            align="center",
            font=dict(color=WHITE, size=13),
            line_color="#222",
            height=48,
        ),
        cells=dict(
            values=[vals1, stats, vals2],
            fill_color=[bg1, bg_s, bg2],
            align="center",
            font=dict(color=[fc1, [GRAY] * len(stats), fc2], size=12),
            line_color="#222",
            height=26,
        ),
    )])

    fig.update_layout(
        width=560,
        height=58 + len(stats) * 26 + 30,
        margin=dict(l=4, r=4, t=30, b=4),
        paper_bgcolor=DARK,
        title=dict(text="⚾ Vision 360", font=dict(color=GRAY, size=11), x=0.5),
    )
    return fig.to_image(format="png")


def build_sprint_row(p1_data: dict, p2_data: dict, name1: str, name2: str) -> pd.DataFrame:
    s1 = p1_data.get("sprint", {})
    s2 = p2_data.get("sprint", {})
    rows = []
    for key, label in [("sprint_speed", "Sprint Speed (ft/s)"), ("hp_to_1b", "HP→1B (seg)")]:
        rows.append({
            "Métrica": label,
            name1: s1.get(key, "N/D"),
            name2: s2.get(key, "N/D"),
        })
    return pd.DataFrame(rows)
