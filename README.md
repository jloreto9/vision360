# ⚾ Vision 360 — MLB Player Comparison App

[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B.svg?style=flat&logo=streamlit)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python)](https://python.org)
[![Plotly](https://img.shields.io/badge/Plotly-5.20+-3F4F75.svg?style=flat&logo=plotly)](https://plotly.com/)
[![MLB Statcast](https://img.shields.io/badge/Data-MLB_Statcast_%26_FanGraphs-002D72.svg?style=flat)](https://baseballsavant.mlb.com/)

**Vision 360** es una plataforma analítica interactiva desarrollada en **Streamlit** para la comparación *head-to-head* (frente a frente) de jugadores de las Grandes Ligas (MLB), cubriendo todas las dimensiones del juego con una visión integral de 360 grados: bateo, pitcheo, calidad de contacto Statcast, métricas esperadas, velocidad de sprint y fildeo defensivo.

Desarrollada por **Jorge Leonardo Loreto** (*AI Data Scientist & Baseball Analytics*).

---

## 🌟 Características Principales

1. **🕸️ Radar 360 Interactivo (Statcast Percentiles 0–100):**
   - Gráfico polar superpuesto en Plotly con tema *Dark Navy glass* de alto contraste.
   - *Bateadores:* `xwOBA`, `Barrel%`, `Exit Velo`, `Hard Hit%`, `Whiff%`, `K%`, `BB%`.
   - *Lanzadores:* `xERA`, `xwOBA`, `FB Velo`, `K%`, `BB%`, `Whiff%`, `Barrel%`.

2. **📊 Tabla Comparativa 360° con Resumen de Ventajas:**
   - Comparación métrica por métrica organizada en 6 categorías:
     - **Tradicional (Rate):** `AVG`, `OBP`, `SLG`, `OPS`, `ISO`, `ERA`, `WHIP`, `K/9`, `BB/9`, `HR/9`, `BABIP`.
     - **Volumen:** `G`, `PA/IP`, `HR`, `R`, `RBI`, `SB`, `W`, `L`, `SV`.
     - **Statcast Esperado:** `xBA`, `xSLG`, `xwOBA`, `Exit Velo`, `Barrel%`, `Hard Hit%`, `Whiff%`.
     - **Diferenciales de Suerte / Regresión:** $\text{diff\_BA}$, $\text{diff\_SLG}$, $\text{diff\_wOBA}$, $\text{diff\_ERA}$.
     - **Defensa Statcast:** Outs Above Average (OAA), Carreras Prevenidas (*Runs Prevented*).
     - **Velocidad:** *Sprint Speed* (ft/s) y tiempo *Home to 1B*.
   - Resumen superior con contadores de ventajas y empates (*"Igual"*).

3. **🖼️ Exportación de Tarjeta Matchup (PNG) con Headshots Oficiales:**
   - Descarga de tarjeta comparativa lista para compartir en redes sociales con las fotos oficiales en alta resolución de ambos jugadores extraídas de MLB Static CDN.

4. **⚡ Statcast & Regresión:**
   - Desglose detallado entre métricas observadas y esperadas para detectar perfiles *Buy-Low* (mala suerte) o candidatos a regresión negativa (*Sell-High*).

5. **🧤 Defensa Statcast OAA & 💨 Velocidad de Sprint:**
   - Tablas dedicadas de Outs Above Average (OAA), Carreras Prevenidas y gráficos comparativos de velocidad.

6. **🔍 Filtros Rápidos de Navegación:**
   - Selector filtrable por rol (*Todos, Solo Bateadores, Solo Lanzadores*) y por franquicia de MLB en la barra lateral.

---

## 🛠️ Estructura del Repositorio

```
vision360/
├── app.py              # Aplicación principal Streamlit, UI, routing y layout
├── data_loader.py      # Ingesta, normalización canónica, percentiles empíricos y caché
├── components.py       # Visualizaciones: Radar polar Plotly, tablas y generador PNG
├── refresh_data.py     # Pipeline de sincronización de datasets locales en data/
├── data/               # Datasets precargados para funcionamiento offline y Cloud
│   ├── batting.csv
│   ├── pitching.csv
│   ├── batting_expected.csv
│   ├── pitching_expected.csv
│   ├── batting_exitvelo.csv
│   ├── pitching_exitvelo.csv
│   ├── fielding.csv
│   └── sprint.csv
├── requirements.txt    # Dependencias del proyecto
├── .streamlit/
│   └── config.toml     # Configuración de tema oscuro y layout
└── CLAUDE.md           # Guía técnica y convenciones del repositorio
```

---

## 🚀 Instalación y Uso

### 1. Clonar el repositorio
```bash
git clone https://github.com/jloreto9/vision360.git
cd vision360
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación
```bash
streamlit run app.py
```

### 4. Actualizar datos locales
```bash
python refresh_data.py
```

---

## 📊 Fuentes de Datos

- **MLB Statcast / Baseball Savant:** Métricas esperadas ($xBA, xSLG, xwOBA, xERA$), percentiles de calidad de contacto, velocidad de sprint y Outs Above Average (OAA).
- **FanGraphs & Baseball Reference:** Estadísticas tradicionales de conteo y ratios.
- **MLB Static CDN:** Headshots oficiales y logos de franquicias.

---

## 👨‍💻 Autor

**Jorge Leonardo Loreto**  
*Economista & AI Data Scientist — Especialista en Sabermetría y Modelado Analítico*

- **GitHub:** [@jloreto9](https://github.com/jloreto9)
- **Portafolio:** [jloreto9.github.io/jloreto9](https://jloreto9.github.io/jloreto9/)
- **LinkedIn:** [linkedin.com/in/jloreto](https://www.linkedin.com/in/jloreto/)

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT — para más detalles, revisa el archivo de licencia correspondiente.
