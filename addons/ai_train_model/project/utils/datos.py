import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns

def cargar_multiples_archivos(archivos_csv):
    """Carga y combina datos de múltiples archivos CSV"""
    print(f"Cargando datos desde {len(archivos_csv)} archivos...")
    dataframes = []
    for archivo in archivos_csv:
        print(f"Procesando: {archivo}")
        try:
            df = pd.read_csv(archivo)
            dataframes.append(df)
            print(f"  - Cargadas {len(df)} filas y {len(df.columns)} columnas")
        except Exception as e:
            print(f"  - Error al cargar {archivo}: {str(e)}")
    if not dataframes:
        raise ValueError("No se pudo cargar ningún archivo de datos")
    datos_combinados = pd.concat(dataframes, ignore_index=True)
    filas_originales = len(datos_combinados)
    datos_combinados = datos_combinados.drop_duplicates()
    filas_unicas = len(datos_combinados)
    print(f"Se eliminaron {filas_originales - filas_unicas} filas duplicadas")
    print(f"Conjunto final: {filas_unicas} filas y {len(datos_combinados.columns)} columnas")
    return datos_combinados

def preprocesar_datos(datos, columnas_objetivo, columnas_excluir=None, usar_fechas=True, directorio_salida='resultados'):
    """
    Preprocesa los datos para el entrenamiento del modelo y genera una matriz de correlación.
    
    Args:
        datos: DataFrame con los datos a procesar
        columnas_objetivo: Lista de columnas objetivo para el análisis
        columnas_excluir: Lista de columnas a excluir del procesamiento (opcional)
        usar_fechas: Boolean que indica si se deben procesar las columnas de fecha (por defecto True)
        directorio_salida: Ruta donde se guardarán las matrices de correlación (por defecto 'resultados')
    """
    print("Preprocesando datos...")
    df = datos.copy()
    datos_originales = df.copy()
    if columnas_excluir is None:
        columnas_excluir = []
    columnas_procesadas = []

    # Procesar fechas si se solicita
    if 'date' in df.columns and usar_fechas:
        print("Convirtiendo la columna 'date' a formato datetime...")
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        print("Extrayendo características de fechas...")
        df['año'] = df['date'].dt.year
        df['mes'] = df['date'].dt.month
        df['dia_mes'] = df['date'].dt.day
        df['dia_semana'] = df['date'].dt.dayofweek
        df['dia_año'] = df['date'].dt.dayofyear
        df['trimestre'] = df['date'].dt.quarter
        df['es_fin_semana'] = df['date'].dt.dayofweek.isin([5, 6]).astype(int)
        df['sin_mes'] = np.sin(2 * np.pi * df['mes'] / 12)
        df['cos_mes'] = np.cos(2 * np.pi * df['mes'] / 12)
        df['sin_dia_mes'] = np.sin(2 * np.pi * df['dia_mes'] / 31)
        df['cos_dia_mes'] = np.cos(2 * np.pi * df['dia_mes'] / 31)
        df['sin_dia_semana'] = np.sin(2 * np.pi * df['dia_semana'] / 7)
        df['cos_dia_semana'] = np.cos(2 * np.pi * df['dia_semana'] / 7)
        columnas_excluir.append('date')
        columnas_procesadas.extend(['año', 'mes', 'dia_mes', 'dia_semana', 'dia_año', 'trimestre',
                                    'es_fin_semana', 'sin_mes', 'cos_mes', 'sin_dia_mes',
                                    'cos_dia_mes', 'sin_dia_semana', 'cos_dia_semana'])

    # Convertir columnas categóricas a numéricas
    print("Procesando variables categóricas...")
    columnas_categoricas = df.select_dtypes(include=['object', 'category']).columns
    if len(columnas_categoricas) > 0:
        for col in columnas_categoricas:
            print(f"  - Codificando columna categórica: {col}")
            df[col] = df[col].astype('category').cat.codes  # Convertir a códigos numéricos

    # Eliminar columnas no necesarias
    print("Eliminando columnas no necesarias...")
    columnas_a_eliminar = [col for col in columnas_excluir if col in df.columns and col not in columnas_objetivo]
    if columnas_a_eliminar:
        df = df.drop(columns=columnas_a_eliminar)

    # Generar matriz de correlación para cada columna objetivo
    print("\nGenerando matriz de correlación...")
    if not os.path.exists(directorio_salida):
        os.makedirs(directorio_salida)

    for columna_objetivo in columnas_objetivo:
        if columna_objetivo not in df.columns:
            print(f"⚠️ La columna objetivo '{columna_objetivo}' no existe en los datos. Saltando...")
            continue

        # Calcular correlaciones y filtrar valores relevantes
        correlaciones = df.corr()[[columna_objetivo]].sort_values(by=columna_objetivo, ascending=False)
        correlaciones_filtradas = correlaciones[
            (correlaciones[columna_objetivo] > 0.5) | (correlaciones[columna_objetivo] < -0.5)
        ]

        if correlaciones_filtradas.empty:
            print(f"⚠️ No se encontraron correlaciones significativas para '{columna_objetivo}'.")
            continue

        matriz_correlacion_path = os.path.join(directorio_salida, f'matriz_correlacion_{columna_objetivo}.png')

        # Crear un gráfico de calor para la matriz de correlación filtrada
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlaciones_filtradas, annot=True, cmap='coolwarm', fmt=".2f", cbar=True)
        plt.title(f'Matriz de Correlación para {columna_objetivo} (Filtrada)')
        plt.tight_layout()
        plt.savefig(matriz_correlacion_path)
        plt.close()
        print(f"Matriz de correlación filtrada para '{columna_objetivo}' guardada en: {matriz_correlacion_path}")

    # Antes de escalar, verificar y convertir tipos de datos
    print("\nVerificando tipos de datos...")
    for columna in columnas_objetivo:
        if pd.api.types.is_datetime64_any_dtype(df[columna]):
            print(f"⚠️ Convirtiendo columna datetime '{columna}' a numérica (timestamp)")
            df[columna] = df[columna].astype(np.int64) // 10**9  # Convertir a timestamp
        elif not pd.api.types.is_numeric_dtype(df[columna]):
            print(f"⚠️ La columna '{columna}' no es numérica. Intentando convertir...")
            try:
                df[columna] = pd.to_numeric(df[columna])
            except Exception as e:
                raise ValueError(f"No se pudo convertir la columna '{columna}' a numérica: {str(e)}")

    # Escalar las características
    print("Escalando características...")
    scaler = StandardScaler()
    X = scaler.fit_transform(df.drop(columns=columnas_objetivo))
    y = df[columnas_objetivo]
    print(f"Características procesadas: {df.drop(columns=columnas_objetivo).columns.tolist()}")
    print(f"Dimensiones de X: {X.shape}, Dimensiones de y: {y.shape}")
    return X, y, columnas_procesadas, datos_originales