# Proyecto de Descarga de Datos de Google Analytics 4 (GA4) y Entrenamiento de IA

Este proyecto contiene scripts para descargar datos históricos de Google Analytics 4, cargarlos a BigQuery y entrenar modelos de IA, así como utilidades para exploración y procesamiento de datos.

## Requisitos previos

1. Tener una cuenta de servicio de Google con acceso a Google Analytics 4 (GA4).
2. Instalar dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Configurar permisos adecuados para la cuenta de servicio en GA4.
4. Habilitar las APIs necesarias en la consola de Google Cloud:
   - Google Analytics Data API v1 (ga:data-beta)
   - Google Analytics Admin API v1 (analytics-admin-beta)
   - BigQuery API (para carga a BigQuery)

---

## Scripts principales

### 1. `descargar_ga_datos.py`
Descarga datos históricos de Google Analytics 4 para un rango de fechas específico.

**Uso:**
```bash
python descargar_ga_datos.py --key-file TU_ARCHIVO_DE_CREDENCIALES.json --property-id ID_DE_PROPIEDAD --start-date YYYY-MM-DD --end-date YYYY-MM-DD --output datos_analytics.csv
```
**Argumentos:**
- `--key-file`: Ruta al archivo de credenciales de la cuenta de servicio.
- `--property-id`: ID de la propiedad de GA4.
- `--start-date`: Fecha de inicio (formato `YYYY-MM-DD`).
- `--end-date`: Fecha de fin (formato `YYYY-MM-DD`).
- `--output`: Nombre del archivo CSV de salida.

---

### 2. `descargar_datos_predictivos.py`
Descarga datos predictivos de Google Analytics 4 para un modelo específico.

**Uso:**
```bash
python descargar_datos_predictivos.py --key-file TU_ARCHIVO_DE_CREDENCIALES.json --property-id ID_DE_PROPIEDAD --start-date YYYY-MM-DD --end-date YYYY-MM-DD --modelo conversiones --output datos_predictivos.csv
```
**Argumentos:**
- `--key-file`: Ruta al archivo de credenciales de la cuenta de servicio.
- `--property-id`: ID de la propiedad de GA4.
- `--start-date`: Fecha de inicio (formato `YYYY-MM-DD`).
- `--end-date`: Fecha de fin (formato `YYYY-MM-DD`).
- `--modelo`: Tipo de modelo predictivo (`conversiones`, `engagement`, `todos`).
- `--output`: Nombre del archivo CSV de salida.

---

### 3. `entrenar_modelo.py`
Entrena un modelo predictivo utilizando datos históricos descargados y admite entrenamiento incremental.

**Uso:**
```bash
python entrenar_modelo.py --archivos datos_analytics.csv --objetivos conversions --modelo-salida modelo_ga.joblib --salida resultados
```
**Argumentos:**
- `--archivos`: Lista de archivos CSV con datos históricos.
- `--objetivos`: Lista de columnas objetivo (para múltiples objetivos).
- `--modelo-salida`: Ruta para guardar el modelo entrenado (por defecto: `modelo_ga.joblib`).
- `--salida`: Directorio para guardar resultados (por defecto: `resultados`).
- `--incremental`: Entrenar el modelo de manera incremental.
- `--batch-size`: Tamaño del lote para entrenamiento incremental (por defecto: `1000`).
- `--epochs`: Número de épocas para entrenamiento incremental (por defecto: `10`).

**Ejemplo de entrenamiento incremental:**
```bash
python entrenar_modelo.py --archivos archivo1.csv --objetivos conversions --modelo-salida modelo_ga.joblib --salida resultados --incremental
python entrenar_modelo.py --archivos archivo2.csv --objetivos conversions --modelo-salida modelo_ga.joblib --salida resultados --incremental
```

---

### 4. `subir_a_bigquery.py`
Carga datos desde un archivo CSV a una tabla de BigQuery.

**Uso:**
```bash
python subir_a_bigquery.py --archivo datos_analytics.csv --proyecto TU_ID_PROYECTO --dataset TU_DATASET --tabla TU_TABLA
```
**Argumentos:**
- `--archivo`: Ruta del archivo CSV con datos.
- `--proyecto`: ID del proyecto de Google Cloud.
- `--dataset`: ID del dataset en BigQuery.
- `--tabla`: ID de la tabla en BigQuery.

---

### 5. `explorar_metricas_dimensiones.py`
Explora las métricas y dimensiones disponibles en una propiedad de GA4 y guarda la lista en CSV.

**Uso:**
```bash
python explorar_metricas_dimensiones.py --key-file TU_ARCHIVO_DE_CREDENCIALES.json --property-id ID_DE_PROPIEDAD --output ga4_metadata --ejemplo
```
**Argumentos:**
- `--key-file`: Ruta al archivo JSON de credenciales.
- `--property-id`: ID de la propiedad de GA4.
- `--output`: Nombre base para los archivos CSV de salida.
- `--ejemplo`: Mostrar datos de ejemplo usando métricas seleccionadas.

---

## Utilidades en `utils/`

- **`utils/datos.py`**: Funciones para cargar y preprocesar datos, generar matrices de correlación y escalar características.
- **`utils/evaluacion.py`**: Funciones para evaluar modelos, generar informes y gráficos de validación.
- **`utils/incremental.py`**: Funciones para entrenamiento incremental por lotes y generación de informes.
- **`utils/pipelines.py`**: Definición de pipelines de scikit-learn para modelos multiobjetivo.
- **`utils/train_column.py`**: Selección dinámica de columnas de entrenamiento, ingeniería de características y codificación de variables.

---

## Flujo de trabajo recomendado

1. **Verificar permisos** (si tienes un script para ello):
   ```bash
   python verificar_permisos_ga.py --key-file TU_ARCHIVO_DE_CREDENCIALES.json
   ```

2. **Explorar métricas y dimensiones disponibles**:
   ```bash
   python explorar_metricas_dimensiones.py --key-file TU_ARCHIVO_DE_CREDENCIALES.json --property-id ID_DE_PROPIEDAD --output ga4_metadata --ejemplo
   ```

3. **Descargar datos históricos**:
   ```bash
   python descargar_ga_datos.py --key-file TU_ARCHIVO_DE_CREDENCIALES.json --property-id ID_DE_PROPIEDAD --start-date 2023-01-01 --end-date 2023-12-31 --output ga4_data.csv
   ```

4. **Descargar datos predictivos**:
   ```bash
   python descargar_datos_predictivos.py --key-file TU_ARCHIVO_DE_CREDENCIALES.json --property-id ID_DE_PROPIEDAD --start-date 2023-01-01 --end-date 2023-12-31 --modelo conversiones --output datos_predictivos.csv
   ```

5. **Cargar datos a BigQuery**:
   ```bash
   python subir_a_bigquery.py --archivo ga4_data.csv --proyecto TU_ID_PROYECTO --dataset TU_DATASET --tabla TU_TABLA
   ```

6. **Entrenar modelo de IA**:
   ```bash
   python entrenar_modelo.py --archivos ga4_data.csv --objetivos conversions --modelo-salida modelo_ga.joblib --salida resultados
   ```

7. **Entrenamiento incremental** (opcional):
   ```bash
   python entrenar_modelo.py --archivos nuevos_datos.csv --objetivos conversions --modelo-salida modelo_ga.joblib --salida resultados --incremental
   ```

---

## Diferencias entre GA4 y Universal Analytics

### Estructura de datos
- **Universal Analytics**: Usaba Vistas y el ID de Vista.
- **GA4**: Solo Cuentas y Propiedades. Se usa el ID de Propiedad.

### API utilizada
- **Universal Analytics**: Google Analytics Reporting API v4.
- **GA4**: Google Analytics Data API v1 (beta).

### Dimensiones y métricas
- **GA4** usa nombres diferentes para dimensiones y métricas. Ejemplos:
  - `ga:sessions` → `sessions`
  - `ga:users` → `activeUsers`
  - `ga:pageviews` → `screenPageViews`
  - `ga:sourceMedium` → `sessionSource` y `sessionMedium`

---

## Solución de problemas comunes

1. **Error "No se encontraron cuentas"**:
   - Verifica permisos de la cuenta de servicio en GA4.
   - Habilita la Analytics Admin API en Google Cloud.

2. **Error "API not enabled"**:
   - Habilita Google Analytics Data API v1 y Google Analytics Admin API v1 en Google Cloud.

3. **Error "Permission denied" o "insufficient permissions"**:
   - Asegúrate de que la cuenta de servicio tiene el rol de "Lector" en la propiedad de GA4.

---

## Créditos

Desarrollado por el equipo de InProfit.  
Contacto: [info@inprofit.es](mailto:info@inprofit.es)