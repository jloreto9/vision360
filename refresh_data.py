"""
Genera los CSVs completos en data/. Ejecutar localmente antes de cada deploy:
    python refresh_data.py
"""
from pathlib import Path
import pybaseball as pb
import pandas as pd
from data_loader import SEASON, _build_batting, _build_pitching, _safe_fg

pb.cache.enable()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def save(name: str, df: pd.DataFrame):
    if df is None or df.empty:
        print(f"  [!] {name}: DataFrame vacío, no se guardó.")
        return
    path = DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  [✓] {name}: {len(df)} filas -> data/{name}.csv")


print(f"=== Actualizando datos MLB para temporada {SEASON} ===")

# 1. Bateo
print("1. Descargando datos de bateo...")
br_bat = _safe_fg(pb.batting_stats_bref, SEASON)
sc_bat_ranks = _safe_fg(pb.statcast_batter_percentile_ranks, SEASON)
exp_bat = _safe_fg(pb.statcast_batter_expected_stats, SEASON)
ev_bat = _safe_fg(getattr(pb, "statcast_batter_exitvelo_barrels", lambda *a: pd.DataFrame()), SEASON)

bat_final = _build_batting(br_bat, sc_bat_ranks, exp_bat, ev_bat)
save("batting", bat_final)
save("batting_expected", exp_bat)
save("batting_exitvelo", ev_bat)

# 2. Pitcheo
print("2. Descargando datos de pitcheo...")
br_pit = _safe_fg(pb.pitching_stats_bref, SEASON)
sc_pit_ranks = _safe_fg(pb.statcast_pitcher_percentile_ranks, SEASON)
exp_pit = _safe_fg(pb.statcast_pitcher_expected_stats, SEASON)
ev_pit = _safe_fg(getattr(pb, "statcast_pitcher_exitvelo_barrels", lambda *a: pd.DataFrame()), SEASON)

pit_final = _build_pitching(br_pit, sc_pit_ranks, exp_pit, ev_pit)
save("pitching", pit_final)
save("pitching_expected", exp_pit)
save("pitching_exitvelo", ev_pit)

# 3. Defensa
print("3. Descargando datos de defensa (Baseball Reference)...")
try:
    field_df = _safe_fg(pb.fielding_stats_bref, SEASON)
    if not field_df.empty and "Tm" in field_df.columns:
        field_df = field_df.rename(columns={"Tm": "Team"})
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

print("=== Proceso de actualización finalizado. ===")
