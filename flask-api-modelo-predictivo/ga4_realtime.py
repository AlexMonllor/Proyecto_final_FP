#!/usr/bin/env python3
# ga4_realtime.py - Module for fetching real-time data from Google Analytics 4
import os
import pandas as pd
import numpy as np
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Metric,
    Dimension,
    DateRange,
)
from datetime import datetime, timedelta
import logging

# Configure GA4 credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "inprofit-ia-casa.json"
DEFAULT_PROPERTY_ID = "properties/271254856"  # Your GA4 property ID

def get_realtime_user_data(client_id, property_id=DEFAULT_PROPERTY_ID, minutes=30):
    """
    Fetches recent GA4 data for a specific client/user to make predictions.
    
    Args:
        client_id: The client ID from GA4 to identify the user
        property_id: Your GA4 property ID
        minutes: How far back to look for user data (default: 30 minutes)
        
    Returns:
        A pandas DataFrame with the user's metrics, ready for model prediction
    """
    try:
        # Initialize the GA4 client
        client = BetaAnalyticsDataClient()
        
        # Calculate the time range (last N minutes)
        end_date = datetime.now()
        start_date = end_date - timedelta(minutes)
        
        # Format dates for GA4 API
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # Create the request
        request = RunReportRequest(
            property=property_id,
            dimensions=[
                Dimension(name="sessionSourceMedium"),
                Dimension(name="deviceCategory"),
                Dimension(name="clientId"),  # Filter by this later
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="userEngagementDuration"),
                Metric(name="eventCount"),
                Metric(name="addToCarts"),
                Metric(name="checkouts"),
            ],
            date_ranges=[DateRange(start_date=start_date_str, end_date=end_date_str)],
        )
        
        # Run the report
        response = client.run_report(request)
        
        # Check if we received data
        if response.row_count == 0:
            logging.warning(f"No data found for client_id: {client_id}")
            return None
            
        # Extract data and create DataFrame
        rows = []
        dim_headers = [header.name for header in response.dimension_headers]
        metric_headers = [header.name for header in response.metric_headers]
        
        for row in response.rows:
            # Parse values into a dict
            row_data = {}
            for i, dim_value in enumerate(row.dimension_values):
                row_data[dim_headers[i]] = dim_value.value
            for i, metric_value in enumerate(row.metric_values):
                row_data[metric_headers[i]] = float(metric_value.value)
                
            # Only keep data for our target client_id
            if row_data.get('clientId') == client_id:
                rows.append(row_data)
                
        if not rows:
            logging.warning(f"No data found for specific client_id: {client_id}")
            return None
            
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Apply the same feature engineering as in training
        if 'sessions' in df.columns and df['sessions'].sum() > 0:
            df['pageviews_per_session'] = df['screenPageViews'] / df['sessions'].clip(lower=1)
            df['duration_per_session'] = df['userEngagementDuration'] / df['sessions'].clip(lower=1)
            df['events_per_session'] = df['eventCount'] / df['sessions'].clip(lower=1)
        
        if 'addToCarts' in df.columns and df['addToCarts'].sum() > 0:
            df['checkout_rate'] = df['checkouts'] / df['addToCarts'].clip(lower=1)
        else:
            df['checkout_rate'] = 0
            
        # Ensure we have all required features (with defaults if missing)
        for feature in ['pageviews_per_session', 'duration_per_session', 'events_per_session', 'checkout_rate']:
            if feature not in df.columns:
                df[feature] = 0
                
        # Handle one-hot encoding for categorical variables
        df_encoded = pd.get_dummies(df, columns=['sessionSourceMedium', 'deviceCategory'], prefix=['sessionSourceMedium', 'deviceCategory'])
        
        # Return the aggregated data (summing numeric values)
        return df_encoded.sum().to_frame().T  # Single row with summed metrics
        
    except Exception as e:
        logging.error(f"Error fetching GA4 data: {e}")
        return None

def preprocess_for_prediction(user_data, training_columns):
    """
    Prepare user data for prediction by aligning columns with the training data
    
    Args:
        user_data: DataFrame with user metrics
        training_columns: List of column names the model was trained with
        
    Returns:
        DataFrame ready for model prediction
    """
    if user_data is None:
        return None
    
    # Log información inicial sobre los datos
    logging.info(f"Input features shape: {user_data.shape}, columns disponibles: {user_data.columns}")
    
    # Nuestro modelo necesita exactamente 14 características
    EXPECTED_FEATURES = 14
    
    # Paso 1: Preparar todas las columnas posibles usando las columnas de entrenamiento
    X_all_columns = pd.DataFrame(index=user_data.index)
    for col in training_columns:
        if col in user_data.columns:
            X_all_columns[col] = user_data[col]
        else:
            X_all_columns[col] = 0
    
    # Definir las características más importantes basadas en conocimiento del dominio
    # Características numéricas prioritarias
    important_numerical = [
        'sessions',
        'screenPageViews',
        'userEngagementDuration',
        'eventCount',
        'addToCarts',
        'checkouts',
        'pageviews_per_session',
        'duration_per_session',
        'events_per_session',
        'checkout_rate'
    ]
    
    # Filtrar solo las que están en las columnas de entrenamiento
    important_numerical = [col for col in important_numerical if col in training_columns]
    
    # Categorías principales para sessionSourceMedium
    important_sources = [
        'sessionSourceMedium_google / organic',
        'sessionSourceMedium_direct / none',
        'sessionSourceMedium_admin / test'
    ]
    important_sources = [col for col in important_sources if col in training_columns]
    
    # Categorías principales para deviceCategory
    important_devices = [
        'deviceCategory_desktop',
        'deviceCategory_mobile'
    ]
    important_devices = [col for col in important_devices if col in training_columns]
    
    # Combinar todas las características importantes
    all_important = important_numerical + important_sources + important_devices
    
    # Seleccionar exactamente las 14 características más importantes
    # Si tenemos menos de 14, añadir del resto de columnas
    if len(all_important) < EXPECTED_FEATURES:
        remaining_cols = [col for col in training_columns if col not in all_important]
        all_important.extend(remaining_cols[:EXPECTED_FEATURES - len(all_important)])
    
    # Limitar a exactamente 14 características
    selected_features = all_important[:EXPECTED_FEATURES]
    
    # Asegurarnos de que todas estas características existen en el DataFrame
    for feature in selected_features:
        if feature not in X_all_columns:
            X_all_columns[feature] = 0
    
    # Crear el DataFrame final con exactamente 14 características
    X_processed = X_all_columns[selected_features]
    
    # Log para depuración
    logging.info(f"Datos preprocesados con {X_processed.shape[1]} características: {X_processed.columns.tolist()}")
    
    return X_processed

def get_user_metrics_from_website(user_data, training_columns=None):
    """
    Process user data coming directly from the website
    
    Args:
        user_data: Dictionary of metrics collected from the website
        training_columns: Optional list of column names the model was trained with
        
    Returns:
        DataFrame ready for feature engineering with limited features
    """
    # Log the incoming data for debugging
    logging.info(f"Website data received: {user_data}")
    
    # Convert to DataFrame
    df = pd.DataFrame([user_data])
    
    # ---- Create FIXED features instead of dynamic encoding ----
    # First extract the basic numeric features
    numeric_features = {
        'sessions': 1.0,
        'screenPageViews': float(user_data.get('screenPageViews', 0)),
        'userEngagementDuration': float(user_data.get('userEngagementDuration', 0)),
        'eventCount': float(user_data.get('eventCount', 0)),
        'addToCarts': float(user_data.get('addToCarts', 0)),
        'checkouts': float(user_data.get('checkouts', 0))
    }
    
    # Calculate derived features
    numeric_features['pageviews_per_session'] = numeric_features['screenPageViews'] / numeric_features['sessions']
    numeric_features['duration_per_session'] = numeric_features['userEngagementDuration'] / numeric_features['sessions']
    numeric_features['events_per_session'] = numeric_features['eventCount'] / numeric_features['sessions']
    
    if numeric_features['addToCarts'] > 0:
        numeric_features['checkout_rate'] = numeric_features['checkouts'] / numeric_features['addToCarts']
    else:
        numeric_features['checkout_rate'] = 0
    
    # Main categorical features we'll create (limited set to avoid explosion)
    source_medium = user_data.get('sessionSourceMedium', 'other / referral').lower()
    device = user_data.get('deviceCategory', 'desktop').lower()
    
    # Create fixed categorical columns for common sources/mediums
    categorical_features = {
        'sessionSourceMedium_google / organic': 1.0 if 'google' in source_medium and 'organic' in source_medium else 0.0,
        'sessionSourceMedium_direct / none': 1.0 if 'direct' in source_medium and 'none' in source_medium else 0.0,
        'sessionSourceMedium_facebook / referral': 1.0 if 'facebook' in source_medium else 0.0,
        'sessionSourceMedium_admin / test': 1.0 if 'admin' in source_medium and 'test' in source_medium else 0.0,
        'sessionSourceMedium_other / referral': 1.0 if not any(x in source_medium for x in ['google', 'direct', 'facebook', 'admin']) else 0.0,
        'deviceCategory_desktop': 1.0 if device == 'desktop' else 0.0,
        'deviceCategory_mobile': 1.0 if device == 'mobile' else 0.0,
        'deviceCategory_tablet': 1.0 if device == 'tablet' else 0.0
    }
    
    # Combine all features (both numeric and categorical)
    all_features = {**numeric_features, **categorical_features}
    
    # Create DataFrame with fixed set of features
    df_fixed = pd.DataFrame([all_features])
    
    # Log for debugging
    logging.info(f"Fixed features created: {len(df_fixed.columns)}, columns: {df_fixed.columns}")
    
    # If training columns are provided, use preprocess_for_prediction to ensure
    # we return exactly the right number of features
    if training_columns is not None:
        df_processed = preprocess_for_prediction(df_fixed, training_columns)
        logging.info(f"Features after preprocessing: {len(df_processed.columns)}, columns: {df_processed.columns}")
        return df_processed
    
    return df_fixed
