import plotly.graph_objects as go
import pandas as pd
import numpy as np


RADAR_METRICS_BAT = {
    "wRC+": {"higher_is_better": True, "scale": (0, 200)},
    "OBP":  {"higher_is_better": True, "scale": (0.200, 0.500)},
    "SLG":  {"higher_is_better": True, "scale": (0.200, 0.700)},
    "ISO":  {"higher_is_better": True, "scale": (0.000, 0.350)},
    "BB%":  {"higher_is_better": True, "scale": (0.03, 0.20)},
    "K%":   {"higher_is_better": False, "scale": (0.05, 0.40)},
    "BABIP":{"higher_is_better": True, "scale": (0.200, 0.420)},
    "BsR":  {"higher_is_better": True, "scale": (-5, 15)},
    "Def":  {"higher_is_better": True, "scale": (-20, 20)},
    "WAR":  {"higher_is_better": True, "scale": (-1, 10)},
}

RADAR_METRICS_PIT = {
    "ERA-":   {"higher_is_better": False, "scale": (40, 160)},
    "FIP-":   {"higher_is_better": False, "scale": (40, 160)},
    "K/9":    {"higher_is_better": True,  "scale": (3, 16)},
    "BB/9":   {"higher_is_better": False, "scale": (1, 6)},
    "HR/9":   {"higher_is_better": False, "scale": (0, 2.5)},
    "SwStr%": {"higher_is_better": True,  "scale": (0.04, 0.20)},
    "BABIP":  {"higher_is_better": False, "scale": (0.200, 0.380)},
    "LOB%":   {"higher_is_better": True,  "scale": (0.50, 0.90)},
    "WAR":    {"higher_is_better": True,  "scale": (-1, 8)},
}


def _normalize(value, low, high, higher_is_better):
    """Normaliza a 0–100."""
    if pd.isna(value):
        return 50  # neutro
    clipped = max(low, min(high, value))
    pct = (clipped - low) / (high - low) * 100
    return pct if higher_is_better else 100 - pct


def build_radar(p1_data: dict, p2_data: dict, name1: str, name2: str, role: str) -> go.Figure:
    metrics = RADAR_METRICS_BAT if role == "batter" else RADAR_METRICS_PIT
    data_key = "batting" if role == "batter" else "pitching"

    d1 = p1_data.get(data_key, {})
    d2 = p2_data.get(data_key, {})

    labels = list(metrics.keys())
    vals1, vals2 = [], []

    for m, cfg in metrics.items():
        low, high = cfg["scale"]
        hib = cfg["higher_is_better"]
        vals1.append(_normalize(d1.get(m, np.nan), low, high, hib))
        vals2.append(_normalize(d2.get(m, np.nan), low, high, hib))

    # Cerrar el polígono
    labels  += [labels[0]]
    vals1   += [vals1[0]]
    vals2   += [vals2[0]]

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

    all_keys = list(metrics_cfg.keys())
    # Agregar stats extra que no están en el radar pero sí son relevantes
    extra = ["G", "PA", "HR", "RBI", "SB", "AVG", "wOBA", "Off"] if role == "batter" \
        else ["G", "GS", "IP", "W", "L", "SV", "xFIP", "K%", "BB%"]

    rows = []
    for k in all_keys + extra:
        v1 = d1.get(k, None)
        v2 = d2.get(k, None)
        hib = metrics_cfg.get(k, {}).get("higher_is_better", True)

        if v1 is not None and v2 is not None:
            try:
                winner = name1 if (float(v1) > float(v2)) == hib else name2
            except Exception:
                winner = "—"
        else:
            winner = "—"

        rows.append({
            "Stat": k,
            name1: v1,
            name2: v2,
            "Ventaja": winner,
        })

    return pd.DataFrame(rows)


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