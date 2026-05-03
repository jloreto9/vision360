import logging
import streamlit as st
import pybaseball as pb
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

pb.cache.enable()

SEASON = 2026

# ── Columnas por dimensión ──────────────────────────────────────────────────

BAT_COLS = [
    "Name", "Team", "G", "PA", "HR", "R", "RBI", "SB",
    "BB%", "K%", "AVG", "OBP", "SLG", "OPS", "wOBA",
    "wRC+", "ISO", "BABIP", "Off", "Def", "BsR", "WAR"
]

PIT_COLS = [
    "Name", "Team", "G", "GS", "IP", "W", "L", "SV",
    "ERA", "FIP", "xFIP", "WHIP", "K/9", "BB/9", "HR/9",
    "K%", "BB%", "BABIP", "LOB%", "SwStr%", "ERA-", "FIP-", "WAR"
]

FIELD_COLS = ["Name", "Team", "Pos", "Inn", "UZR/150", "DRS", "OAA"]

SPRINT_COLS = ["last_name, first_name", "sprint_speed", "hp_to_1b", "competitive_runs"]


def _safe_fg(func, *args, **kwargs):
    try:
        df = func(*args, **kwargs)
        return df
    except Exception as e:
        logger.error("%s(%s %s) falló: %s", func.__name__, args, kwargs, e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_batting():
    df = _safe_fg(pb.batting_stats, SEASON, SEASON, qual=50)
    cols = [c for c in BAT_COLS if c in df.columns]
    return df[cols].copy()


@st.cache_data(ttl=3600, show_spinner=False)
def load_pitching():
    df = _safe_fg(pb.pitching_stats, SEASON, SEASON, qual=20)
    cols = [c for c in PIT_COLS if c in df.columns]
    return df[cols].copy()


@st.cache_data(ttl=3600, show_spinner=False)
def load_fielding():
    df = _safe_fg(pb.fielding_stats, SEASON, SEASON, qual=50)
    cols = [c for c in FIELD_COLS if c in df.columns]
    return df[cols].copy()


@st.cache_data(ttl=3600, show_spinner=False)
def load_sprint():
    try:
        df = pb.statcast_sprint_speed(SEASON)
        return df
    except Exception:
        return pd.DataFrame()


def detect_role(name: str, bat_df: pd.DataFrame, pit_df: pd.DataFrame) -> str:
    """Retorna 'batter', 'pitcher', o 'two-way'."""
    is_bat = name in bat_df["Name"].values
    is_pit = name in pit_df["Name"].values
    if is_bat and is_pit:
        return "two-way"
    elif is_pit:
        return "pitcher"
    return "batter"


def get_player_data(name: str, bat_df, pit_df, field_df, sprint_df) -> dict:
    role = detect_role(name, bat_df, pit_df)
    result = {"name": name, "role": role}

    if role in ("batter", "two-way"):
        row = bat_df[bat_df["Name"] == name]
        result["batting"] = row.iloc[0].to_dict() if not row.empty else {}

    if role in ("pitcher", "two-way"):
        row = pit_df[pit_df["Name"] == name]
        result["pitching"] = row.iloc[0].to_dict() if not row.empty else {}

    # Fielding
    if not field_df.empty and "Name" in field_df.columns:
        frow = field_df[field_df["Name"] == name]
        result["fielding"] = frow.to_dict("records") if not frow.empty else []

    # Sprint speed
    if not sprint_df.empty:
        sprint_df["full_name"] = sprint_df["last_name, first_name"].apply(
            lambda x: " ".join(reversed(x.split(", "))) if isinstance(x, str) and ", " in x else x
        )
        srow = sprint_df[sprint_df["full_name"].str.lower() == name.lower()]
        result["sprint"] = srow.iloc[0].to_dict() if not srow.empty else {}

    return result