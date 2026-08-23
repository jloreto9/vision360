"""
Genera y actualiza los CSVs completos en data/ para toda la MLB (sin cortes de mínimos).
Ejecutar localmente o en GitHub Actions:
    python refresh_data.py
"""
from pathlib import Path
import pybaseball as pb
import pandas as pd
from data_loader import (
    SEASON, _build_batting, _build_pitching, _safe_fg,
    clean_display_name, normalize_name_key
)

pb.cache.enable()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def sanitize_dataframe_names(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia nombres corruptos antes de guardar en disco."""
    if df is None or df.empty:
        return df
    df = df.copy()
    for col in ["Name", "last_name, first_name", "player_name"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_display_name)
    return df


def save(name: str, df: pd.DataFrame):
    if df is None or df.empty:
        print(f"  [!] {name}: DataFrame vacio, no se guardo.")
        return
    df = sanitize_dataframe_names(df)
    path = DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  [OK] {name}: {len(df)} filas -> data/{name}.csv")


print(f"=== Actualizando datos MLB completos para temporada {SEASON} ===")

# 1. Bateo: Expected Stats (minPA=1), Exit Velo (minBBE=1), Percentile Ranks
print("1. Descargando datos Statcast de Bateo (cobertura total)...")
try:
    exp_bat = pb.statcast_batter_expected_stats(SEASON, minPA=1)
except Exception:
    exp_bat = _safe_fg(pb.statcast_batter_expected_stats, SEASON)

try:
    ev_bat = pb.statcast_batter_exitvelo_barrels(SEASON, minBBE=1)
except Exception:
    ev_bat = _safe_fg(getattr(pb, "statcast_batter_exitvelo_barrels", lambda *a: pd.DataFrame()), SEASON)

sc_bat = _safe_fg(pb.statcast_batter_percentile_ranks, SEASON)

save("batting_expected", exp_bat)
save("batting_exitvelo", ev_bat)

# Actualizar batting.csv existente si bref falla
br_bat = _safe_fg(pb.batting_stats_bref, SEASON)
if br_bat.empty and (DATA_DIR / "batting.csv").exists():
    print("  [i] Usando batting.csv base para enriquecer con Statcast...")
    bat_base = pd.read_csv(DATA_DIR / "batting.csv")
    bat_final = _build_batting(bat_base, sc_bat, exp_bat, ev_bat)
else:
    bat_final = _build_batting(br_bat, sc_bat, exp_bat, ev_bat)
save("batting", bat_final)

# 2. Pitcheo: Expected Stats (minPA=1), Exit Velo (minBBE=1), Percentile Ranks
print("2. Descargando datos Statcast de Pitcheo (cobertura total)...")
try:
    exp_pit = pb.statcast_pitcher_expected_stats(SEASON, minPA=1)
except Exception:
    exp_pit = _safe_fg(pb.statcast_pitcher_expected_stats, SEASON)

try:
    ev_pit = pb.statcast_pitcher_exitvelo_barrels(SEASON, minBBE=1)
except Exception:
    ev_pit = _safe_fg(getattr(pb, "statcast_pitcher_exitvelo_barrels", lambda *a: pd.DataFrame()), SEASON)

sc_pit = _safe_fg(pb.statcast_pitcher_percentile_ranks, SEASON)

save("pitching_expected", exp_pit)
save("pitching_exitvelo", ev_pit)

br_pit = _safe_fg(pb.pitching_stats_bref, SEASON)
if br_pit.empty and (DATA_DIR / "pitching.csv").exists():
    print("  [i] Usando pitching.csv base para enriquecer con Statcast...")
    pit_base = pd.read_csv(DATA_DIR / "pitching.csv")
    pit_final = _build_pitching(pit_base, sc_pit, exp_pit, ev_pit)
else:
    pit_final = _build_pitching(br_pit, sc_pit, exp_pit, ev_pit)
save("pitching", pit_final)

# 3. Defensa (Statcast OAA con min_att=0 para incluir todos los jugadores)
print("3. Descargando defensa Statcast OAA (sin filtro de calificacion)...")
try:
    from pybaseball.statcast_fielding import statcast_outs_above_average
    field_df = statcast_outs_above_average(SEASON, "all", min_att=0)
    save("fielding", field_df)
except Exception as e:
    print(f"  [!] fielding: Error {e}")

# 4. Velocidad de Sprint (min_opp=1)
print("4. Descargando velocidad de sprint Statcast...")
try:
    sprint_df = pb.statcast_sprint_speed(SEASON, min_opp=1)
    save("sprint", sprint_df)
except Exception as e:
    print(f"  [!] sprint: Error {e}")

print("=== Proceso de actualizacion finalizado exitosamente. ===")
