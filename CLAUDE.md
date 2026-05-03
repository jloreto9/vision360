# CLAUDE.md — Vision 360: Baseball Player Comparison App

## Propósito del proyecto

Aplicación Streamlit de comparación head-to-head entre jugadores de MLB con visión 360°.
Datos vía `pybaseball` (FanGraphs + Baseball Savant/Statcast). Uso personal. Temporada activa = 2025.

---

## Estructura del repositorio

```
vision360/
├── app.py              # Entrada principal Streamlit — UI, tabs, routing
├── data_loader.py      # Carga, caché y normalización de datos
├── components.py       # Visualizaciones: radar, tablas, gráficas
├── requirements.txt
├── .streamlit/
│   └── config.toml     # Tema oscuro, layout wide
└── CLAUDE.md
```

**Regla:** no agregar archivos fuera de esta estructura sin justificación explícita.
Si se necesita un módulo nuevo (e.g., `lvbp_loader.py`), documentarlo aquí antes de crearlo.

---

## Stack y dependencias

| Componente | Librería | Notas |
|---|---|---|
| UI | `streamlit>=1.35.0` | layout="wide" siempre |
| Datos MLB | `pybaseball>=2.2.7` | caché habilitado con `pb.cache.enable()` |
| Visualización | `plotly>=5.20.0` | Solo Plotly — no matplotlib, no altair |
| Datos tabulares | `pandas>=2.0.0` | |
| Numérico | `numpy>=1.26.0` | |

**No agregar** librerías nuevas sin actualizar `requirements.txt` y este documento.

---

## Convenciones de código

### General
- Python 3.11+
- Nombres de variables en `snake_case`
- Funciones de carga siempre decoradas con `@st.cache_data(ttl=3600)`
- Nunca hardcodear temporada en más de un lugar — usar la constante `SEASON = 2025` en `data_loader.py`
- Todos los DataFrames que se muestran al usuario usan `hide_index=True`

### Manejo de errores
- Toda llamada a `pybaseball` va dentro de `_safe_fg()` o equivalente con try/except
- Si un jugador no tiene datos en una dimensión, mostrar `"N/D"` — nunca crashear
- Valores NaN en métricas del radar se normalizan a 50 (neutro) — no imputar con 0

### Detección de rol
- `role = detect_role(name, bat_df, pit_df)` → `"batter"`, `"pitcher"`, o `"two-way"`
- Two-way = jugador presente en ambas tablas FanGraphs simultáneamente
- Threshold mínimo de IP para calificar como pitcher: actualmente sin límite explícito (FanGraphs `qual=20` lo filtra). Si se ajusta, documentar aquí.

### Normalización de métricas (radar)
- Escala: 0–100 por percentil dentro del rango configurado en `RADAR_METRICS_BAT` / `RADAR_METRICS_PIT`
- `higher_is_better=False` invierte la escala (K%, ERA-, BB/9, etc.)
- **No cambiar los rangos de escala sin revisar distribución histórica de la métrica**

---

## Paleta de colores

| Elemento | Color |
|---|---|
| Jugador 1 | `#E63946` (rojo) |
| Jugador 2 | `#457B9D` (azul acero) |
| Fondo de gráficas | `rgba(0,0,0,0)` (transparente) |
| Fuente en gráficas | `white` |

Estos colores son fijos. No cambiarlos sin actualizar todos los componentes simultáneamente.

---

## Fuentes de datos y limitaciones conocidas

### FanGraphs vía pybaseball
- `batting_stats(SEASON, SEASON, qual=50)` — mínimo 50 PA para aparecer
- `pitching_stats(SEASON, SEASON, qual=20)` — mínimo 20 IP
- `fielding_stats(SEASON, SEASON, qual=50)` — incluye UZR/150 y DRS, **no OAA**
- Lag típico: 24–48h respecto a juegos reales

### Statcast vía pybaseball
- `statcast_sprint_speed(SEASON)` — nombres en formato `"apellido, nombre"` → se normaliza en `get_player_data()`
- OAA disponible vía `statcast_fielding()` — **pendiente de integrar** (ver Roadmap)

### Regla de nombres
- Los nombres de jugadores en FanGraphs y Statcast **no siempre coinciden**
- El matching de sprint speed usa comparación `.lower()` — es case-insensitive pero sensible a acentos y apodos
- Si hay mismatch, registrarlo como issue conocido antes de parchear

---

## Tabs de la aplicación

| Tab | Contenido | Archivo responsable |
|---|---|---|
| 🕸️ Radar 360 | Radar chart normalizado, solo si ambos jugadores comparten rol | `components.py → build_radar()` |
| 📊 Stats Comparados | Tabla con delta coloreado y columna "Ventaja" | `components.py → build_comparison_table()` |
| 🧤 Defensa | UZR/150, DRS por posición | `components.py` + `data_loader.py` |
| 💨 Velocidad | Sprint speed, HP→1B, barra comparativa | `components.py → build_sprint_row()` |

---

## Roadmap de extensiones (planificadas)

### v1.1 — Statcast avanzado + OAA
- Integrar `statcast_fielding()` para OAA real
- Agregar métricas Statcast de bateo: `xBA`, `xSLG`, `xwOBA`, `Hard Hit%`, `Barrel%`, `Exit Velocity avg`
- Nuevo tab: **🎯 Statcast** separado del radar actual

### v1.2 — Comparación multi-jugador (3+)
- Cambiar `selectbox` a `multiselect` con máximo configurable (sugerido: 4)
- Radar con trazos múltiples (ya soportado por Plotly `Scatterpolar`)
- Tabla comparativa con N columnas dinámicas
- Lógica de "ventaja" cambia a ranking 1–N por métrica

### v1.3 — Deploy Streamlit Cloud
- Agregar `.streamlit/secrets.toml` para variables de entorno si se integra Supabase
- `requirements.txt` debe ser reproducible con versiones fijas (`==` no `>=`) para el deploy
- Cacheo en disco de pybaseball debe deshabilitarse o redirigirse en Cloud (verificar path de caché)
- Agregar `README.md` con badge de Streamlit Cloud antes del deploy

---

## Lo que Claude Code NO debe hacer en este repo

- ❌ No usar `matplotlib` ni `seaborn` — solo Plotly
- ❌ No modificar `SEASON` inline en funciones — siempre importar la constante
- ❌ No añadir autenticación de usuarios (app personal, sin login)
- ❌ No crear endpoints API (FastAPI, Flask, etc.) — la app es solo Streamlit
- ❌ No cambiar el esquema de `get_player_data()` sin actualizar todos los consumidores (`app.py`, `components.py`)
- ❌ No imputar NaN con 0 en métricas de rendimiento — usar 50 (neutro) en radar, `"N/D"` en tablas
- ❌ No agregar datos de LVBP/Supabase en esta versión — está reservado para un módulo separado futuro

---

## Comandos útiles

```bash
# Correr la app localmente
streamlit run app.py

# Instalar dependencias
pip install -r requirements.txt

# Limpiar caché de pybaseball si los datos están desactualizados
python -c "import pybaseball as pb; pb.cache.purge()"

# Ver versión de dependencias instaladas
pip freeze | grep -E "streamlit|pybaseball|plotly|pandas"
```

---

*Última actualización: Mayo 2025 · Autor: Jorge Loreto (jloreto9)*