import matplotlib
matplotlib.use('Agg')  # Configurar backend no interactivo
import os
import numpy as np
import pandas as pd
import json
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score
from utils.evaluacion import generar_informe, evaluar_modelo
import logging

def imputar_valores_faltantes(X):
    """Imputa valores faltantes en X"""
    if isinstance(X, np.ndarray):
        imputer = SimpleImputer(strategy='mean')
        return imputer.fit_transform(X)
    return X

def crear_pipeline_incremental():
    """Crea un pipeline optimizado para entrenamiento incremental"""
    base_model = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        min_samples_split=5,
        min_samples_leaf=3,
        subsample=0.8,
        random_state=42
    )
    
    return Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', MultiOutputRegressor(base_model, n_jobs=-1))
    ])

def entrenar_por_lotes(modelo, X, y, batch_size, n_epochs, directorio_salida):
    """Entrena el modelo de forma incremental usando mini-lotes
    
    Args:
        modelo: Pipeline de sklearn o None
        X: Features de entrenamiento
        y: Variables objetivo
        batch_size: Tamaño de los lotes para entrenamiento
        n_epochs: Número de épocas de entrenamiento
        directorio_salida: Directorio donde se guardarán los resultados
    """
    # Configurar logging en lugar de print para mensajes
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info(f"\nEntrenamiento incremental con {n_epochs} épocas y lotes de {batch_size}")
    
    # Convertir entradas a numpy arrays
    X = X.values if isinstance(X, pd.DataFrame) else X
    y = y.values if isinstance(y, pd.DataFrame) else y
    
    # Crear modelo si no existe
    if modelo is None:
        modelo = crear_pipeline_incremental()
        
    logger.info(f"Dimensiones de entrada - X: {X.shape}, y: {y.shape}")
    
    # Ajuste inicial del modelo
    initial_size = min(batch_size * 10, X.shape[0])
    indices_iniciales = np.random.choice(X.shape[0], initial_size, replace=False)
    modelo.fit(X[indices_iniciales], y[indices_iniciales])
    
    # Variables para el entrenamiento
    n_samples = X.shape[0]
    indices = np.arange(n_samples)
    mejor_score = -np.inf
    mejor_modelo = None
    n_eval = min(1000, X.shape[0])  # Tamaño del conjunto de evaluación
    indices_eval = np.random.choice(X.shape[0], n_eval, replace=False)
    X_eval = X[indices_eval]
    y_eval = y[indices_eval]
    
    # Entrenamiento por épocas
    for epoch in range(n_epochs):
        logger.info(f"\nÉpoca {epoch + 1}/{n_epochs}")
        np.random.shuffle(indices)
        
        for start_idx in range(0, n_samples, batch_size):
            end_idx = min(start_idx + batch_size, n_samples)
            batch_indices = indices[start_idx:end_idx]
            
            X_batch = X[batch_indices]
            y_batch = y[batch_indices]
            
            try:
                # Transformar y entrenar
                modelo.fit(X_batch, y_batch)
                
                # Evaluar en conjunto de evaluación fijo
                score = r2_score(y_eval, modelo.predict(X_eval))
                
                if score > mejor_score:
                    mejor_score = score
                    mejor_modelo = clone(modelo)
                    mejor_modelo.fit(X_batch, y_batch)
                
                if (start_idx + batch_size) % (batch_size * 10) == 0:
                    logger.info(f"Procesado hasta muestra {end_idx}/{n_samples} - R² en eval: {score:.4f}")
            except Exception as e:
                logger.info(f"\n❌ Error en batch {start_idx}-{end_idx}: {str(e)}")
                continue
    
    logger.info(f"\nMejor R² conseguido en evaluación: {mejor_score:.4f}")
    
    # Evaluar y generar informes usando el mismo conjunto de evaluación
    try:
        logger.info("\nGenerando informes de evaluación...")
        modelo_final = mejor_modelo if mejor_modelo is not None else modelo
        
        # Evaluar modelo y guardar resultados
        resultados = evaluar_modelo(modelo_final, X_eval, y_eval)
        resultados_json = os.path.join(directorio_salida, 'resultados_modelo_incremental.json')
        with open(resultados_json, 'w') as f:
            json.dump(resultados, f, indent=2)
        
        # Generar informe visual
        generar_informe(modelo_final, X_eval, y_eval, directorio_salida=directorio_salida)
        
    except Exception as e:
        logger.error(f"Error al generar informes: {str(e)}")
    
    return mejor_modelo if mejor_modelo is not None else modelo