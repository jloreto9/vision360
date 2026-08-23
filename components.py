import io
import os
import plotly.graph_objects as go
import pandas as pd
import numpy as np


# ── Métricas del radar (Statcast percentile ranks 0-100, mayor = mejor) ──────

RADAR_METRICS_BAT = {
    "P_xwOBA":   {"higher_is_better": True, "scale": (0, 100), "label": "xwOBA"},
    "P_Barrel":  {"higher_is_better": True, "scale": (0, 100), "label": "Barrel%"},
    "P_EV":      {"higher_is_better": True, "scale": (0, 100), "label": "Exit Velo"},
    "P_HardHit": {"higher_is_better": True, "scale": (0, 100), "label": "Hard Hit%"},
    "P_Whiff":   {"higher_is_better": True, "scale": (0, 100), "label": "Whiff%"},
    "P_K":       {"higher_is_better": True, "scale": (0, 100), "label": "K%"},
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

# Counting stats que aparecen en la tabla pero no en el radar
_EXTRA_BAT = ["G", "PA", "HR", "R", "RBI", "SB"]
_EXTRA_PIT = ["G", "GS", "IP", "W", "L", "SV"]

# Stats tradicionales de rate (batting)
_TRAD_BAT = {
    "AVG":   {"label": "AVG",   "higher_is_better": True},
    "OBP":   {"label": "OBP",   "higher_is_better": True},
    "SLG":   {"label": "SLG",   "higher_is_better": True},
    "OPS":   {"label": "OPS",   "higher_is_better": True},
    "ISO":   {"label": "ISO",   "higher_is_better": True},
    "BB%":   {"label": "BB%",   "higher_is_better": True},
    "K%":    {"label": "K%",    "higher_is_better": False},
}

# Stats tradicionales de rate (pitching)
_TRAD_PIT = {
    "ERA":   {"label": "ERA",   "higher_is_better": False},
    "WHIP":  {"label": "WHIP",  "higher_is_better": False},
    "K/9":   {"label": "K/9",   "higher_is_better": True},
    "BB/9":  {"label": "BB/9",  "higher_is_better": False},
    "HR/9":  {"label": "HR/9",  "higher_is_better": False},
    "BABIP": {"label": "BABIP", "higher_is_better": False},
}

# Valores reales Statcast (calidad de contacto y métricas esperadas)
_STATCAST_BAT = {
    "V_xBA":     {"label": "xBA",        "higher_is_better": True},
    "V_xSLG":    {"label": "xSLG",       "higher_is_better": True},
    "V_xwOBA":   {"label": "xwOBA",      "higher_is_better": True},
    "V_EV":      {"label": "Exit Velo",  "higher_is_better": True},
    "V_Barrel":  {"label": "Barrel%",    "higher_is_better": True},
    "V_HardHit": {"label": "Hard Hit%",  "higher_is_better": True},
    "V_Whiff":   {"label": "Whiff%",     "higher_is_better": False},
}

_DIFF_BAT = {
    "V_diff_BA":   {"label": "diff (BA - xBA)",     "higher_is_better": False, "note": "Negativo = mala suerte (Buy-Low)"},
    "V_diff_SLG":  {"label": "diff (SLG - xSLG)",   "higher_is_better": False, "note": "Negativo = mala suerte (Buy-Low)"},
    "V_diff_wOBA": {"label": "diff (OBP - xwOBA)",  "higher_is_better": False, "note": "Negativo = mala suerte (Buy-Low)"},
}

_STATCAST_PIT = {
    "V_xERA":    {"label": "xERA",            "higher_is_better": False},
    "V_xwOBA":   {"label": "xwOBA (rec)",     "higher_is_better": False},
    "V_EV":      {"label": "EV (rec)",        "higher_is_better": False},
    "V_Barrel":  {"label": "Barrel% (rec)",   "higher_is_better": False},
    "V_HardHit": {"label": "Hard Hit% (rec)", "higher_is_better": False},
    "V_Whiff":   {"label": "Whiff%",          "higher_is_better": True},
}

_DIFF_PIT = {
    "V_diff_ERA":  {"label": "diff (ERA - xERA)", "higher_is_better": True, "note": "Positivo = ERA inflada / mala suerte"},
}

# ── Formateo de valores ─────────────────────────────────────────────────────

_INT_STATS   = {"G", "PA", "HR", "R", "RBI", "SB", "GS", "W", "L", "SV"}
_RATE3_STATS = {"AVG", "OBP", "SLG", "OPS", "ISO", "BABIP"}
_RATE2_STATS = {"ERA", "WHIP", "K/9", "BB/9", "HR/9"}
_PCT_STATS   = {"BB%", "K%"}


def _fmt(stat: str, value) -> str:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)) or str(value).strip() in ("", "nan", "<NA>"):
            return "N/D"
        if stat.startswith("P_"):
            return str(int(round(float(value))))
        if stat.startswith("V_diff_"):
            v = float(value)
            sign = "+" if v > 0 else ""
            if "ERA" in stat:
                return f"{sign}{v:.2f}"
            return f"{sign}{v:.3f}"
        if stat.startswith("V_"):
            v = float(value)
            if stat in {"V_xwOBA", "V_xBA", "V_xSLG"}:
                s = f"{v:.3f}"
                return s[1:] if s.startswith("0.") else s
            if stat in {"V_xERA"}:
                return f"{v:.2f}"
            if stat in {"V_EV", "V_FBVelo"}:
                return f"{v:.1f} mph"
            return f"{v:.1f}%"
        if stat in _INT_STATS:
            return str(int(round(float(value))))
        if stat in _RATE3_STATS:
            s = f"{float(value):.3f}"
            return s[1:] if s.startswith("0.") else s
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
    clipped = max(low, min(high, float(value)))
    pct = (clipped - low) / (high - low) * 100
    return pct if higher_is_better else 100 - pct


def _winner(v1, v2, higher_is_better: bool, name1: str, name2: str) -> str:
    if v1 is None or v2 is None:
        return "—"
    try:
        f1, f2 = float(v1), float(v2)
        if np.isnan(f1) or np.isnan(f2):
            return "—"
        if abs(f1 - f2) < 1e-5:
            return "Igual"
        return name1 if (f1 > f2) == higher_is_better else name2
    except (ValueError, TypeError):
        return "—"


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Visualizaciones ─────────────────────────────────────────────────────────

def build_radar(p1_data: dict, p2_data: dict, name1: str, name2: str, role: str) -> go.Figure:
    metrics = RADAR_METRICS_BAT if role == "batter" else RADAR_METRICS_PIT
    data_key = "batting" if role == "batter" else "pitching"

    d1 = p1_data.get(data_key, {})
    d2 = p2_data.get(data_key, {})

    # Usar etiquetas amigables en los ejes del radar
    labels = [cfg["label"] for cfg in metrics.values()]
    vals1, vals2 = [], []

    for m, cfg in metrics.items():
        low, high = cfg["scale"]
        hib = cfg["higher_is_better"]
        vals1.append(_normalize(d1.get(m, np.nan), low, high, hib))
        vals2.append(_normalize(d2.get(m, np.nan), low, high, hib))

    labels += [labels[0]]
    vals1  += [vals1[0]]
    vals2  += [vals2[0]]

    RED  = "#E63946"
    BLUE = "#457B9D"
    fig = go.Figure()
    for vals, name, color in [(vals1, name1, RED), (vals2, name2, BLUE)]:
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=labels,
            fill="toself",
            name=name,
            line=dict(color=color, width=2.5),
            fillcolor=_hex_to_rgba(color, 0.28),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(15, 23, 42, 0.4)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                tickfont=dict(color="rgba(226, 232, 240, 0.8)", size=10),
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.20)",
            ),
            angularaxis=dict(
                tickfont=dict(color="#FFFFFF", size=13, family="sans-serif"),
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.25)",
            ),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.16,
            xanchor="center",
            x=0.5,
            font=dict(color="#FFFFFF", size=14),
            bgcolor="rgba(15, 23, 42, 0.85)",
            bordercolor="rgba(255, 255, 255, 0.20)",
            borderwidth=1,
        ),
        height=540,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FFFFFF"),
        margin=dict(t=25, b=85, l=45, r=45),
    )
    return fig


def build_comparison_table(p1_data: dict, p2_data: dict,
                            name1: str, name2: str, role: str) -> pd.DataFrame:
    data_key = "batting" if role == "batter" else "pitching"
    d1 = p1_data.get(data_key, {})
    d2 = p2_data.get(data_key, {})

    rows = []

    # Sección 1: Stats tradicionales de rate
    trad = _TRAD_BAT if role == "batter" else _TRAD_PIT
    for k, cfg in trad.items():
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg["higher_is_better"], name1, name2)
        rows.append({"Categoría": "Tradicional (Rate)", "Stat": cfg["label"], name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    # Sección 2: Stats de volumen / conteo
    extra = _EXTRA_BAT if role == "batter" else _EXTRA_PIT
    for k in extra:
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, True, name1, name2)
        rows.append({"Categoría": "Volumen", "Stat": k, name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    # Sección 3: Statcast (valores reales, métricas esperadas)
    statcast = _STATCAST_BAT if role == "batter" else _STATCAST_PIT
    for k, cfg in statcast.items():
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg["higher_is_better"], name1, name2)
        rows.append({"Categoría": "Statcast Esperado", "Stat": cfg["label"], name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    # Sección 4: Diferenciales de Suerte / Regresión
    diffs = _DIFF_BAT if role == "batter" else _DIFF_PIT
    for k, cfg in diffs.items():
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg["higher_is_better"], name1, name2)
        rows.append({"Categoría": "Diferenciales (Regresión)", "Stat": cfg["label"], name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    return pd.DataFrame(rows)


def build_comparison_image(p1_data: dict, p2_data: dict,
                            name1: str, name2: str, role: str,
                            df_comp: pd.DataFrame) -> bytes:
    """Genera PNG descargable de alta definición con soporte seguro de fuentes."""
    from PIL import Image, ImageDraw, ImageFont

    data_key = "batting" if role == "batter" else "pitching"
    d1s = p1_data.get(data_key, {})
    d2s = p2_data.get(data_key, {})
    team1 = d1s.get("Team", "—")
    team2 = d2s.get("Team", "—")

    COL1, COL2, COL3 = 190, 160, 190
    W = COL1 + COL2 + COL3
    ROW_H, HDR_H, FOOT_H = 28, 60, 26
    n = len(df_comp)
    H = HDR_H + n * ROW_H + FOOT_H

    BG    = (255, 255, 255)
    ALT   = (244, 246, 250)
    RED   = (220, 50, 60)
    BLUE  = (60, 110, 145)
    DARK  = (35, 40, 50)
    GRAY  = (110, 115, 125)
    RHDR  = (210, 45, 58)
    BHDR  = (45, 95, 135)
    CHDR  = (225, 228, 236)

    def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
        suffix = "-Bold" if bold else ""
        paths = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
            f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf",
            f"C:/Windows/Fonts/{'segoeuib' if bold else 'segoeui'}.ttf",
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    fb = _load_font(13, bold=True)
    fn = _load_font(12)
    fs = _load_font(10)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    def _tc(cx, cy, text, font, color):
        try:
            bb = draw.textbbox((0, 0), str(text), font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
        except AttributeError:
            tw, th = draw.textsize(str(text), font=font)
        draw.text((cx - tw // 2, cy - th // 2), str(text), font=font, fill=color)

    # Header
    draw.rectangle([0, 0, COL1 - 1, HDR_H - 1], fill=RHDR)
    draw.rectangle([COL1, 0, COL1 + COL2 - 1, HDR_H - 1], fill=CHDR)
    draw.rectangle([COL1 + COL2, 0, W - 1, HDR_H - 1], fill=BHDR)

    _tc(COL1 // 2,              20, name1, fb, (255, 255, 255))
    _tc(COL1 // 2,              42, f"{team1} · {role.upper()}", fs, (240, 230, 230))
    _tc(COL1 + COL2 // 2,       30, "VS", fb, GRAY)
    _tc(COL1 + COL2 + COL3//2, 20, name2, fb, (255, 255, 255))
    _tc(COL1 + COL2 + COL3//2, 42, f"{team2} · {role.upper()}", fs, (225, 235, 245))

    draw.line([(0, HDR_H), (W, HDR_H)], fill=(200, 205, 215), width=1)

    # Rows
    stats   = df_comp["Stat"].tolist()
    vals1   = df_comp[name1].astype(str).replace({"nan": "N/D", "<NA>": "N/D"}).tolist()
    vals2   = df_comp[name2].astype(str).replace({"nan": "N/D", "<NA>": "N/D"}).tolist()
    winners = df_comp["Ventaja"].tolist()

    for i, (stat, v1, v2, w) in enumerate(zip(stats, vals1, vals2, winners)):
        y0 = HDR_H + i * ROW_H
        draw.rectangle([0, y0, W - 1, y0 + ROW_H - 1], fill=ALT if i % 2 == 0 else BG)
        draw.line([(0, y0 + ROW_H - 1), (W, y0 + ROW_H - 1)], fill=(225, 228, 235), width=1)
        mid = y0 + ROW_H // 2
        c1 = RED  if w == name1 else DARK
        c2 = BLUE if w == name2 else DARK
        _tc(COL1 // 2,             mid, v1, fb if w == name1 else fn, c1)
        _tc(COL1 + COL2 // 2,      mid, stat, fn, GRAY)
        _tc(COL1 + COL2 + COL3//2, mid, v2, fb if w == name2 else fn, c2)

    # Footer
    _tc(W // 2, HDR_H + n * ROW_H + FOOT_H // 2, "⚾ Vision 360 · MLB Sabermetrics", fs, (160, 165, 175))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_sprint_row(p1_data: dict, p2_data: dict, name1: str, name2: str) -> pd.DataFrame:
    s1 = p1_data.get("sprint", {})
    s2 = p2_data.get("sprint", {})
    rows = []
    for key, label in [("sprint_speed", "Sprint Speed (ft/s)"), ("hp_to_1b", "HP→1B (seg)")]:
        rows.append({
            "Métrica": label,
            name1: _fmt("V_EV" if key == "sprint_speed" else "sprint", s1.get(key, "N/D")),
            name2: _fmt("V_EV" if key == "sprint_speed" else "sprint", s2.get(key, "N/D")),
        })
    return pd.DataFrame(rows)
