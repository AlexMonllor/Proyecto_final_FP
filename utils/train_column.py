import pandas as pd
import os
import json

def seleccionar_columnas_entrenamiento(df, columnas_objetivo, args):
    """
    Selecciona y procesa las columnas de entrenamiento para el modelo de forma dinámica.
    Realiza ingeniería de características y codificación de variables categóricas.
    Devuelve X (features), y (objetivo), columnas_objetivo.
    El parámetro args debe contener el atributo 'salida' con el directorio de resultados.
    """
    # Detectar columnas numéricas y categóricas dinámicamente
    columnas_objetivo = columnas_objetivo or []
    columnas_numericas = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col]) and col not in columnas_objetivo]
    columnas_categoricas = [col for col in df.columns if (df[col].dtype == 'object' or df[col].dtype.name == 'category') and col not in columnas_objetivo]

    # Ingeniería de características flexible: ratios entre columnas numéricas (evitar divisiones triviales)
    nuevas_features = []
    for i, col1 in enumerate(columnas_numericas):
        for j, col2 in enumerate(columnas_numericas):
            if i != j and not df[col2].eq(0).all():
                nombre_feature = f"{col1}_per_{col2}"
                # Evitar crear features redundantes si ya existen
                if nombre_feature not in df.columns:
                    df[nombre_feature] = df[col1] / df[col2].replace(0, pd.NA)
                    nuevas_features.append(nombre_feature)
    # Eliminar features con demasiados nulos (más del 80%)
    for feature in nuevas_features:
        if df[feature].isnull().mean() > 0.8:
            df.drop(columns=[feature], inplace=True)
    # Actualizar columnas numéricas con las nuevas features válidas
    columnas_numericas = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col]) and col not in columnas_objetivo]

    X_num = df[columnas_numericas]
    X_cat = pd.get_dummies(df[columnas_categoricas], prefix=columnas_categoricas, dummy_na=False)
    X = pd.concat([X_num, X_cat], axis=1)

    # Si no se especifica objetivo, usar 'ecommercePurchases' > 0 como binario si existe
    if not columnas_objetivo:
        if 'ecommercePurchases' in df.columns:
            y = (df['ecommercePurchases'] > 0).astype(int)
            columnas_objetivo = ['purchased']
        else:
            y = None
            columnas_objetivo = []
    else:
        y = df[columnas_objetivo]

    # Guardar columnas procesadas y objetivo en JSON en la misma ruta que los resultados
    if args and hasattr(args, 'salida') and args.salida:
        salida_dir = args.salida
        if not os.path.exists(salida_dir):
            os.makedirs(salida_dir)
        columnas_info = {
            "columnas_objetivo": columnas_objetivo
        }
        with open(os.path.join(salida_dir, "training_columns.json"), "w", encoding="utf-8") as f:
            json.dump(columnas_info, f, ensure_ascii=False, indent=2)

    return X, y, columnas_objetivo