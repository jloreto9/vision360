"""
Genera los CSVs en data/. Ejecutar localmente antes de cada deploy.
  python refresh_data.py
"""
import pybaseball as pb
from pathlib import Path
from data_loader import SEASON, _build_batting, _build_pitching

pb.cache.enable()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def save(name, df):
    if df.empty:
        print(f"  {name}: DataFrame vacío, no se guarda.")
        return
    path = DATA_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  {name}: {len(df)} filas -> data/{name}.csv")


print("Descargando batting (Baseball Reference)...")
br = pb.batting_stats_bref(SEASON)
print("Descargando batter percentile ranks (Statcast)...")
sc = pb.statcast_batter_percentile_ranks(SEASON)
save("batting", _build_batting(br, sc))

print("Descargando pitching (Baseball Reference)...")
brp = pb.pitching_stats_bref(SEASON)
print("Descargando pitcher percentile ranks (Statcast)...")
scp = pb.statcast_pitcher_percentile_ranks(SEASON)
save("pitching", _build_pitching(brp, scp))

print("Descargando sprint speed (Statcast)...")
try:
    sprint = pb.statcast_sprint_speed(SEASON)
    save("sprint", sprint)
except Exception as e:
    print(f"  sprint: ERROR {e}")

print("Listo.")
