# CLAUDE.md — Vision 360: Baseball Player Comparison App

## Propósito del proyecto

Aplicación Streamlit de comparación *head-to-head* entre jugadores de MLB con visión integral 360° (bateo, pitcheo, Statcast, defensa, velocidad y calidad de contacto).
Datos vía `pybaseball` (Baseball Reference + Baseball Savant / Statcast). Uso personal. Temporada activa = `SEASON = 2026`.

---

## Estructura del repositorio

```
vision360/
├── app.py              # Entrada principal Streamlit — UI, filtros (rol/equipo), headshots MLB, tabs
├── data_loader.py      # Carga, caché, normalización de nombres, percentiles empíricos, Statcast y defensa
├── components.py       # Visualizaciones: radar polar, tablas comparativas, métricas diferenciales, tarjeta PNG
├── refresh_data.py     # Ingesta completa y generación de CSVs en data/
├── data/               # CSVs cacheados locales (batting, pitching, fielding, sprint, expected)
├── requirements.txt
├── .streamlit/
│   └── config.toml     # Tema oscuro, layout wide
└── CLAUDE.md
```

**Regla:** Mantener una arquitectura minimalista y directa. No agregar archivos fuera de esta estructura sin justificación explícita.

---

## Stack y dependencias

| Componente | Librería | Notas |
|---|---|---|
| UI | `streamlit>=1.35.0` | layout="wide" siempre |
| Datos MLB | `pybaseball>=2.2.7` | caché habilitado con `pb.cache.enable()` |
| Visualización | `plotly>=5.20.0` | Solo Plotly — no matplotlib, no altair |
| Datos tabulares | `pandas>=2.0.0` | |
| Numérico | `numpy>=1.26.0` | |
| Exportación de imagen | `Pillow>=10.0.0` | Generación de Matchup Card en PNG |

---

## Convenciones de código

### General
- Python 3.10+
- Nombres de variables y funciones en `snake_case`
- Funciones de carga decoradas con `@st.cache_data(ttl=3600)`
- Temporada centralizada en la constante `SEASON = 2026` en `data_loader.py`
- DataFrames mostrados al usuario con `hide_index=True`

### Manejo de errores y resiliencia
- Toda llamada a `pybaseball` va dentro de `_safe_fg()` o bloques `try/except`
- Si un jugador no tiene datos en una métrica, formatear como `"N/D"` — nunca crashear
- Valores `NaN` en percentiles de radar se imputan con percentil empírico local (`_add_empirical_percentiles`) o `50` neutro
- Normalización avanzada de nombres con `normalize_name_key()` para empatar sufijos (`Jr.`, `II`, `III`), acentos y formatos `Last, First` vs `First Last`

### Detección de rol y fotos oficiales
- `role = detect_role(name, bat_df, pit_df)` → `"batter"`, `"pitcher"`, o `"two-way"`
- Preservación de `mlbID` para enlace con headshots oficiales en alta definición:
  `https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/w_213,q_auto:best/v1/people/{mlbID}/headshot/67/current`

### Normalización de métricas (radar)
- Escala: 0–100 percentil dentro de la distribución Statcast
- Ejes radiales etiquetados con `cfg["label"]` legible (`xwOBA`, `Barrel%`, `Exit Velo`, `Hard Hit%`, `Whiff%`, `K%`, `BB%`)
- `higher_is_better=False` invierte la escala adecuadamente

---

## Paleta de colores

| Elemento | Color |
|---|---|
| Jugador 1 | `#E63946` (rojo) |
| Jugador 2 | `#457B9D` (azul acero) |
| Fondo de radar | `rgba(15, 23, 42, 0.40)` (dark navy glass) |
| Grid y líneas | `rgba(255, 255, 255, 0.15)` |
| Texto en gráficas | `#FFFFFF` |

---

## Tabs de la aplicación

| Tab | Contenido | Archivo responsable |
|---|---|---|
| 🕸️ Radar 360 | Radar polar interactivo normalizado (0–100) con alto contraste | `components.py → build_radar()` |
| 📊 Stats Comparados | Tabla tabular con deltas, conteo de ventajas y exportación a PNG | `components.py → build_comparison_table()` & `build_comparison_image()` |
| ⚡ Statcast & Regresión | Desglose de métricas esperadas ($xBA, xSLG, xwOBA, xERA$) y diferenciales de suerte | `app.py` + `data_loader.py` |
| 🧤 Defensa | Registros defensivos por posición (G, GS, Inn, PO, A, E, DP, Fld%) | `data_loader.py → load_fielding()` |
| 💨 Velocidad | Sprint speed (ft/s) y tiempo Home-to-1B con barra comparativa | `components.py → build_sprint_row()` |

---

## Comandos útiles

```bash
# Correr la app localmente
streamlit run app.py

# Actualizar y pre-cargar todos los CSVs en data/
python refresh_data.py

# Limpiar caché de pybaseball
python -c "import pybaseball as pb; pb.cache.purge()"
```