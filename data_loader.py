import logging
import unicodedata
from pathlib import Path
import streamlit as st
import pybaseball as pb
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

pb.cache.enable()

SEASON = 2026
DATA_DIR = Path(__file__).parent / "data"

# ── Columnas finales por dimensión ─────────────────────────────────────────
BAT_COLS = [
    "Name", "Team", "Pos", "mlbID", "G", "PA", "HR", "R", "RBI", "SB",
    "AVG", "OBP", "SLG", "OPS", "BB%", "K%", "ISO",
    "P_xwOBA", "P_Barrel", "P_EV", "P_HardHit", "P_Whiff", "P_K", "P_BB",
    "V_xBA", "V_xSLG", "V_xwOBA", "V_EV", "V_Barrel", "V_HardHit", "V_Whiff",
    "V_diff_BA", "V_diff_SLG", "V_diff_wOBA",
]

PIT_COLS = [
    "Name", "Team", "Pos", "mlbID", "G", "GS", "IP", "W", "L", "SV",
    "ERA", "WHIP", "K/9", "BB/9", "HR/9", "BABIP",
    "P_xERA", "P_xwOBA", "P_FBVelo", "P_K", "P_BB", "P_Whiff", "P_Barrel",
    "V_xERA", "V_xwOBA", "V_EV", "V_Barrel", "V_HardHit", "V_Whiff", "V_diff_ERA",
]

SPRINT_COLS = ["last_name, first_name", "sprint_speed", "hp_to_1b", "competitive_runs"]

# expected_statistics endpoint: stats "x" (xBA, xSLG, xwOBA, xERA)
_BAT_EXP_RENAME = [
    ("est_ba",   "V_xBA"),
    ("xba",      "V_xBA"),
    ("est_slg",  "V_xSLG"),
    ("xslg",     "V_xSLG"),
    ("est_woba", "V_xwOBA"),
    ("xwoba",    "V_xwOBA"),
]
_PIT_EXP_RENAME = [
    ("est_era",  "V_xERA"),
    ("xera",     "V_xERA"),
    ("est_woba", "V_xwOBA"),
    ("xwoba",    "V_xwOBA"),
]

# exitvelo_barrels endpoint: EV, Barrel%, Hard Hit%, Whiff%
_BAT_EV_RENAME = [
    ("avg_hit_speed",    "V_EV"),
    ("exit_velocity",    "V_EV"),
    ("brl_percent",      "V_Barrel"),
    ("brl_pa",           "V_Barrel"),
    ("barrel",           "V_Barrel"),
    ("ev95percent",      "V_HardHit"),
    ("hard_hit_percent", "V_HardHit"),
    ("whiff_percent",    "V_Whiff"),
]
_PIT_EV_RENAME = [
    ("avg_hit_speed",    "V_EV"),
    ("exit_velocity",    "V_EV"),
    ("brl_percent",      "V_Barrel"),
    ("brl_pa",           "V_Barrel"),
    ("ev95percent",      "V_HardHit"),
    ("hard_hit_percent", "V_HardHit"),
    ("whiff_percent",    "V_Whiff"),
]


# ── Normalización avanzada de nombres (ordenación canónica de tokens) ─────

def normalize_name_key(name: str) -> str:
    """Normaliza un nombre eliminando acentos, sufijos (Jr, II, etc.) y ordenando tokens."""
    if not isinstance(name, str) or not name.strip():
        return ""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("utf-8").lower()
    text = text.replace(".", "").replace(",", " ").strip()
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    tokens = [t for t in text.split() if t and t not in suffixes]
    return " ".join(sorted(tokens))


# ── Helpers de carga ────────────────────────────────────────────────────────

def _load_csv(name: str) -> pd.DataFrame | None:
    path = DATA_DIR / f"{name}.csv"
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as e:
            logger.error("Error leyendo %s.csv: %s", name, e)
    return None


def _safe_fg(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error("%s falló: %s", getattr(func, "__name__", str(func)), e)
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def _get_chadwick_map() -> dict:
    """Carga mapeo de nombres a mlbID oficial mediante chadwick_register."""
    try:
        cr = _safe_fg(pb.chadwick_register)
        if cr is not None and not cr.empty and "key_mlbam" in cr.columns:
            cr["norm_name"] = (cr["name_first"].fillna("") + " " + cr["name_last"].fillna("")).apply(normalize_name_key)
            cr_valid = cr.dropna(subset=["key_mlbam"]).drop_duplicates("norm_name")
            return dict(zip(cr_valid["norm_name"], cr_valid["key_mlbam"].astype(int)))
    except Exception as e:
        logger.warning("No se pudo cargar chadwick_register: %s", e)
    return {}


def _add_empirical_percentiles(df: pd.DataFrame, role: str) -> pd.DataFrame:
    """Calcula percentiles empíricos locales (0-100) para columnas que falten."""
    if df.empty:
        return df

    out = df.copy()
    if role == "batter":
        metric_map = {
            "P_xwOBA": ("V_xwOBA", True),
            "P_Barrel": ("V_Barrel", True),
            "P_EV": ("V_EV", True),
            "P_HardHit": ("V_HardHit", True),
            "P_Whiff": ("V_Whiff", False),
            "P_K": ("K%", False),
            "P_BB": ("BB%", True),
        }
    else:
        metric_map = {
            "P_xERA": ("V_xERA", False),
            "P_xwOBA": ("V_xwOBA", False),
            "P_FBVelo": ("V_EV", True),
            "P_K": ("K/9", True),
            "P_BB": ("BB/9", False),
            "P_Whiff": ("V_Whiff", True),
            "P_Barrel": ("V_Barrel", False),
        }

    for p_col, (src_col, higher_is_better) in metric_map.items():
        if p_col not in out.columns:
            out[p_col] = np.nan

        if src_col in out.columns and out[p_col].isna().sum() > len(out) * 0.5:
            valid_mask = out[src_col].notna()
            if valid_mask.sum() > 5:
                ranks = out.loc[valid_mask, src_col].rank(pct=True) * 100
                if not higher_is_better:
                    ranks = 100 - ranks
                out.loc[valid_mask, p_col] = ranks.round(1)

    return out


# ── Construcción de DataFrames ──────────────────────────────────────────────

def _build_batting(br: pd.DataFrame, sc: pd.DataFrame, exp_df: pd.DataFrame = None, ev_df: pd.DataFrame = None) -> pd.DataFrame:
    """Combina Baseball Reference + Statcast percentile ranks y métricas esperadas para batters."""
    if br.empty:
        return pd.DataFrame()

    df = br.rename(columns={"Tm": "Team", "BA": "AVG"}).copy()
    df = df.sort_values("PA", ascending=False).drop_duplicates("Name").copy()

    if "BB" in df.columns and "PA" in df.columns:
        df["BB%"] = (pd.to_numeric(df["BB"], errors="coerce") / pd.to_numeric(df["PA"], errors="coerce")).round(3)
    if "SO" in df.columns and "PA" in df.columns:
        df["K%"]  = (pd.to_numeric(df["SO"], errors="coerce") / pd.to_numeric(df["PA"], errors="coerce")).round(3)
    
    if "SLG" in df.columns and "AVG" in df.columns and "ISO" not in df.columns:
        avg_num = pd.to_numeric(df["AVG"], errors="coerce")
        slg_num = pd.to_numeric(df["SLG"], errors="coerce")
        df["ISO"] = (slg_num - avg_num).round(3)

    if "mlbID" in df.columns:
        df["mlbID"] = pd.to_numeric(df["mlbID"], errors="coerce").astype("Int64")

    # Statcast percentile ranks
    if sc is not None and not sc.empty:
        sc_sel = sc.rename(columns={
            "xwoba":            "P_xwOBA",
            "brl_percent":      "P_Barrel",
            "exit_velocity":    "P_EV",
            "hard_hit_percent": "P_HardHit",
            "whiff_percent":    "P_Whiff",
            "k_percent":        "P_K",
            "bb_percent":       "P_BB",
        })
        sc_cols = ["player_id", "P_xwOBA", "P_Barrel", "P_EV", "P_HardHit", "P_Whiff", "P_K", "P_BB"]
        sc_sel = sc_sel[[c for c in sc_cols if c in sc_sel.columns]].copy()
        if "player_id" in sc_sel.columns and "mlbID" in df.columns:
            sc_sel["player_id"] = sc_sel["player_id"].astype("Int64")
            df = df.merge(sc_sel, left_on="mlbID", right_on="player_id", how="left")
            df.drop(columns=["player_id"], errors="ignore", inplace=True)

    # Fallback percentiles empíricos
    df = _add_empirical_percentiles(df, "batter")

    cols = [c for c in BAT_COLS if c in df.columns]
    return df[cols].copy()


def _build_pitching(brp: pd.DataFrame, scp: pd.DataFrame, exp_df: pd.DataFrame = None, ev_df: pd.DataFrame = None) -> pd.DataFrame:
    """Combina Baseball Reference + Statcast percentile ranks y métricas esperadas para pitchers."""
    if brp.empty:
        return pd.DataFrame()

    df = brp.rename(columns={
        "Tm": "Team", "SO9": "K/9", "BAbip": "BABIP"
    }).copy()
    df = df.sort_values("IP", ascending=False).drop_duplicates("Name").copy()

    if "BB" in df.columns and "IP" in df.columns and "BB/9" not in df.columns:
        df["BB/9"] = ((pd.to_numeric(df["BB"], errors="coerce") / pd.to_numeric(df["IP"], errors="coerce")) * 9).round(2)
    if "HR" in df.columns and "IP" in df.columns and "HR/9" not in df.columns:
        df["HR/9"] = ((pd.to_numeric(df["HR"], errors="coerce") / pd.to_numeric(df["IP"], errors="coerce")) * 9).round(2)

    if "mlbID" in df.columns:
        df["mlbID"] = pd.to_numeric(df["mlbID"], errors="coerce").astype("Int64")

    # Statcast percentile ranks
    if scp is not None and not scp.empty:
        scp_sel = scp.rename(columns={
            "xera":          "P_xERA",
            "xwoba":         "P_xwOBA",
            "fb_velocity":   "P_FBVelo",
            "k_percent":     "P_K",
            "bb_percent":    "P_BB",
            "whiff_percent": "P_Whiff",
            "brl_percent":   "P_Barrel",
        })
        sc_cols = ["player_id", "P_xERA", "P_xwOBA", "P_FBVelo", "P_K", "P_BB", "P_Whiff", "P_Barrel"]
        scp_sel = scp_sel[[c for c in sc_cols if c in scp_sel.columns]].copy()
        if "player_id" in scp_sel.columns and "mlbID" in df.columns:
            scp_sel["player_id"] = scp_sel["player_id"].astype("Int64")
            df = df.merge(scp_sel, left_on="mlbID", right_on="player_id", how="left")
            df.drop(columns=["player_id"], errors="ignore", inplace=True)

    # Fallback percentiles empíricos
    df = _add_empirical_percentiles(df, "pitcher")

    cols = [c for c in PIT_COLS if c in df.columns]
    return df[cols].copy()


# ── Funciones cacheadas de Streamlit ────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_batting():
    csv = _load_csv("batting")
    if csv is not None:
        return _add_empirical_percentiles(csv, "batter")
    br = _safe_fg(pb.batting_stats_bref, SEASON)
    sc = _safe_fg(pb.statcast_batter_percentile_ranks, SEASON)
    return _build_batting(br, sc)


@st.cache_data(ttl=3600, show_spinner=False)
def load_pitching():
    csv = _load_csv("pitching")
    if csv is not None:
        return _add_empirical_percentiles(csv, "pitcher")
    brp = _safe_fg(pb.pitching_stats_bref, SEASON)
    scp = _safe_fg(pb.statcast_pitcher_percentile_ranks, SEASON)
    return _build_pitching(brp, scp)


@st.cache_data(ttl=3600, show_spinner=False)
def load_batting_expected():
    csv = _load_csv("batting_expected")
    if csv is not None:
        return csv
    try:
        return pb.statcast_batter_expected_stats(SEASON)
    except Exception as e:
        logger.error("statcast_batter_expected_stats: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_pitching_expected():
    csv = _load_csv("pitching_expected")
    if csv is not None:
        return csv
    try:
        return pb.statcast_pitcher_expected_stats(SEASON)
    except Exception as e:
        logger.error("statcast_pitcher_expected_stats: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_batting_exitvelo():
    csv = _load_csv("batting_exitvelo")
    if csv is not None:
        return csv
    try:
        return pb.statcast_batter_exitvelo_barrels(SEASON)
    except Exception as e:
        logger.warning("statcast_batter_exitvelo_barrels no disponible: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_pitching_exitvelo():
    csv = _load_csv("pitching_exitvelo")
    if csv is not None:
        return csv
    try:
        return pb.statcast_pitcher_exitvelo_barrels(SEASON)
    except Exception as e:
        logger.warning("statcast_pitcher_exitvelo_barrels no disponible: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_fielding():
    csv = _load_csv("fielding")
    if csv is not None:
        return csv
    try:
        from pybaseball.statcast_fielding import statcast_outs_above_average
        df = statcast_outs_above_average(SEASON, "all")
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        logger.error("statcast_outs_above_average falló: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_sprint():
    df = _load_csv("sprint")
    if df is not None:
        return df
    try:
        return pb.statcast_sprint_speed(SEASON)
    except Exception as e:
        logger.error("statcast_sprint_speed falló: %s", e)
        return pd.DataFrame()


# ── Helpers de negocio ──────────────────────────────────────────────────────

def detect_role(name: str, bat_df: pd.DataFrame, pit_df: pd.DataFrame) -> str:
    is_bat = (not bat_df.empty) and (name in bat_df["Name"].values)
    is_pit = (not pit_df.empty) and (name in pit_df["Name"].values)
    if is_bat and is_pit:
        return "two-way"
    elif is_pit:
        return "pitcher"
    return "batter"


def _merge_expected(data_dict: dict, exp_df: pd.DataFrame, rename_map: list) -> None:
    if exp_df is None or exp_df.empty:
        return

    matched = pd.Series(dtype=object)

    # Intento 1: por player_id / mlbID
    mlb_id = data_dict.get("mlbID")
    if mlb_id is not None and not pd.isna(mlb_id) and "player_id" in exp_df.columns:
        try:
            pid = int(pd.to_numeric(mlb_id, errors="coerce"))
            tmp = exp_df.copy()
            tmp["_pid"] = pd.to_numeric(tmp["player_id"], errors="coerce")
            hit = tmp[tmp["_pid"] == pid]
            if not hit.empty:
                matched = hit.iloc[0]
        except (ValueError, TypeError):
            pass

    # Intento 2: por normalización de nombres token-sorted
    if matched.empty:
        target_norm = normalize_name_key(data_dict.get("Name", ""))
        if target_norm:
            for name_col in ["last_name, first_name", "Name", "name", "player_name"]:
                if name_col in exp_df.columns:
                    tmp = exp_df.copy()
                    tmp["_norm"] = tmp[name_col].apply(normalize_name_key)
                    hit = tmp[tmp["_norm"] == target_norm]
                    if not hit.empty:
                        matched = hit.iloc[0]
                        break

    if matched.empty:
        return

    seen: set = set()
    for src_col, v_key in rename_map:
        if v_key in seen or v_key in data_dict:
            continue
        if src_col in matched.index and not pd.isna(matched[src_col]):
            data_dict[v_key] = matched[src_col]
            seen.add(v_key)


def get_player_data(name: str, bat_df, pit_df, field_df, sprint_df,
                    bat_exp_df=None, pit_exp_df=None,
                    bat_ev_df=None, pit_ev_df=None) -> dict:
    role = detect_role(name, bat_df, pit_df)
    result = {"name": name, "role": role, "mlbID": None}

    # Resolver mlbID temprano
    chadwick = _get_chadwick_map()
    norm_n = normalize_name_key(name)
    if norm_n in chadwick:
        result["mlbID"] = chadwick[norm_n]

    if role in ("batter", "two-way") and not bat_df.empty:
        row = bat_df[bat_df["Name"] == name]
        if not row.empty:
            result["batting"] = row.iloc[0].to_dict()
            if result.get("mlbID"):
                result["batting"]["mlbID"] = result["mlbID"]
            elif pd.notna(result["batting"].get("mlbID")):
                result["mlbID"] = int(result["batting"]["mlbID"])

            _merge_expected(result["batting"], bat_exp_df, _BAT_EXP_RENAME)
            _merge_expected(result["batting"], bat_ev_df,  _BAT_EV_RENAME)

            # Calcular diferenciales en tiempo real
            b = result["batting"]
            if "V_xBA" in b and "AVG" in b and pd.notna(b["V_xBA"]) and pd.notna(b["AVG"]):
                b["V_diff_BA"] = round(float(b["AVG"]) - float(b["V_xBA"]), 3)
            if "V_xSLG" in b and "SLG" in b and pd.notna(b["V_xSLG"]) and pd.notna(b["SLG"]):
                b["V_diff_SLG"] = round(float(b["SLG"]) - float(b["V_xSLG"]), 3)
            if "V_xwOBA" in b and pd.notna(b["V_xwOBA"]):
                ref_obp = b.get("OBP") if pd.notna(b.get("OBP")) else b.get("AVG")
                if pd.notna(ref_obp):
                    b["V_diff_wOBA"] = round(float(ref_obp) - float(b["V_xwOBA"]), 3)
        else:
            result["batting"] = {}

    if role in ("pitcher", "two-way") and not pit_df.empty:
        row = pit_df[pit_df["Name"] == name]
        if not row.empty:
            result["pitching"] = row.iloc[0].to_dict()
            if result.get("mlbID"):
                result["pitching"]["mlbID"] = result["mlbID"]
            elif pd.notna(result["pitching"].get("mlbID")):
                result["mlbID"] = int(result["pitching"]["mlbID"])

            _merge_expected(result["pitching"], pit_exp_df, _PIT_EXP_RENAME)
            _merge_expected(result["pitching"], pit_ev_df,  _PIT_EV_RENAME)

            p = result["pitching"]
            if "V_xERA" in p and "ERA" in p and pd.notna(p["V_xERA"]) and pd.notna(p["ERA"]):
                p["V_diff_ERA"] = round(float(p["ERA"]) - float(p["V_xERA"]), 2)
        else:
            result["pitching"] = {}

    # Headshot oficial de MLB
    if result.get("mlbID"):
        result["headshot_url"] = (
            f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/"
            f"w_213,q_auto:best/v1/people/{result['mlbID']}/headshot/67/current"
        )
    else:
        result["headshot_url"] = None

    # Fielding (Statcast OAA / BRef)
    result["fielding"] = []
    if field_df is not None and not field_df.empty:
        fmatch = pd.DataFrame()
        if result.get("mlbID"):
            for id_col in ["player_id", "mlbID"]:
                if id_col in field_df.columns:
                    fmatch = field_df[pd.to_numeric(field_df[id_col], errors="coerce") == result["mlbID"]]
                    if not fmatch.empty:
                        break
        if fmatch.empty:
            target_norm = normalize_name_key(name)
            for name_col in ["last_name, first_name", "Name", "name", "player_name"]:
                if name_col in field_df.columns:
                    fmatch = field_df[field_df[name_col].apply(normalize_name_key) == target_norm]
                    if not fmatch.empty:
                        break

        if not fmatch.empty:
            field_entry = {}
            row0 = fmatch.iloc[0]
            pos = row0.get("primary_pos_formatted") or row0.get("Pos") or "—"
            team = row0.get("display_team_name") or row0.get("Team") or "—"
            field_entry["Posición"] = pos
            field_entry["Equipo"] = team
            if "outs_above_average" in fmatch.columns and pd.notna(row0.get("outs_above_average")):
                field_entry["OAA"] = int(row0.get("outs_above_average"))
            if "fielding_runs_prevented" in fmatch.columns and pd.notna(row0.get("fielding_runs_prevented")):
                field_entry["Runs Prevented"] = int(row0.get("fielding_runs_prevented"))
            if "actual_success_rate_formatted" in fmatch.columns and pd.notna(row0.get("actual_success_rate_formatted")):
                field_entry["Success Rate"] = str(row0.get("actual_success_rate_formatted"))
            if "adj_estimated_success_rate_formatted" in fmatch.columns and pd.notna(row0.get("adj_estimated_success_rate_formatted")):
                field_entry["Expected Success"] = str(row0.get("adj_estimated_success_rate_formatted"))
            if "diff_success_rate_formatted" in fmatch.columns and pd.notna(row0.get("diff_success_rate_formatted")):
                field_entry["diff Success"] = str(row0.get("diff_success_rate_formatted"))
            for col in ["G", "GS", "Inn", "PO", "A", "E", "DP", "Fld%"]:
                if col in fmatch.columns and pd.notna(row0.get(col)):
                    field_entry[col] = row0.get(col)
            result["fielding"] = [field_entry]

    # Sprint Speed
    if sprint_df is not None and not sprint_df.empty:
        target_norm = normalize_name_key(name)
        srow = pd.DataFrame()
        if result.get("mlbID") and "player_id" in sprint_df.columns:
            srow = sprint_df[pd.to_numeric(sprint_df["player_id"], errors="coerce") == result["mlbID"]]
        if srow.empty:
            for name_col in ["last_name, first_name", "full_name", "Name", "name"]:
                if name_col in sprint_df.columns:
                    srow = sprint_df[sprint_df[name_col].apply(normalize_name_key) == target_norm]
                    if not srow.empty:
                        break
        result["sprint"] = srow.iloc[0].to_dict() if not srow.empty else {}
    else:
        result["sprint"] = {}

    return result
