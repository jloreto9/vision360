import io
import os
import plotly.graph_objects as go
import pandas as pd
import numpy as np


# ── Métricas del radar (stats crudas, mismas que la tabla) ──────────────────

RADAR_METRICS_BAT = {
    "OBP":  {"higher_is_better": True,  "scale": (0.200, 0.500)},
    "SLG":  {"higher_is_better": True,  "scale": (0.200, 0.700)},
    "ISO":  {"higher_is_better": True,  "scale": (0.000, 0.350)},
    "OPS":  {"higher_is_better": True,  "scale": (0.500, 1.100)},
    "BB%":  {"higher_is_better": True,  "scale": (0.030, 0.200)},
    "K%":   {"higher_is_better": False, "scale": (0.050, 0.400)},
    "AVG":  {"higher_is_better": True,  "scale": (0.180, 0.360)},
}

RADAR_METRICS_PIT = {
    "ERA":   {"higher_is_better": False, "scale": (1.50, 7.00)},
    "WHIP":  {"higher_is_better": False, "scale": (0.80, 1.80)},
    "K/9":   {"higher_is_better": True,  "scale": (3.00, 16.00)},
    "BB/9":  {"higher_is_better": False, "scale": (1.00, 6.00)},
    "HR/9":  {"higher_is_better": False, "scale": (0.00, 2.50)},
    "BABIP": {"higher_is_better": False, "scale": (0.200, 0.380)},
}

# Counting stats que aparecen en la tabla pero no en el radar
_EXTRA_BAT = ["G", "PA", "HR", "R", "RBI", "SB"]
_EXTRA_PIT = ["G", "GS", "IP", "W", "L", "SV"]

# ── Formateo de valores ─────────────────────────────────────────────────────

_INT_STATS   = {"G", "PA", "HR", "R", "RBI", "SB", "GS", "W", "L", "SV"}
_RATE3_STATS = {"AVG", "OBP", "SLG", "OPS", "ISO", "BABIP"}
_RATE2_STATS = {"ERA", "WHIP", "K/9", "BB/9", "HR/9"}
_PCT_STATS   = {"BB%", "K%"}


def _fmt(stat: str, value) -> str:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "N/D"
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

    labels = list(metrics.keys())
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
            line=dict(color=color, width=2),
            fillcolor=_hex_to_rgba(color, 0.25),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(255,255,255,0.06)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                tickfont=dict(color="rgba(255,255,255,0.55)", size=9),
                gridcolor="rgba(255,255,255,0.18)",
                linecolor="rgba(255,255,255,0.18)",
            ),
            angularaxis=dict(
                tickfont=dict(color="white", size=12),
                gridcolor="rgba(255,255,255,0.18)",
                linecolor="rgba(255,255,255,0.25)",
            ),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(color="white", size=13),
            bgcolor="rgba(0,0,0,0.40)",
            bordercolor="rgba(255,255,255,0.25)",
            borderwidth=1,
        ),
        height=530,
        paper_bgcolor="#111827",
        font=dict(color="white"),
        margin=dict(t=20, b=80, l=40, r=40),
    )
    return fig


def build_comparison_table(p1_data: dict, p2_data: dict,
                            name1: str, name2: str, role: str) -> pd.DataFrame:
    data_key = "batting" if role == "batter" else "pitching"
    metrics_cfg = RADAR_METRICS_BAT if role == "batter" else RADAR_METRICS_PIT

    d1 = p1_data.get(data_key, {})
    d2 = p2_data.get(data_key, {})
    extra = _EXTRA_BAT if role == "batter" else _EXTRA_PIT

    rows = []
    for k, cfg in metrics_cfg.items():
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg["higher_is_better"], name1, name2)
        rows.append({"Stat": k, name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    for k in extra:
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, True, name1, name2)
        rows.append({"Stat": k, name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    return pd.DataFrame(rows)


def build_comparison_image(p1_data: dict, p2_data: dict,
                            name1: str, name2: str, role: str,
                            df_comp: pd.DataFrame) -> bytes:
    """Genera PNG descargable — fondo blanco, texto oscuro."""
    from PIL import Image, ImageDraw, ImageFont

    data_key = "batting" if role == "batter" else "pitching"
    d1s = p1_data.get(data_key, {})
    d2s = p2_data.get(data_key, {})
    team1 = d1s.get("Team", "—")
    team2 = d2s.get("Team", "—")

    COL1, COL2, COL3 = 170, 140, 170
    W = COL1 + COL2 + COL3
    ROW_H, HDR_H, FOOT_H = 26, 54, 22
    n = len(df_comp)
    H = HDR_H + n * ROW_H + FOOT_H

    # Paleta fondo blanco
    BG    = (255, 255, 255)
    ALT   = (243, 245, 249)
    RED   = (220, 50, 60)
    BLUE  = (60, 110, 145)
    DARK  = (40, 40, 45)        # texto loser
    GRAY  = (120, 120, 130)     # texto stat name
    RHDR  = (195, 40, 52)       # fondo header p1
    BHDR  = (48, 100, 138)      # fondo header p2
    CHDR  = (230, 232, 240)     # fondo header central

    def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
        suffix = "-Bold" if bold else ""
        paths = [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
            f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf",
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
            bb = draw.textbbox((0, 0), text, font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
        except AttributeError:
            tw, th = draw.textsize(text, font=font)
        draw.text((cx - tw // 2, cy - th // 2), text, font=font, fill=color)

    # Header
    draw.rectangle([0, 0, COL1 - 1, HDR_H - 1], fill=RHDR)
    draw.rectangle([COL1, 0, COL1 + COL2 - 1, HDR_H - 1], fill=CHDR)
    draw.rectangle([COL1 + COL2, 0, W - 1, HDR_H - 1], fill=BHDR)

    _tc(COL1 // 2,              18, name1, fb, (255, 255, 255))
    _tc(COL1 // 2,              37, f"{team1} · {role.upper()}", fs, (230, 220, 220))
    _tc(COL1 + COL2 // 2,       27, "VS", fb, GRAY)
    _tc(COL1 + COL2 + COL3//2, 18, name2, fb, (255, 255, 255))
    _tc(COL1 + COL2 + COL3//2, 37, f"{team2} · {role.upper()}", fs, (215, 225, 235))

    draw.line([(0, HDR_H), (W, HDR_H)], fill=(200, 202, 210), width=1)

    # Rows
    stats   = df_comp["Stat"].tolist()
    vals1   = df_comp[name1].astype(str).replace({"nan": "N/D", "<NA>": "N/D"}).tolist()
    vals2   = df_comp[name2].astype(str).replace({"nan": "N/D", "<NA>": "N/D"}).tolist()
    winners = df_comp["Ventaja"].tolist()

    for i, (stat, v1, v2, w) in enumerate(zip(stats, vals1, vals2, winners)):
        y0 = HDR_H + i * ROW_H
        draw.rectangle([0, y0, W - 1, y0 + ROW_H - 1], fill=ALT if i % 2 == 0 else BG)
        draw.line([(0, y0 + ROW_H - 1), (W, y0 + ROW_H - 1)], fill=(220, 222, 228), width=1)
        mid = y0 + ROW_H // 2
        c1 = RED  if w == name1 else DARK
        c2 = BLUE if w == name2 else DARK
        _tc(COL1 // 2,             mid, v1, fb if w == name1 else fn, c1)
        _tc(COL1 + COL2 // 2,      mid, stat, fn, GRAY)
        _tc(COL1 + COL2 + COL3//2, mid, v2, fb if w == name2 else fn, c2)

    # Footer
    _tc(W // 2, HDR_H + n * ROW_H + FOOT_H // 2, "⚾ Vision 360", fs, (170, 170, 180))

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
            name1: s1.get(key, "N/D"),
            name2: s2.get(key, "N/D"),
        })
    return pd.DataFrame(rows)
