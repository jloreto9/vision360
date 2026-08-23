"""
Genera y actualiza los CSVs completos en data/. Ejecutar localmente antes de cada deploy:
    python refresh_data.py
"""
from pathlib import Path
import pybaseball as pb
import pandas as pd
from data_loader import SEASON, _build_batting, _build_pitching, _safe_fg, normalize_name_key

pb.cache.enable()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def save(name: str, df: pd.DataFrame):
    if df is None or df.empty:
        print(f"  [!] {name}: DataFrame vacio, no se guardo.")
        return
    path = DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  [OK] {name}: {len(df)} filas -> data/{name}.csv")


print(f"=== Actualizando datos MLB para temporada {SEASON} ===")

# 1. Bateo: Expected Stats, Exit Velo, Percentile Ranks
print("1. Descargando datos Statcast de Bateo...")
exp_bat = _safe_fg(pb.statcast_batter_expected_stats, SEASON)
ev_bat  = _safe_fg(getattr(pb, "statcast_batter_exitvelo_barrels", lambda *a: pd.DataFrame()), SEASON)
sc_bat  = _safe_fg(pb.statcast_batter_percentile_ranks, SEASON)

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

# 2. Pitcheo: Expected Stats, Exit Velo, Percentile Ranks
print("2. Descargando datos Statcast de Pitcheo...")
exp_pit = _safe_fg(pb.statcast_pitcher_expected_stats, SEASON)
ev_pit  = _safe_fg(getattr(pb, "statcast_pitcher_exitvelo_barrels", lambda *a: pd.DataFrame()), SEASON)
sc_pit  = _safe_fg(pb.statcast_pitcher_percentile_ranks, SEASON)

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

# 3. Defensa (Statcast OAA)
print("3. Descargando defensa Statcast OAA...")
try:
    from pybaseball.statcast_fielding import statcast_outs_above_average
    field_df = statcast_outs_above_average(SEASON, "all")
    save("fielding", field_df)
except Exception as e:
    print(f"  [!] fielding: Error {e}")

# 4. Velocidad de Sprint
print("4. Descargando velocidad de sprint (Statcast)...")
try:
    sprint_df = pb.statcast_sprint_speed(SEASON)
    save("sprint", sprint_df)
except Exception as e:
    print(f"  [!] sprint: Error {e}")

print("=== Proceso de actualizacion finalizado exitosamente. ===")
