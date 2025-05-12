import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, KFold
import numpy as np
import pandas as pd

def evaluar_modelo(modelo, X, y, X_val=None, y_val=None, cv=5):
    """
    Evalúa el modelo usando validación cruzada y/o conjunto de validación.
    - Realiza validación cruzada con KFold y calcula métricas R2, MSE y RMSE.
    - Si se proporciona un conjunto de validación, calcula métricas sobre ese conjunto.
    - Devuelve un diccionario con los resultados.
    """
    print("\n=== Evaluación del modelo ===")
    resultados = {}
    print("\nUsando KFold para validación cruzada...")
    try:
        kf = KFold(n_splits=cv, shuffle=True, random_state=42)
        cv_scores = cross_val_score(modelo, X, y, cv=kf, scoring='r2', n_jobs=-1)
        mse_scores = -cross_val_score(modelo, X, y, cv=kf, scoring='neg_mean_squared_error', n_jobs=-1)
        rmse_scores = np.sqrt(mse_scores)
        print(f"R² promedio (CV): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        print(f"RMSE promedio (CV): {rmse_scores.mean():.4f} ± {rmse_scores.std():.4f}")
        print(f"MSE promedio (CV): {mse_scores.mean():.4f} ± {mse_scores.std():.4f}")
        resultados['cv'] = {
            'r2_mean': cv_scores.mean(),
            'r2_std': cv_scores.std(),
            'rmse_mean': rmse_scores.mean(),
            'rmse_std': rmse_scores.std(),
            'mse_mean': mse_scores.mean(),
            'mse_std': mse_scores.std()
        }
    except Exception as e:
        print(f"❌ Error durante la validación cruzada: {e}")
        resultados['cv'] = {
            'r2_mean': None,
            'r2_std': None,
            'rmse_mean': None,
            'rmse_std': None,
            'mse_mean': None,
            'mse_std': None,
            'error': str(e)
        }
    if X_val is not None and y_val is not None:
        print("\nResultados en conjunto de validación:")
        try:
            y_pred = modelo.predict(X_val)
            val_mse = mean_squared_error(y_val, y_pred)
            val_rmse = np.sqrt(val_mse)
            val_r2 = r2_score(y_val, y_pred)
            print(f"R²: {val_r2:.4f}")
            print(f"RMSE: {val_rmse:.4f}")
            print(f"MSE: {val_mse:.4f}")
            resultados['validation'] = {
                'r2': val_r2,
                'rmse': val_rmse,
                'mse': val_mse
            }
        except ValueError as e:
            print(f"❌ Error durante la validación en conjunto separado: {e}")
            resultados['validation'] = {
                'r2': None,
                'rmse': None,
                'mse': None
            }
    return resultados

def generar_informe(modelo, X_val, y_val, directorio_salida='resultados'):
    """
    Genera un informe en formato HTML con gráficos de validación y verificación del modelo.
    - Ajusta el pipeline si es necesario.
    - Genera gráfico de valores reales vs predicciones y distribución de residuos.
    - Calcula y grafica la matriz de correlación entre valores reales y predichos.
    - Crea un informe HTML con los gráficos generados.
    """
    try:
        # Verificar si el pipeline está ajustado
        if not hasattr(modelo, 'named_steps') or not hasattr(modelo.named_steps['imputer'], 'statistics_'):
            print("⚠️ Pipeline no ajustado, reajustando...")
            modelo.fit(X_val, y_val)
        
        # Realizar predicciones
        print("Generando predicciones...")
        y_pred = modelo.predict(X_val)

        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
        
        # Corregir las rutas para usar el directorio de salida
        grafico_valores_reales_path = os.path.join(directorio_salida, 'grafico_valores_reales_vs_predicciones.png')
        html_path = os.path.join(directorio_salida, 'informe_modelo.html')
        
        print("\nGenerando gráfico de valores reales vs. predicciones...")
        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.scatter(y_val, y_pred, alpha=0.6, color='blue')
        plt.plot([y_val.min(), y_val.max()], [y_val.min(), y_val.max()], 'r--', lw=2)
        plt.xlabel('Valores reales')
        plt.ylabel('Predicciones')
        plt.title('Valores reales vs. predicciones')
        residuos = y_val - y_pred
        plt.subplot(1, 2, 2)
        sns.histplot(residuos, kde=True, color='blue', bins=30)
        plt.axvline(0, color='red', linestyle='--', lw=2)
        plt.xlabel('Residuos')
        plt.ylabel('Frecuencia')
        plt.title('Distribución de residuos')
        plt.tight_layout()
        plt.savefig(grafico_valores_reales_path)
        plt.close()

        # Determinar nombres de columnas
        if hasattr(y_val, 'columns'):
            y_val_cols = list(y_val.columns)
        else:
            y_val_cols = [f"real_{i+1}" for i in range(y_val.shape[1] if len(y_val.shape) > 1 else 1)]
        if hasattr(y_pred, 'columns'):
            y_pred_cols = list(y_pred.columns)
        else:
            y_pred_cols = [f"pred_{col}" for col in y_val_cols]

        # Convertir a DataFrame para correlación
        df_real_pred = pd.DataFrame(
            np.column_stack([np.array(y_val), np.array(y_pred)]),
            columns=y_val_cols + y_pred_cols
        )
        corr_matrix = df_real_pred.corr(method='pearson')

        # Graficar heatmap de la matriz de correlación (sin guardar CSV)
        heatmap_path = os.path.join(directorio_salida, 'matriz_correlacion.png')
        plt.figure(figsize=(8, 6))
        sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm')
        plt.title('Matriz de correlación (valores reales vs predicciones)')
        plt.tight_layout()
        plt.savefig(heatmap_path)
        plt.close()

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Informe del Modelo Predictivo</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    line-height: 1.6;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Informe del Modelo Predictivo</h1>
                <h2>Gráfico de Valores Reales vs. Predicciones</h2>
                <img src="grafico_valores_reales_vs_predicciones.png" alt="Gráfico de Valores Reales vs. Predicciones">
                <h2>Matriz de correlación (valores reales vs predicciones)</h2>
                <img src="matriz_correlacion.png" alt="Matriz de correlación">
            </div>
        </body>
        </html>
        """
        with open(html_path, 'w') as f:
            f.write(html_content)
        print(f"\nInforme generado: {html_path}")
    except Exception as e:
        print(f"❌ Error durante la generación del informe: {str(e)}")
        raise