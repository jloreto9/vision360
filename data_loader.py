import logging
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
    "Name", "Team", "G", "PA", "HR", "R", "RBI", "SB",
    "AVG", "OBP", "SLG", "OPS", "BB%", "K%", "ISO",
    "P_xwOBA", "P_Barrel", "P_EV", "P_HardHit", "P_Whiff", "P_K", "P_BB",
]

PIT_COLS = [
    "Name", "Team", "G", "GS", "IP", "W", "L", "SV",
    "ERA", "WHIP", "K/9", "BB/9", "HR/9", "BABIP",
    "P_xERA", "P_xwOBA", "P_FBVelo", "P_K", "P_BB", "P_Whiff", "P_Barrel",
]

SPRINT_COLS = ["last_name, first_name", "sprint_speed", "hp_to_1b", "competitive_runs"]

# Mapas de columnas de valores reales Statcast — varios nombres posibles, gana el primero que exista
_BAT_EXP_RENAME = [
    ("est_woba",          "V_xwOBA"),
    ("xwoba",             "V_xwOBA"),
    ("brl_percent",       "V_Barrel"),
    ("barrel",            "V_Barrel"),
    ("barrel_batted_rate","V_Barrel"),
    ("exit_velocity",     "V_EV"),
    ("launch_speed",      "V_EV"),
    ("hard_hit_percent",  "V_HardHit"),
    ("whiff_percent",     "V_Whiff"),
    ("k_percent",         "V_K"),
    ("bb_percent",        "V_BB"),
]
_PIT_EXP_RENAME = [
    ("est_era",           "V_xERA"),
    ("xera",              "V_xERA"),
    ("est_woba",          "V_xwOBA"),
    ("xwoba",             "V_xwOBA"),
    ("k_percent",         "V_K"),
    ("p_k_percent",       "V_K"),
    ("bb_percent",        "V_BB"),
    ("p_bb_percent",      "V_BB"),
    ("whiff_percent",     "V_Whiff"),
    ("brl_percent",       "V_Barrel"),
    ("barrel",            "V_Barrel"),
]


# ── Helpers de carga ────────────────────────────────────────────────────────

def _load_csv(name: str) -> pd.DataFrame | None:
    path = DATA_DIR / f"{name}.csv"
    return pd.read_csv(path) if path.exists() else None


def _safe_fg(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error("%s falló: %s", func.__name__, e)
        return pd.DataFrame()


# ── Construcción de DataFrames (llamable desde refresh_data.py) ─────────────

def _build_batting(br: pd.DataFrame, sc: pd.DataFrame) -> pd.DataFrame:
    """Combina Baseball Reference + Statcast percentile ranks para batters."""
    if br.empty:
        return pd.DataFrame()

    df = br.rename(columns={"Tm": "Team", "BA": "AVG"}).copy()
    # Players traded mid-season aparecen duplicados; quedarse con el stint de más PA
    df = df.sort_values("PA", ascending=False).drop_duplicates("Name").copy()

    df["BB%"] = (df["BB"] / df["PA"]).round(3)
    df["K%"]  = (df["SO"] / df["PA"]).round(3)
    df["ISO"] = (df["SLG"] - df["AVG"]).round(3)

    if not sc.empty:
        sc_sel = sc.rename(columns={
            "xwoba":            "P_xwOBA",
            "brl_percent":      "P_Barrel",
            "exit_velocity":    "P_EV",
            "hard_hit_percent": "P_HardHit",
            "whiff_percent":    "P_Whiff",
            "k_percent":        "P_K",
            "bb_percent":       "P_BB",
        })[["player_id", "P_xwOBA", "P_Barrel", "P_EV",
             "P_HardHit", "P_Whiff", "P_K", "P_BB"]]
        df["mlbID"] = pd.to_numeric(df["mlbID"], errors="coerce").astype("Int64")
        sc_sel["player_id"] = sc_sel["player_id"].astype("Int64")
        df = df.merge(sc_sel, left_on="mlbID", right_on="player_id", how="left")
        df.drop(columns=["player_id"], errors="ignore", inplace=True)

    cols = [c for c in BAT_COLS if c in df.columns]
    return df[cols].copy()


def _build_pitching(brp: pd.DataFrame, scp: pd.DataFrame) -> pd.DataFrame:
    """Combina Baseball Reference + Statcast percentile ranks para pitchers."""
    if brp.empty:
        return pd.DataFrame()

    df = brp.rename(columns={
        "Tm": "Team", "SO9": "K/9", "BAbip": "BABIP"
    }).copy()
    df = df.sort_values("IP", ascending=False).drop_duplicates("Name").copy()

    df["BB/9"] = ((df["BB"] / df["IP"]) * 9).round(2)
    df["HR/9"] = ((df["HR"] / df["IP"]) * 9).round(2)

    if not scp.empty:
        scp_sel = scp.rename(columns={
            "xera":          "P_xERA",
            "xwoba":         "P_xwOBA",
            "fb_velocity":   "P_FBVelo",
            "k_percent":     "P_K",
            "bb_percent":    "P_BB",
            "whiff_percent": "P_Whiff",
            "brl_percent":   "P_Barrel",
        })[["player_id", "P_xERA", "P_xwOBA", "P_FBVelo",
             "P_K", "P_BB", "P_Whiff", "P_Barrel"]]
        df["mlbID"] = pd.to_numeric(df["mlbID"], errors="coerce").astype("Int64")
        scp_sel["player_id"] = scp_sel["player_id"].astype("Int64")
        df = df.merge(scp_sel, left_on="mlbID", right_on="player_id", how="left")
        df.drop(columns=["player_id"], errors="ignore", inplace=True)

    cols = [c for c in PIT_COLS if c in df.columns]
    return df[cols].copy()


# ── Funciones cacheadas de Streamlit ────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_batting():
    csv = _load_csv("batting")
    if csv is not None:
        return csv
    br = _safe_fg(pb.batting_stats_bref, SEASON)
    sc = _safe_fg(pb.statcast_batter_percentile_ranks, SEASON)
    return _build_batting(br, sc)


@st.cache_data(ttl=3600, show_spinner=False)
def load_pitching():
    csv = _load_csv("pitching")
    if csv is not None:
        return csv
    brp = _safe_fg(pb.pitching_stats_bref, SEASON)
    scp = _safe_fg(pb.statcast_pitcher_percentile_ranks, SEASON)
    return _build_pitching(brp, scp)


@st.cache_data(ttl=3600, show_spinner=False)
def load_batting_expected():
    try:
        return pb.statcast_batter_expected_stats(SEASON)
    except Exception as e:
        logger.error("statcast_batter_expected_stats: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_pitching_expected():
    try:
        return pb.statcast_pitcher_expected_stats(SEASON)
    except Exception as e:
        logger.error("statcast_pitcher_expected_stats: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_fielding():
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_sprint():
    df = _load_csv("sprint")
    if df is not None:
        return df
    try:
        return pb.statcast_sprint_speed(SEASON)
    except Exception as e:
        logger.error("statcast_sprint_speed fallo: %s", e)
        return pd.DataFrame()


# ── Helpers de negocio ──────────────────────────────────────────────────────

def detect_role(name: str, bat_df: pd.DataFrame, pit_df: pd.DataFrame) -> str:
    is_bat = name in bat_df["Name"].values
    is_pit = name in pit_df["Name"].values
    if is_bat and is_pit:
        return "two-way"
    elif is_pit:
        return "pitcher"
    return "batter"


def _merge_expected(data_dict: dict, exp_df: pd.DataFrame, rename_map: list) -> None:
    if exp_df is None or exp_df.empty:
        return

    matched = pd.Series(dtype=object)

    # Intento 1: por player_id (solo funciona cuando mlbID viene de fetch en vivo)
    mlb_id = data_dict.get("mlbID")
    if mlb_id is not None and "player_id" in exp_df.columns:
        try:
            pid = int(pd.to_numeric(mlb_id, errors="coerce"))
            tmp = exp_df.copy()
            tmp["player_id"] = pd.to_numeric(tmp["player_id"], errors="coerce")
            hit = tmp[tmp["player_id"] == pid]
            if not hit.empty:
                matched = hit.iloc[0]
        except (ValueError, TypeError):
            pass

    # Intento 2: por nombre "Last, First" (cubre cuando datos vienen del CSV)
    if matched.empty and "last_name, first_name" in exp_df.columns:
        name = data_dict.get("Name", "")
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            last_first = f"{parts[1]}, {parts[0]}"
            exp_copy = exp_df.copy()
            exp_copy["_fn"] = exp_copy["last_name, first_name"].str.lower()
            hit = exp_copy[exp_copy["_fn"] == last_first.lower()]
            if not hit.empty:
                matched = hit.iloc[0]

    if matched.empty:
        return

    seen: set = set()
    for src_col, v_key in rename_map:
        if v_key in seen:
            continue
        if src_col in matched.index and not pd.isna(matched[src_col]):
            data_dict[v_key] = matched[src_col]
            seen.add(v_key)


def get_player_data(name: str, bat_df, pit_df, field_df, sprint_df,
                    bat_exp_df=None, pit_exp_df=None) -> dict:
    role = detect_role(name, bat_df, pit_df)
    result = {"name": name, "role": role}

    if role in ("batter", "two-way"):
        row = bat_df[bat_df["Name"] == name]
        result["batting"] = row.iloc[0].to_dict() if not row.empty else {}
        if result["batting"]:
            _merge_expected(result["batting"], bat_exp_df, _BAT_EXP_RENAME)

    if role in ("pitcher", "two-way"):
        row = pit_df[pit_df["Name"] == name]
        result["pitching"] = row.iloc[0].to_dict() if not row.empty else {}
        if result["pitching"]:
            _merge_expected(result["pitching"], pit_exp_df, _PIT_EXP_RENAME)

    result["fielding"] = []

    if not sprint_df.empty:
        sprint_df = sprint_df.copy()
        sprint_df["full_name"] = sprint_df["last_name, first_name"].apply(
            lambda x: " ".join(reversed(x.split(", ")))
            if isinstance(x, str) and ", " in x else x
        )
        srow = sprint_df[sprint_df["full_name"].str.lower() == name.lower()]
        result["sprint"] = srow.iloc[0].to_dict() if not srow.empty else {}
    else:
        result["sprint"] = {}

    return result
