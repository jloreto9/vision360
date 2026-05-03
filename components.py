import plotly.graph_objects as go
import pandas as pd
import numpy as np


# Statcast percentile ranks: escala 0-100, mayor = mejor en todos los casos
# (Baseball Savant invierte las métricas "negativas" para que siempre aplique
# mayor percentile = mejor jugador)

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


def _normalize(value, low, high, higher_is_better):
    if pd.isna(value):
        return 50
    clipped = max(low, min(high, value))
    pct = (clipped - low) / (high - low) * 100
    return pct if higher_is_better else 100 - pct


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

    # Cerrar el polígono
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

    # Stats base (no están en el radar pero son relevantes para la tabla)
    extra_bat = ["G", "PA", "HR", "R", "RBI", "SB", "AVG", "OBP", "SLG", "OPS", "BB%", "K%", "ISO"]
    extra_pit = ["G", "GS", "IP", "W", "L", "SV", "ERA", "WHIP", "K/9", "BB/9", "HR/9", "BABIP"]
    extra = extra_bat if role == "batter" else extra_pit

    rows = []
    for k, cfg in metrics_cfg.items():
        label = cfg.get("label", k)
        v1 = d1.get(k)
        v2 = d2.get(k)
        hib = cfg.get("higher_is_better", True)
        winner = _winner(v1, v2, hib, name1, name2)
        rows.append({"Stat": label, name1: v1, name2: v2, "Ventaja": winner})

    for k in extra:
        v1 = d1.get(k)
        v2 = d2.get(k)
        winner = _winner(v1, v2, True, name1, name2)
        rows.append({"Stat": k, name1: v1, name2: v2, "Ventaja": winner})

    return pd.DataFrame(rows)


def _winner(v1, v2, higher_is_better: bool, name1: str, name2: str) -> str:
    if v1 is None or v2 is None:
        return "—"
    try:
        return name1 if (float(v1) > float(v2)) == higher_is_better else name2
    except Exception:
        return "—"


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
