#!/usr/bin/env python3
import warnings
import matplotlib
matplotlib.use('Agg')
import argparse
import os
import numpy as np
import pandas as pd
import joblib
import json
from sklearn.model_selection import train_test_split
from utils.datos import cargar_multiples_archivos
from utils.evaluacion import evaluar_modelo, generar_informe
from utils.incremental import imputar_valores_faltantes, entrenar_por_lotes
from utils.pipelines import crear_pipeline_multioutput
from utils.train_column import seleccionar_columnas_entrenamiento

warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', message='.*main thread.*')
warnings.filterwarnings('ignore', message='.*main loop.*')

def main():
    """
    Función principal que orquesta el proceso de entrenamiento del modelo predictivo.
    - Lee argumentos de línea de comandos.
    - Carga y prepara los datos.
    - Realiza la selección de columnas y filtrado de valores faltantes.
    - Divide los datos en conjuntos de entrenamiento y validación.
    - Entrena el modelo (de forma incremental o tradicional).
    - Evalúa el modelo y guarda los resultados y el modelo entrenado.
    """
    parser = argparse.ArgumentParser(description='Entrenar modelo predictivo con datos históricos')
    parser.add_argument('--archivos', nargs='+', help='Lista de archivos CSV con datos históricos', required=False)
    parser.add_argument('--objetivos', nargs='+', help='Lista de columnas objetivo (para múltiples objetivos)')
    parser.add_argument('--modelo-salida', default='modelo_ga.joblib', help='Ruta para guardar el modelo entrenado')
    parser.add_argument('--salida', default='resultados', help='Directorio para guardar resultados')
    parser.add_argument('--incremental', action='store_true', help='Entrenar el modelo de manera incremental')
    parser.add_argument('--batch-size', type=int, default=1000, help='Tamaño del lote para entrenamiento incremental')
    parser.add_argument('--epochs', type=int, default=10, help='Número de épocas para entrenamiento incremental')
    args = parser.parse_args()

    if not args.archivos:
        parser.error("Debe proporcionar --archivos")
    if not os.path.exists(args.salida):
        os.makedirs(args.salida)

    # Definir la ruta completa para guardar el modelo dentro del directorio de salida
    ruta_modelo = os.path.join(args.salida, os.path.basename(args.modelo_salida))

    # Carga múltiples archivos CSV y los concatena en un solo DataFrame
    datos = cargar_multiples_archivos(args.archivos)
    columnas_objetivo = args.objetivos

    # Selecciona las columnas de entrada y salida para el entrenamiento
    X, y, columnas_procesadas = seleccionar_columnas_entrenamiento(
        datos, columnas_objetivo, args
    )

    print("\nVerificando valores faltantes en los objetivos (y)...")
    if np.any(pd.isnull(y)):
        print(f"⚠️ Se encontraron valores faltantes en los objetivos. Filtrando filas...")
        mask = ~np.isnan(y).any(axis=1)
        X = X[mask]
        y = y[mask]
        print(f"Dimensiones después de filtrar: X: {X.shape}, y: {y.shape}")

    # Divide los datos en conjuntos de entrenamiento y validación
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
    X_val, _, y_val, _ = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    print(f"\nConjunto de entrenamiento: {X_train.shape[0]} muestras")
    print(f"Conjunto de validación: {X_val.shape[0]} muestras")

    if args.incremental:
        print("\nEntrenando modelo de manera incremental...")
        if os.path.exists(ruta_modelo):
            print(f"\nCargando modelo existente desde {ruta_modelo}...")
            modelo_dict = joblib.load(ruta_modelo)
            modelo = modelo_dict['modelo']
            
            # Verifica si el modelo existente es compatible con los nuevos objetivos
            if hasattr(modelo, 'n_outputs_') and modelo.n_outputs_ != y.shape[1]:
                print(f"\n❌ Error: El modelo existente fue entrenado para predecir {modelo.n_outputs_} objetivos, "
                      f"pero los datos actuales tienen {y.shape[1]} objetivos.")
                print("Re-entrenando modelo desde cero con los nuevos objetivos...")
                modelo = crear_pipeline_multioutput()
            
            columnas_modelo = modelo_dict.get('columnas', None)
            if columnas_modelo and set(columnas_modelo) != set(columnas_procesadas):
                print("⚠️ Advertencia: Las características del modelo no coinciden con los datos actuales")
                print(f"Características faltantes: {set(columnas_modelo) - set(columnas_procesadas)}")
                print(f"Características nuevas: {set(columnas_procesadas) - set(columnas_modelo)}")
                X = X[columnas_modelo]  # Usar solo las columnas del modelo original
        else:
            # Crea un nuevo pipeline para entrenamiento incremental
            modelo = crear_pipeline_multioutput()
        # Imputa valores faltantes en X antes de entrenar
        X = imputar_valores_faltantes(X)
        # Entrena el modelo por lotes (incremental)
        modelo = entrenar_por_lotes(modelo, X, y, 
                                    batch_size=args.batch_size, 
                                    n_epochs=args.epochs,
                                    directorio_salida=args.salida)
        print(f"\nGuardando modelo incremental en {ruta_modelo}...")
        joblib.dump({'modelo': modelo, 'columnas': columnas_procesadas}, ruta_modelo)
    else:
        if os.path.exists(ruta_modelo):
            print(f"\nCargando modelo existente desde {ruta_modelo}...")
            modelo_dict = joblib.load(ruta_modelo)
            columnas_modelo = modelo_dict.get('columnas', None)
            
            if columnas_modelo and set(columnas_modelo) != set(columnas_procesadas):
                print("\n⚠️ Detectado cambio en las características del modelo:")
                print(f"- Características anteriores: {len(columnas_modelo)}")
                print(f"- Características actuales: {len(columnas_procesadas)}")
                print("\n🔄 Re-entrenando modelo con las nuevas características...")
                
                modelo = crear_pipeline_multioutput()
            else:
                modelo = modelo_dict['modelo']
        else:
            print("\nCreando nuevo modelo GradientBoostingRegressor...")
            modelo = crear_pipeline_multioutput()
        
        print("\nEntrenando modelo...")
        # Entrena el modelo con el conjunto de entrenamiento
        modelo.fit(X_train, y_train)
        
        print("\nEvaluando modelo...")
        # Verifica compatibilidad de dimensiones entre modelo y datos de validación
        if hasattr(modelo, 'n_outputs_') and modelo.n_outputs_ != y_val.shape[1]:
            print(f"\n❌ Error: El modelo fue entrenado para predecir {modelo.n_outputs_} objetivos, "
                  f"pero los datos actuales tienen {y_val.shape[1]} objetivos.")
            print("Es necesario re-entrenar el modelo desde cero con los nuevos objetivos.")
            return
            
        # Evalúa el modelo y genera informe
        resultados = evaluar_modelo(modelo, X_train, y_train, X_val, y_val)
        generar_informe(modelo, X_val, y_val, directorio_salida=args.salida)
        
        print(f"\nGuardando modelo en {ruta_modelo}...")
        joblib.dump({'modelo': modelo, 'columnas': columnas_procesadas}, ruta_modelo)
        
        resultados_json = os.path.join(args.salida, 'resultados_modelo.json')
        with open(resultados_json, 'w') as f:
            json.dump(resultados, f, indent=2)
        print("¡Entrenamiento finalizado con éxito!")

if __name__ == "__main__":
    # Punto de entrada del script
    main()