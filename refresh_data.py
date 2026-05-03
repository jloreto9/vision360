"""
Genera los CSVs en data/. Ejecutar localmente antes de cada deploy.
  python refresh_data.py
"""
import pybaseball as pb
from pathlib import Path

pb.cache.enable()

SEASON = 2026
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def refresh(name, func, *args, **kwargs):
    print(f"Descargando {name}...", end=" ", flush=True)
    try:
        df = func(*args, **kwargs)
        df.to_csv(DATA_DIR / f"{name}.csv", index=False)
        print(f"{len(df)} filas -> data/{name}.csv")
    except Exception as e:
        print(f"ERROR: {e}")


refresh("batting",  pb.batting_stats,         SEASON, SEASON, qual=50)
refresh("pitching", pb.pitching_stats,        SEASON, SEASON, qual=20)
refresh("fielding", pb.fielding_stats,        SEASON, SEASON, qual=50)
refresh("sprint",   pb.statcast_sprint_speed, SEASON)
