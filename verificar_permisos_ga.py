#!/usr/bin/env python3
"""
Script para verificar los permisos y acceso a Google Analytics 4 (GA4)
"""
import os
import argparse
import json
import sys
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
# Importaciones corregidas para Google Analytics Admin
from google.analytics.admin import AnalyticsAdminServiceClient
# No necesitamos importar ListAccountsRequest directamente

from google.oauth2 import service_account

def verificar_credenciales(archivo_clave):
    """
    Verifica que las credenciales sean válidas y muestra información sobre ellas.
    - Comprueba que el archivo existe y es un JSON válido.
    - Intenta cargar las credenciales y autenticar con Google.
    - Devuelve el objeto de credenciales si es exitoso, None si falla.
    """
    print(f"\n=== Verificando archivo de credenciales: {archivo_clave} ===")
    
    # Verificar que existe el archivo
    if not os.path.exists(archivo_clave):
        print(f"ERROR: El archivo de credenciales no existe: {archivo_clave}")
        return None
        
    # Cargar el archivo de credenciales para mostrar información
    try:
        with open(archivo_clave, 'r') as f:
            datos_clave = json.load(f)
            
        print(f"Tipo de cuenta: {datos_clave.get('type')}")
        print(f"Proyecto ID: {datos_clave.get('project_id')}")
        print(f"Cliente email: {datos_clave.get('client_email')}")
        print(f"Cliente ID: {datos_clave.get('client_id')}")
        
        # Intentar autenticar
        print("\nIntentando autenticar con Google...")
        try:
            credentials = service_account.Credentials.from_service_account_file(
                archivo_clave,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )
            print("✓ Credenciales cargadas correctamente")
            return credentials
        except Exception as e:
            print(f"ERROR al cargar credenciales: {str(e)}")
            return None
            
    except json.JSONDecodeError:
        print("ERROR: El archivo de credenciales no es un JSON válido")
        return None
    except Exception as e:
        print(f"ERROR al leer el archivo de credenciales: {str(e)}")
        return None

def verificar_acceso_api(credenciales):
    """
    Verifica el acceso a la API de Google Analytics 4.
    - Intenta crear los clientes de Analytics Data API y Admin API.
    - Devuelve ambos clientes si tiene éxito, None si falla.
    """
    if not credenciales:
        return None, None
        
    print("\n=== Verificando acceso a la API de Analytics ===")
    try:
        # Construir el cliente de Analytics Data API (para consultas de datos)
        analytics_data_client = BetaAnalyticsDataClient(credentials=credenciales)
        
        # Construir el cliente de Analytics Admin API (para listar propiedades)
        analytics_admin_client = AnalyticsAdminServiceClient(credentials=credenciales)
        
        print("✓ Conexión a las APIs establecida correctamente")
        return analytics_data_client, analytics_admin_client
    except Exception as e:
        print(f"ERROR al conectar con la API: {str(e)}")
        return None, None

def listar_cuentas_disponibles(analytics_admin_client):
    """
    Lista todas las cuentas y propiedades GA4 a las que tiene acceso la cuenta de servicio.
    - Muestra las cuentas y propiedades encontradas.
    - Da instrucciones si no se encuentran cuentas o propiedades.
    """
    if not analytics_admin_client:
        return
        
    print("\n=== Verificando acceso a cuentas de GA4 ===")
    try:
        # Obtener la lista de cuentas (sin necesidad de crear un objeto request)
        accounts_response = analytics_admin_client.list_accounts()
        
        accounts = list(accounts_response)
        
        if not accounts:
            print("No se encontraron cuentas. La cuenta de servicio no tiene permisos para ver ninguna cuenta.")
            print("\nSOLUCIÓN: En Google Analytics, añade la cuenta de servicio como usuario con permisos de Lectura y Análisis")
            print("1. Ve a Administración > Acceso > Administración de acceso")
            print("2. Añade el email de la cuenta de servicio")
            print("3. Asigna permisos de Lector como mínimo")
            return
            
        print(f"✓ La cuenta de servicio tiene acceso a {len(accounts)} cuentas de GA4")
        
        print("\n=== CUENTAS Y PROPIEDADES DE GA4 DISPONIBLES ===")
        print("NOTA: Para descargar datos necesitas un ID de PROPIEDAD de GA4")
        
        found_properties = False
        
        for account in accounts:
            account_name = account.display_name
            account_path = account.name  # Formato: "accounts/XXXX"
            account_id = account_path.split('/')[-1]
            
            print(f"\nCUENTA: {account_name} (ID: {account_id})")
            
            try:
                # Listar propiedades para esta cuenta
                properties_response = analytics_admin_client.list_properties(parent=account_path)
                properties = list(properties_response)
                
                if not properties:
                    print("  No se encontraron propiedades GA4")
                    continue
                    
                found_properties = True
                for property in properties:
                    property_name = property.display_name
                    property_path = property.name  # Formato: "properties/XXXX"
                    property_id = property_path.split('/')[-1]
                    
                    print(f"  PROPIEDAD: {property_name} (ID: {property_id}) ★ USAR ESTE ID PARA DESCARGAR DATOS ★")
                    print(f"             URL completa: {property_path}")
                
            except Exception as e:
                print(f"  Error al obtener propiedades: {str(e)}")
                
        if not found_properties:
            print("\n⚠️ ADVERTENCIA: No se encontraron propiedades de GA4.")
            print("Sin propiedades configuradas no podrás descargar datos.")
            print("Asegúrate de que tienes propiedades configuradas en tu cuenta de Google Analytics 4")
            print("y que la cuenta de servicio tiene permisos para acceder a ellas.")
                
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("\nEs posible que necesites habilitar la API de Google Analytics Admin en la consola de Google Cloud.")
        print("1. Ve a https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com")
        print("2. Selecciona tu proyecto")
        print("3. Habilita la API")

def verificar_propiedad_especifica(analytics_data_client, property_id):
    """
    Verifica el acceso a una propiedad específica de GA4.
    - Intenta hacer una consulta mínima para comprobar el acceso.
    - Muestra una vista previa de los datos si tiene éxito.
    - Devuelve True si el acceso es correcto, False si falla.
    """
    if not analytics_data_client:
        return
        
    # Asegurarse de que el property_id tiene el formato correcto
    if not property_id.startswith("properties/"):
        property_id = f"properties/{property_id}"
            
    print(f"\n=== Verificando acceso a la propiedad (ID: {property_id}) ===")
    try:
        # Intentamos hacer una consulta mínima para verificar el acceso
        request = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
            metrics=[Metric(name="activeUsers")],
            dimensions=[Dimension(name="date")]
        )
        
        response = analytics_data_client.run_report(request)
        
        print(f"✓ Acceso verificado correctamente a la propiedad: {property_id}")
        print("  Se pudo obtener datos de esta propiedad.")
        
        # Mostrar una pequeña vista previa de los datos
        print("\n=== Vista previa de datos ===")
        dimension_names = [header.name for header in response.dimension_headers]
        metric_names = [header.name for header in response.metric_headers]
        
        print(f"Dimensiones: {dimension_names}")
        print(f"Métricas: {metric_names}")
        
        # Mostrar hasta 5 filas
        row_count = min(5, len(response.rows))
        for i in row_count:
            row = response.rows[i]
            dimensions = [dim.value for dim in row.dimension_values]
            metrics = [metric.value for metric in row.metric_values]
            print(f"Fila {i+1}: {dimensions} - {metrics}")
        
        return True
    except Exception as e:
        print(f"ERROR: No se puede acceder a la propiedad {property_id}: {str(e)}")
        print("\nPosibles soluciones:")
        print("1. Verifica que el ID de la propiedad es correcto")
        print("2. Asegúrate que la cuenta de servicio tiene permisos para esta propiedad específica")
        print("3. Verifica que la propiedad está activa y recolectando datos")
        return False

def main():
    """
    Función principal del script.
    - Procesa los argumentos de línea de comandos.
    - Verifica credenciales y acceso a la API.
    - Lista cuentas y propiedades disponibles.
    - Si se indica, verifica el acceso a una propiedad específica.
    """
    parser = argparse.ArgumentParser(description='Verificar permisos y acceso a Google Analytics 4')
    parser.add_argument('--key-file', required=True, help='Ruta al archivo JSON de credenciales')
    parser.add_argument('--property-id', help='ID de la propiedad específica a verificar')
    
    args = parser.parse_args()
    
    # Verificar credenciales
    credenciales = verificar_credenciales(args.key_file)
    if not credenciales:
        sys.exit(1)
        
    # Verificar acceso a la API
    analytics_data_client, analytics_admin_client = verificar_acceso_api(credenciales)
    if not analytics_data_client or not analytics_admin_client:
        sys.exit(1)
        
    # Listar cuentas disponibles
    listar_cuentas_disponibles(analytics_admin_client)
    
    # Si se proporcionó una propiedad específica, verificarla
    if args.property_id:
        if not verificar_propiedad_especifica(analytics_data_client, args.property_id):
            sys.exit(1)
    
    print("\n✅ Verificación completada.")
    
if __name__ == "__main__":
    main()