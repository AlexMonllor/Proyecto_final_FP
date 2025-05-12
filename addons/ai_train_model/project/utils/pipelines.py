from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.multioutput import MultiOutputRegressor

def crear_pipeline_multioutput():
    """Crea un pipeline de preprocesamiento y modelo para múltiples objetivos"""
    base_model = GradientBoostingRegressor(
        n_estimators=300,    # Aumentado de 200 a 300
        learning_rate=0.05,  # Reducido de 0.1 a 0.05 para mejor generalización
        max_depth=4,         # Reducido de 5 a 4 para evitar sobreajuste
        min_samples_split=5, # Aumentado de 3 a 5
        min_samples_leaf=3,  # Aumentado de 2 a 3
        subsample=0.8,       # Nuevo: usar 80% de las muestras en cada árbol
        random_state=42
    )
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
        ('model', MultiOutputRegressor(base_model, n_jobs=-1))  # Habilitar paralelismo
    ])
    return pipeline
