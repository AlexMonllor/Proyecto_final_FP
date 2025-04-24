#!/usr/bin/env python3
# prediction_api.py - API for real-time purchase prediction
import os
import joblib
import logging
import pandas as pd
from flask import Flask, request, jsonify, make_response
from flask_restful import Api, Resource
from datetime import datetime
from flask_cors import CORS, cross_origin

# Import GA4 real-time data functions
from ga4_realtime import (
    get_realtime_user_data,
    preprocess_for_prediction,
    get_user_metrics_from_website
)

# Configure logging - enhanced version
logging.basicConfig(
    level=logging.DEBUG,  # Cambiar a DEBUG para más detalles
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('prediction_api.log')
    ]
)
# Configuración detallada para CORS y Flask
logging.getLogger('flask_cors').level = logging.DEBUG
logging.getLogger('flask').level = logging.DEBUG
logging.getLogger('werkzeug').level = logging.DEBUG

# Log inicial para verificar que el registro está funcionando
logging.info("=====================================")
logging.info("API de Predicción iniciada")
logging.info("=====================================")

# --- Configuration ---
MODEL_PATH = "purchase_predictor_model_ensemble_20250414_181759.joblib"
COLUMNS_PATH = "training_columns.joblib"
OPTIMAL_THRESHOLD = 0.70  # The optimized threshold found during model training
# --- End Configuration ---

# Initialize Flask app
app = Flask(__name__)

# Configuración CORS más permisiva para desarrollo
cors = CORS(app,
            resources={r"/predict/*": {
                "origins": "*",
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
                "expose_headers": ["Content-Type", "X-Total-Count"],
                "supports_credentials": True,
                "max_age": 600
            }},
            allow_headers=["Content-Type", "X-Requested-With", "Origin", "Accept"],
            expose_headers=["Content-Length", "X-Json"],
            allow_methods=["GET", "POST", "OPTIONS"])

# Middleware para añadir encabezados CORS a todas las respuestas
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Origin, Accept'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

# Manejar explícitamente las solicitudes OPTIONS
@app.route('/predict/website', methods=['OPTIONS'])
def handle_options_website():
    response = app.make_default_options_response()
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Origin, Accept'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

api = Api(app)

# Load model and training columns
model = None
training_columns = None

def load_model():
    """Load the trained model and columns"""
    global model, training_columns
    try:
        model = joblib.load(MODEL_PATH)
        training_columns = joblib.load(COLUMNS_PATH)
        logging.info(f"Model loaded successfully from {MODEL_PATH}")
        return True
    except Exception as e:
        logging.error(f"Error loading model: {e}")
        return False

class HealthCheck(Resource):
    """API endpoint to check if the service is running"""
    def get(self):
        return {"status": "ok", "model_loaded": model is not None}

class PredictFromGA4(Resource):
    """API endpoint to predict purchase likelihood using GA4 data"""
    def post(self):
        if not model or not training_columns:
            return {"error": "Model not loaded"}, 500
            
        # Get client_id from request
        try:
            data = request.get_json(force=True)
            client_id = data.get("client_id")
            minutes = data.get("minutes", 30)  # How far back to look
            
            if not client_id:
                return {"error": "client_id is required"}, 400
        except Exception as e:
            logging.error(f"Error parsing request: {e}")
            return {"error": "Invalid request format"}, 400
            
        # Get user data from GA4
        user_data = get_realtime_user_data(client_id, minutes=minutes)
        if user_data is None:
            return {"error": "No data found for this user"}, 404
            
        # Prepare data for prediction
        X = preprocess_for_prediction(user_data, training_columns)
        if X is None:
            return {"error": "Error preparing data for prediction"}, 500
            
        # Make prediction
        try:
            # Get probability
            purchase_prob = model.predict_proba(X)[0, 1]
            
            # Apply optimal threshold
            purchase_likely = purchase_prob >= OPTIMAL_THRESHOLD
            
            # Round probability for cleaner output
            purchase_prob = round(float(purchase_prob), 4)
            
            # Prepare response
            result = {
                "client_id": client_id,
                "purchase_probability": purchase_prob,
                "purchase_likely": bool(purchase_likely),
                "threshold_used": OPTIMAL_THRESHOLD,
                "timestamp": datetime.now().isoformat(),
                "features_used": len(training_columns)
            }
            
            # Log prediction
            logging.info(f"Prediction for {client_id}: prob={purchase_prob}, likely={purchase_likely}")
            
            return result, 200
            
        except Exception as e:
            logging.error(f"Error making prediction: {e}")
            return {"error": f"Prediction error: {str(e)}"}, 500

class PredictFromWebsite(Resource):
    """API endpoint to predict purchase likelihood using data sent directly from website"""
    def post(self):
        # Log origin for debugging
        origin = request.headers.get('Origin', 'No Origin header')
        logging.info(f"Received request from: {origin}")
        logging.info(f"Headers: {request.headers}")
        
        if not model or not training_columns:
            response = jsonify({"status": "error", "error": "Model not loaded"})
            return response, 500
            
        # Get user data from request
        try:
            # Log the raw request data for debugging
            raw_data = request.get_data()
            logging.info(f"Request data: {raw_data}")
            
            user_data = request.get_json(force=True)
            logging.info(f"Processed user data: {user_data}")
            user_id = user_data.get("user_id", "unknown")
            
            # Remove the user_id from metrics
            if "user_id" in user_data:
                user_data_copy = user_data.copy()
                del user_data_copy["user_id"]
            else:
                user_data_copy = user_data
                
            # Check if we have the minimum required data
            required_fields = ["sessionSourceMedium", "deviceCategory"]
            for field in required_fields:
                if field not in user_data_copy:
                    response = jsonify({"status": "error", "error": f"Missing required field: {field}"})
                    return response, 400
                    
            # Ensure numeric fields are float
            numeric_fields = ["sessions", "screenPageViews", "userEngagementDuration", 
                             "eventCount", "addToCarts", "checkouts"]
            for field in numeric_fields:
                if field in user_data_copy:
                    user_data_copy[field] = float(user_data_copy[field])
                else:
                    user_data_copy[field] = 0.0
                    
        except Exception as e:
            logging.error(f"Error parsing website data: {e}")
            response = jsonify({"status": "error", "error": f"Invalid data format: {str(e)}"})
            return response, 400
            
        # Process website data
        try:
            # Pass training_columns directly to get_user_metrics_from_website
            # This will ensure we get exactly the right number of features
            X = get_user_metrics_from_website(user_data_copy, training_columns)
            if X is None:
                response = jsonify({"status": "error", "error": "Error preparing data for prediction"})
                return response, 500
        except Exception as e:
            logging.error(f"Error in processing: {e}")
            response = jsonify({"status": "error", "error": f"Processing error: {str(e)}"})
            return response, 500
            
        # Make prediction
        try:
            # Get probability
            purchase_prob = model.predict_proba(X)[0, 1]
            
            # Apply optimal threshold
            purchase_likely = purchase_prob >= OPTIMAL_THRESHOLD
            
            # Round probability for cleaner output
            purchase_prob = round(float(purchase_prob), 4)
            
            # Prepare response
            result = {
                "status": "success",
                "user_id": user_id,
                "purchase_probability": purchase_prob,
                "purchase_likely": bool(purchase_likely),
                "threshold_used": OPTIMAL_THRESHOLD,
                "timestamp": datetime.now().isoformat()
            }
            
            # Log prediction
            logging.info(f"Website prediction for {user_id}: prob={purchase_prob}, likely={purchase_likely}")
            
            # Return the dictionary directly for Flask-RESTful to handle
            return result, 200
            
        except Exception as e:
            logging.error(f"Error in prediction: {e}")
            response = jsonify({"status": "error", "error": f"Prediction error: {str(e)}"})
            return response, 500

# Register API resources
api.add_resource(HealthCheck, '/health')
api.add_resource(PredictFromGA4, '/predict/ga4')
api.add_resource(PredictFromWebsite, '/predict/website')

# Add a basic welcome page
@app.route('/')
@cross_origin()
def index():
    return """
    <html>
        <head><title>Purchase Prediction API</title></head>
        <body>
            <h1>Purchase Prediction API</h1>
            <p>API endpoints:</p>
            <ul>
                <li><a href="/health">/health</a> - Check API status</li>
                <li>/predict/ga4 - Get predictions using GA4 data</li>
                <li>/predict/website - Get predictions using website data</li>
            </ul>
        </body>
    </html>
    """

if __name__ == "__main__":
    # Load model before starting the server
    if load_model():
        # Run the API server locally for testing
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        logging.error("Failed to load model. API not started.")
else:
    # Para cuando se ejecuta a través de passenger_wsgi.py en Hostinger
    load_model()
