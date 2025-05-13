import pandas as pd
import os
import json
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

def seleccionar_columnas_entrenamiento(df, columnas_objetivo, args):
    """
    Selecciona y procesa las columnas de entrenamiento para el modelo de forma dinámica.
    Versión optimizada para uso mínimo de memoria.
    """
    # Detectar columnas numéricas y categóricas dinámicamente
    columnas_objetivo = columnas_objetivo or []
    
    # Definir las métricas más importantes (reducidas al mínimo esencial)
    metricas_importantes = ['sessions', 'engagementRate', 'activeUsers']
    
    # Seleccionar solo las columnas numéricas importantes
    columnas_numericas = [col for col in df.columns 
                         if pd.api.types.is_numeric_dtype(df[col]) 
                         and col not in columnas_objetivo
                         and (col in metricas_importantes or 
                             any(metrica in col for metrica in metricas_importantes))]
    
    # Limitar estrictamente el número de columnas numéricas
    MAX_NUMERIC_COLUMNS = 10
    if len(columnas_numericas) > MAX_NUMERIC_COLUMNS:
        # Calcular la varianza de cada columna de forma eficiente
        varianzas = df[columnas_numericas].var()
        columnas_numericas = varianzas.nlargest(MAX_NUMERIC_COLUMNS).index.tolist()
    
    # Seleccionar solo columnas categóricas esenciales
    columnas_categoricas = [col for col in df.columns 
                          if pd.api.types.is_categorical_dtype(df[col])
                          and col not in columnas_objetivo
                          and df[col].nunique() < 10]  # Solo categorías con pocos valores únicos
    
    # Limitar estrictamente columnas categóricas
    MAX_CATEGORICAL_COLUMNS = 5
    if len(columnas_categoricas) > MAX_CATEGORICAL_COLUMNS:
        # Seleccionar las que tengan menos valores únicos
        cardinalidad = {col: df[col].nunique() for col in columnas_categoricas}
        columnas_categoricas = sorted(cardinalidad.items(), key=lambda x: x[1])[:MAX_CATEGORICAL_COLUMNS]
        columnas_categoricas = [col for col, _ in columnas_categoricas]
    
    # Crear características derivadas solo si son absolutamente necesarias
    nuevas_features = {}
    if 'sessions' in df.columns and 'activeUsers' in df.columns:
        nuevas_features['sessions_per_user'] = df['sessions'] / df['activeUsers'].replace(0, 1)
    
    # Construir el DataFrame final de manera eficiente
    dfs_to_concat = []
    
    # Agregar columnas numéricas
    if columnas_numericas:
        dfs_to_concat.append(df[columnas_numericas])
    
    # Agregar columnas categóricas (si existen)
    if columnas_categoricas:
        X_cat = pd.get_dummies(df[columnas_categoricas], prefix=columnas_categoricas, dummy_na=False)
        dfs_to_concat.append(X_cat)
        del X_cat  # Liberar memoria inmediatamente
    
    # Agregar características derivadas
    if nuevas_features:
        dfs_to_concat.append(pd.DataFrame(nuevas_features))
    
    # Concatenar todo de una vez
    X = pd.concat(dfs_to_concat, axis=1) if dfs_to_concat else pd.DataFrame()
    
    # Limpiar memoria
    del dfs_to_concat
    
    # Mapeo simplificado de nombres de columnas
    mapeo_columnas = {
        'engagementRate': ['engagementRate'],
        'sessions': ['sessions'],
        'activeUsers': ['activeUsers', 'users']
    }
    
    # Verificar columnas disponibles
    columnas_disponibles = []
    mapeo_final = {}
    
    # Simplificar la búsqueda de columnas objetivo
    if not columnas_objetivo:
        for col_deseada in mapeo_columnas:
            if col_deseada in df.columns:
                columnas_disponibles.append(col_deseada)
                mapeo_final[col_deseada] = col_deseada
    else:
        for col_deseada in columnas_objetivo:
            if col_deseada in df.columns:
                columnas_disponibles.append(col_deseada)
                mapeo_final[col_deseada] = col_deseada
            elif col_deseada in mapeo_columnas:
                for alt in mapeo_columnas[col_deseada]:
                    if alt in df.columns:
                        columnas_disponibles.append(col_deseada)
                        mapeo_final[col_deseada] = alt
                        break
    
    if not columnas_disponibles:
        raise ValueError(f"No se encontraron las columnas objetivo en el CSV. Columnas disponibles: {list(df.columns)}")
    
    # Crear DataFrame con las columnas objetivo
    y = df[[mapeo_final[col] for col in columnas_disponibles]]
    y.columns = columnas_disponibles
    
    return X, y, columnas_disponibles

def preparar_datos(df, columnas_objetivo):
    """
    Prepara los datos para el entrenamiento del modelo.
    
    Args:
        df (pandas.DataFrame): DataFrame con los datos de GA4
        columnas_objetivo (list): Lista de columnas objetivo para el modelo
        
    Returns:
        tuple: (X, y) donde X son las características y y son las etiquetas
    """
    # Verificar que todas las columnas objetivo existan
    columnas_faltantes = [col for col in columnas_objetivo if col not in df.columns]
    if columnas_faltantes:
        raise ValueError(
            f"Las siguientes columnas no están disponibles en el CSV: {columnas_faltantes}. "
            f"Columnas disponibles: {df.columns.tolist()}"
        )
    
    # Crear el conjunto de características (X)
    X = df[columnas_objetivo].copy()
    
    # Normalizar los datos
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=X.columns)
    
    # Crear las etiquetas (y) - usamos engagement como métrica objetivo
    if 'engagementRate' in df.columns:
        y = df['engagementRate']
    else:
        # Si no hay tasa de engagement, usamos el promedio de las métricas disponibles
        y = X_scaled.mean(axis=1)
    
    return X_scaled, y

def entrenar_modelo(X, y):
    """
    Entrena un modelo de regresión usando los datos proporcionados.
    Versión optimizada para uso mínimo de memoria.
    """
    # Usar tipos de datos de menor precisión
    X = X.astype('float32')
    y = y.astype('float32')
    
    # Dividir los datos en conjuntos más pequeños
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Liberar memoria de los datos originales
    del X, y
    
    # Crear un modelo más ligero
    modelo = RandomForestRegressor(
        n_estimators=50,  # Reducido de 100 a 50
        max_depth=10,     # Limitar la profundidad
        min_samples_split=5,
        max_features='sqrt',  # Usar solo sqrt(n_features)
        n_jobs=-1,  # Usar todos los cores disponibles
        random_state=42
    )
    
    # Entrenar el modelo
    modelo.fit(X_train, y_train)
    
    # Evaluar
    y_pred = modelo.predict(X_test)
    metricas = {
        'r2': r2_score(y_test, y_pred),
        'mse': mean_squared_error(y_test, y_pred),
        'mae': mean_absolute_error(y_test, y_pred)
    }
    
    # Liberar memoria del conjunto de prueba
    del X_test, y_test, y_pred
    
    return modelo, metricas