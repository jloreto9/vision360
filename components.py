import io
import os
import urllib.request
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont


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
    "V_diff_BA":   {"label": "diff (BA - xBA)",     "higher_is_better": False},
    "V_diff_SLG":  {"label": "diff (SLG - xSLG)",   "higher_is_better": False},
    "V_diff_wOBA": {"label": "diff (OBP - xwOBA)",  "higher_is_better": False},
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
    "V_diff_ERA":  {"label": "diff (ERA - xERA)", "higher_is_better": True},
}

# ── Formateo de valores ─────────────────────────────────────────────────────

_INT_STATS   = {"G", "PA", "HR", "R", "RBI", "SB", "GS", "W", "L", "SV", "OAA", "Runs Prevented"}
_RATE3_STATS = {"AVG", "OBP", "SLG", "OPS", "ISO", "BABIP"}
_RATE2_STATS = {"ERA", "WHIP", "K/9", "BB/9", "HR/9"}
_PCT_STATS   = {"BB%", "K%"}


def _fmt(stat: str, value) -> str:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)) or str(value).strip() in ("", "nan", "<NA>", "None"):
            return "N/D"
        if stat.startswith("P_"):
            return str(int(round(float(value))))
        if stat.startswith("V_diff_") or stat.startswith("diff"):
            v = float(str(value).replace("%", "").replace("+", ""))
            sign = "+" if v > 0 else ""
            if "ERA" in stat:
                return f"{sign}{v:.2f}"
            return f"{sign}{v:.3f}"
        if stat.startswith("V_"):
            v = float(str(value).replace("%", "").replace(" mph", ""))
            if stat in {"V_xwOBA", "V_xBA", "V_xSLG"}:
                s = f"{v:.3f}"
                return s[1:] if s.startswith("0.") else s
            if stat in {"V_xERA"}:
                return f"{v:.2f}"
            if stat in {"V_EV", "V_FBVelo"}:
                return f"{v:.1f} mph"
            return f"{v:.1f}%"
        if stat == "sprint_speed":
            return f"{float(value):.1f} ft/s"
        if stat == "hp_to_1b":
            return f"{float(value):.2f} s"
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
        if str(value).endswith("%"):
            return str(value)
        return str(value)
    except (ValueError, TypeError):
        return str(value) if value is not None else "N/D"


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
        s1 = str(v1).replace("%", "").replace(" mph", "").replace(" ft/s", "").replace(" s", "").strip()
        s2 = str(v2).replace("%", "").replace(" mph", "").replace(" ft/s", "").replace(" s", "").strip()
        if s1 in ("N/D", "—", "nan") or s2 in ("N/D", "—", "nan"):
            return "—"
        f1, f2 = float(s1), float(s2)
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

    # 1. Tradicional Rate
    trad = _TRAD_BAT if role == "batter" else _TRAD_PIT
    for k, cfg in trad.items():
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg["higher_is_better"], name1, name2)
        rows.append({"Categoría": "Tradicional (Rate)", "Stat": cfg["label"], name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    # 2. Volumen
    extra = _EXTRA_BAT if role == "batter" else _EXTRA_PIT
    for k in extra:
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, True, name1, name2)
        rows.append({"Categoría": "Volumen", "Stat": k, name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    # 3. Statcast Esperado
    statcast = _STATCAST_BAT if role == "batter" else _STATCAST_PIT
    for k, cfg in statcast.items():
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg["higher_is_better"], name1, name2)
        rows.append({"Categoría": "Statcast Esperado", "Stat": cfg["label"], name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    # 4. Diferenciales (Regresión)
    diffs = _DIFF_BAT if role == "batter" else _DIFF_PIT
    for k, cfg in diffs.items():
        v1, v2 = d1.get(k), d2.get(k)
        winner = _winner(v1, v2, cfg["higher_is_better"], name1, name2)
        rows.append({"Categoría": "Diferenciales", "Stat": cfg["label"], name1: _fmt(k, v1), name2: _fmt(k, v2), "Ventaja": winner})

    # 5. Defensa (Statcast OAA)
    f1 = p1_data.get("fielding", [{}])[0] if p1_data.get("fielding") else {}
    f2 = p2_data.get("fielding", [{}])[0] if p2_data.get("fielding") else {}
    
    oaa1, oaa2 = f1.get("OAA"), f2.get("OAA")
    if oaa1 is not None or oaa2 is not None:
        winner = _winner(oaa1, oaa2, True, name1, name2)
        rows.append({"Categoría": "Defensa", "Stat": "OAA (Outs Above Avg)", name1: _fmt("OAA", oaa1), name2: _fmt("OAA", oaa2), "Ventaja": winner})

    rp1, rp2 = f1.get("Runs Prevented"), f2.get("Runs Prevented")
    if rp1 is not None or rp2 is not None:
        winner = _winner(rp1, rp2, True, name1, name2)
        rows.append({"Categoría": "Defensa", "Stat": "Runs Prevented", name1: _fmt("Runs Prevented", rp1), name2: _fmt("Runs Prevented", rp2), "Ventaja": winner})

    # 6. Velocidad
    s1 = p1_data.get("sprint", {})
    s2 = p2_data.get("sprint", {})
    sp1, sp2 = s1.get("sprint_speed"), s2.get("sprint_speed")
    if sp1 is not None or sp2 is not None:
        winner = _winner(sp1, sp2, True, name1, name2)
        rows.append({"Categoría": "Velocidad", "Stat": "Sprint Speed", name1: _fmt("sprint_speed", sp1), name2: _fmt("sprint_speed", sp2), "Ventaja": winner})

    hp1, hp2 = s1.get("hp_to_1b"), s2.get("hp_to_1b")
    if hp1 is not None or hp2 is not None:
        winner = _winner(hp1, hp2, False, name1, name2)
        rows.append({"Categoría": "Velocidad", "Stat": "HP-1B", name1: _fmt("hp_to_1b", hp1), name2: _fmt("hp_to_1b", hp2), "Ventaja": winner})

    return pd.DataFrame(rows)


def _fetch_headshot_image(url: str, size: tuple = (56, 56)) -> Image.Image | None:
    """Descarga y recorta en formato circular el headshot oficial de MLB."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = resp.read()
        raw_img = Image.open(io.BytesIO(data)).convert("RGBA")
        raw_img = raw_img.resize(size, Image.Resampling.LANCZOS)
        
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        
        circ = Image.new("RGBA", size, (0, 0, 0, 0))
        circ.paste(raw_img, (0, 0), mask=mask)
        return circ
    except Exception:
        return None


def _fetch_raw_image(url: str, size: tuple = (24, 24)) -> Image.Image | None:
    """Descarga y redimensiona una imagen con transparencia (ej. logo de equipo oficial)."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = resp.read()
        raw_img = Image.open(io.BytesIO(data)).convert("RGBA")
        return raw_img.resize(size, Image.Resampling.LANCZOS)
    except Exception:
        return None


def build_comparison_image(p1_data: dict, p2_data: dict,
                            name1: str, name2: str, role: str,
                            df_comp: pd.DataFrame) -> bytes:
    """Genera PNG descargable de alta definición con Headshots oficiales y logos de equipo MLB."""
    data_key = "batting" if role == "batter" else "pitching"
    d1s = p1_data.get(data_key, {})
    d2s = p2_data.get(data_key, {})
    team1 = p1_data.get("team") or d1s.get("Team", "—")
    team2 = p2_data.get("team") or d2s.get("Team", "—")

    COL1, COL2, COL3 = 210, 160, 210
    W = COL1 + COL2 + COL3
    ROW_H, HDR_H, FOOT_H = 28, 86, 30
    n = len(df_comp)
    H = HDR_H + n * ROW_H + FOOT_H

    BG    = (255, 255, 255)
    ALT   = (244, 247, 251)
    RED   = (220, 50, 60)
    BLUE  = (50, 105, 145)
    DARK  = (30, 35, 45)
    GRAY  = (105, 110, 120)
    RHDR  = (210, 45, 58)
    BHDR  = (40, 95, 135)
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
    ftitle = _load_font(14, bold=True)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    def _tc(cx, cy, text, font, color):
        try:
            bb = draw.textbbox((0, 0), str(text), font=font)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
        except AttributeError:
            tw, th = draw.textsize(str(text), font=font)
        draw.text((cx - tw // 2, cy - th // 2), str(text), font=font, fill=color)

    # Header Backgrounds
    draw.rectangle([0, 0, COL1 - 1, HDR_H - 1], fill=RHDR)
    draw.rectangle([COL1, 0, COL1 + COL2 - 1, HDR_H - 1], fill=CHDR)
    draw.rectangle([COL1 + COL2, 0, W - 1, HDR_H - 1], fill=BHDR)

    # Descargar y pegar Headshots y Logos de Equipo
    headshot1 = _fetch_headshot_image(p1_data.get("headshot_url"), size=(56, 56))
    if headshot1:
        img.paste(headshot1, (10, (HDR_H - 56) // 2), mask=headshot1)
        _tc(COL1 // 2 + 20, 30, name1, ftitle, (255, 255, 255))
        _tc(COL1 // 2 + 20, 54, f"{team1} · {role.upper()}", fs, (245, 230, 230))
    else:
        _tc(COL1 // 2, 30, name1, ftitle, (255, 255, 255))
        _tc(COL1 // 2, 54, f"{team1} · {role.upper()}", fs, (245, 230, 230))

    tlogo1 = _fetch_raw_image(p1_data.get("team_logo_url"), size=(24, 24))
    if tlogo1:
        img.paste(tlogo1, (COL1 - 30, 8), mask=tlogo1)

    _tc(COL1 + COL2 // 2, 42, "VS", ftitle, GRAY)

    headshot2 = _fetch_headshot_image(p2_data.get("headshot_url"), size=(56, 56))
    if headshot2:
        img.paste(headshot2, (COL1 + COL2 + 10, (HDR_H - 56) // 2), mask=headshot2)
        _tc(COL1 + COL2 + COL3 // 2 + 20, 30, name2, ftitle, (255, 255, 255))
        _tc(COL1 + COL2 + COL3 // 2 + 20, 54, f"{team2} · {role.upper()}", fs, (225, 235, 245))
    else:
        _tc(COL1 + COL2 + COL3 // 2, 30, name2, ftitle, (255, 255, 255))
        _tc(COL1 + COL2 + COL3 // 2, 54, f"{team2} · {role.upper()}", fs, (225, 235, 245))

    tlogo2 = _fetch_raw_image(p2_data.get("team_logo_url"), size=(24, 24))
    if tlogo2:
        img.paste(tlogo2, (W - 30, 8), mask=tlogo2)

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
    _tc(W // 2, HDR_H + n * ROW_H + FOOT_H // 2, "⚾ Vision 360 · Desarrollado por Jorge Leonardo Loreto", fs, (140, 145, 155))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_sprint_row(p1_data: dict, p2_data: dict, name1: str, name2: str) -> pd.DataFrame:
    s1 = p1_data.get("sprint", {})
    s2 = p2_data.get("sprint", {})
    rows = []
    for key, label in [("sprint_speed", "Sprint Speed (ft/s)"), ("hp_to_1b", "HP-1B (seg)")]:
        rows.append({
            "Métrica": label,
            name1: _fmt(key, s1.get(key, "N/D")),
            name2: _fmt(key, s2.get(key, "N/D")),
        })
    return pd.DataFrame(rows)
