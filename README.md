# Observatorio de Energía y Clima - EA1 (Capa Bronce)

## 📌 Objetivo del Proyecto
El objetivo de este proyecto es construir un pipeline de datos robusto en Python para la extracción e ingesta de datos en estado crudo (Capa Bronce) en formato **Parquet** y la generación de muestras representativas en formato **CSV**. El pipeline integra información de variables energéticas, climáticas y financieras para el análisis dentro del Observatorio de Energía y Clima.

---

## 👤 Integrante y Roles
* **Estudiante:** Cristian Vicioso
* **Modalidad:** Trabajo Individual
* **Roles Asumidos:**
  * **Data Engineer:** Diseño e implementación de extractores (APIs, Web/SoQL, Excel) y orquestación del pipeline (`src/pipeline.py`).
  * **Data Quality Analyst:** Perfilamiento de datos e identificación de hallazgos de calidad en `docs/perfilamiento.md`.
  * **Analytics Engineer:** Estructuración del repositorio, arquitectura modular y suite de pruebas unitarias (`pytest`).
  * **BI Analyst:** Definición del alcance analítico y requerimientos de fuentes.

---

## 🗄️ Fuentes de Datos Ingestadas

1. **XM - Generación y Recursos (API REST):** Datos de generación del Sistema Interconectado Nacional y catálogo de recursos.
2. **IDEAM (Datos Abiertos / Socrata):** Registro de datos climáticos de temperatura a nivel nacional.
3. **NOAA - Índice ONI (Web Scraper/Data File):** Histórico del Índice Oceánico El Niño para análisis de variabilidad climática.
4. **EnerAndes (Dataset Interno Excel):** Registro histórico de ventas de energía 2023 - 2026.
5. **Fuente Propia Adicional (TRM Colombia - Socrata):** Tasa de Cambio Representativa del Mercado para evaluar la correlación entre la tasa cambiaria y los precios de bolsa de energía.

---

## 🛠️ Instrucciones de Ejecución

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/cristianvicioso/pi4-observatorio-energia-Vicioso.git](https://github.com/cristianvicioso/pi4-observatorio-energia-Vicioso.git)
   cd pi4-observatorio-energia-Vicioso