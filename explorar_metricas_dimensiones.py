#!/usr/bin/env python3
"""
Script para explorar las métricas y dimensiones disponibles en Google Analytics 4
"""
import argparse
import pandas as pd
import sys
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    GetMetadataRequest
)
from google.oauth2 import service_account

def initialize_analytics_client(key_file_location):
    """Inicializa el cliente de Analytics Data.

    Args:
        key_file_location: ruta al archivo JSON de credenciales

    Returns:
        Un cliente autorizado de Analytics Data.
    """
    try:
        print(f"Intentando autenticar con credenciales de: {key_file_location}")
        
        # Usar credenciales de cuenta de servicio
        credentials = service_account.Credentials.from_service_account_file(
            key_file_location,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        
        # Construir el cliente de Analytics Data
        client = BetaAnalyticsDataClient(credentials=credentials)
        print("✓ Autenticación exitosa con Google Analytics Data API")
        
        return client
    except Exception as e:
        print(f"Error durante la autenticación: {str(e)}")
        sys.exit(1)

def obtener_metadatos(client, property_id):
    """
    Obtiene los metadatos de métricas y dimensiones disponibles para una propiedad GA4
    
    Args:
        client: Cliente autorizado de Analytics Data
        property_id: ID de la propiedad GA4
        
    Returns:
        Listas de métricas y dimensiones disponibles
    """
    try:
        # Asegurar formato correcto del property_id
        if not property_id.startswith("properties/"):
            property_id = f"properties/{property_id}"
            
        print(f"Obteniendo metadatos para propiedad: {property_id}")
        
        # Solicitar metadatos
        metadata_request = GetMetadataRequest(name=f"{property_id}/metadata")
        metadata = client.get_metadata(metadata_request)
        
        # Procesar métricas
        metricas = []
        for metric in metadata.metrics:
            metricas.append({
                'nombre': metric.api_name,
                'display_name': metric.ui_name,
                'descripcion': metric.description,
                'categoria': metric.category,
                'tipo': metric.type_.name
            })
            
        # Procesar dimensiones
        dimensiones = []
        for dimension in metadata.dimensions:
            dimensiones.append({
                'nombre': dimension.api_name,
                'display_name': dimension.ui_name,
                'descripcion': dimension.description,
                'categoria': dimension.category
            })
            
        return metricas, dimensiones
        
    except Exception as e:
        print(f"Error al obtener metadatos: {str(e)}")
        sys.exit(1)
        
def explorar_datos_ejemplo(client, property_id, metricas_ejemplo, dimensiones_ejemplo):
    """
    Muestra un ejemplo de datos usando algunas métricas y dimensiones
    
    Args:
        client: Cliente autorizado de Analytics Data
        property_id: ID de la propiedad GA4
        metricas_ejemplo: Lista de métricas para consultar
        dimensiones_ejemplo: Lista de dimensiones para consultar
    """
    try:
        # Asegurar formato correcto del property_id
        if not property_id.startswith("properties/"):
            property_id = f"properties/{property_id}"
            
        print(f"\n=== Obteniendo datos de ejemplo ===")
        print(f"Métricas: {', '.join(metricas_ejemplo)}")
        print(f"Dimensiones: {', '.join(dimensiones_ejemplo)}")
        
        # Crear solicitud
        request = RunReportRequest(
            property=property_id,
            dimensions=[Dimension(name=d) for d in dimensiones_ejemplo],
            metrics=[Metric(name=m) for m in metricas_ejemplo],
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            limit=10
        )
        
        # Ejecutar consulta
        response = client.run_report(request)
        
        # Mostrar resultados
        print("\n=== Datos de ejemplo (últimos 30 días) ===")
        
        # Cabeceras
        dimension_headers = [header.name for header in response.dimension_headers]
        metric_headers = [header.name for header in response.metric_headers]
        print(f"Dimensiones: {dimension_headers}")
        print(f"Métricas: {metric_headers}")
        
        # Datos
        print("\nFilas de ejemplo:")
        for row in response.rows:
            dimension_values = [value.value for value in row.dimension_values]
            metric_values = [value.value for value in row.metric_values]
            print(f"  {dimension_values} - {metric_values}")
            
    except Exception as e:
        print(f"Error al explorar datos de ejemplo: {str(e)}")

def mostrar_metricas_recomendadas():
    """Muestra una lista de métricas y dimensiones recomendadas para modelos predictivos"""
    print("\n=== MÉTRICAS Y DIMENSIONES RECOMENDADAS PARA MODELOS PREDICTIVOS ===")
    print("""
PARA PREDECIR CONVERSIONES:

Métricas clave:
- conversions                 : Total de conversiones
- ecommercePurchases          : Compras de comercio electrónico
- transactions                : Transacciones
- purchaseRevenue             : Ingresos de compra
- itemsPurchased              : Artículos comprados
- averagePurchaseRevenue      : Valor promedio de transacción

Dimensiones útiles:
- sessionSource               : Fuente de la sesión
- sessionMedium               : Medio de la sesión
- deviceCategory             : Tipo de dispositivo (mobile, desktop, tablet)
- city                       : Ciudad del usuario
- country                    : País del usuario
- dayOfWeek                  : Día de la semana
- date                       : Fecha
- userType                   : Tipo de usuario (nuevo vs. recurrente)
- sessionCampaignName        : Nombre de campaña
- landingPage                : Página de aterrizaje

PARA PREDECIR ENGAGEMENT:

Métricas clave:
- engagementRate             : Tasa de engagement
- activeUsers                : Usuarios activos
- sessions                   : Sesiones
- totalUsers                 : Total de usuarios
- screenPageViews            : Vistas de página
- userEngagementDuration     : Duración de engagement
- sessionDuration            : Duración de sesión
- bounceRate                 : Tasa de rebote
- eventsPerSession           : Eventos por sesión

COMPORTAMIENTO DEL USUARIO:

Dimensiones útiles:
- newVsReturning             : Usuarios nuevos vs. recurrentes
- sessionDefaultChannelGrouping: Agrupación de canal por defecto
- pageReferrer               : Página de referencia
- pageTitle                  : Título de la página
- pagePathPlusQueryString    : Ruta de página más cadena de consulta
- firstUserMedium            : Medio del primer usuario
- firstUserSource            : Fuente del primer usuario
""")

def guardar_lista_metricas_dimensiones(metricas, dimensiones, archivo_salida):
    """Guarda las listas de métricas y dimensiones en un archivo CSV
    
    Args:
        metricas: Lista de diccionarios con información de métricas
        dimensiones: Lista de diccionarios con información de dimensiones
        archivo_salida: Nombre base para los archivos CSV de salida
    """
    # Convertir a DataFrames
    df_metricas = pd.DataFrame(metricas)
    df_dimensiones = pd.DataFrame(dimensiones)
    
    # Guardar en archivos CSV
    archivo_metricas = f"{archivo_salida}_metricas.csv"
    archivo_dimensiones = f"{archivo_salida}_dimensiones.csv"
    
    df_metricas.to_csv(archivo_metricas, index=False)
    df_dimensiones.to_csv(archivo_dimensiones, index=False)
    
    print(f"\nLista de métricas guardada en: {archivo_metricas}")
    print(f"Lista de dimensiones guardada en: {archivo_dimensiones}")

def main():
    parser = argparse.ArgumentParser(description='Explorar métricas y dimensiones disponibles en Google Analytics 4')
    parser.add_argument('--key-file', required=True, help='Ruta al archivo JSON de credenciales')
    parser.add_argument('--property-id', required=True, help='ID de la propiedad de GA4')
    parser.add_argument('--output', default='ga4_metadata', help='Nombre base para los archivos CSV de salida')
    parser.add_argument('--ejemplo', action='store_true', help='Mostrar datos de ejemplo usando métricas seleccionadas')
    
    args = parser.parse_args()
    
    # Inicializar cliente
    client = initialize_analytics_client(args.key_file)
    
    # Obtener metadatos
    metricas, dimensiones = obtener_metadatos(client, args.property_id)
    
    # Mostrar resumen
    print(f"\n=== MÉTRICAS DISPONIBLES: {len(metricas)} ===")
    for i, metrica in enumerate(metricas[:10], 1):
        print(f"{i}. {metrica['nombre']} - {metrica['display_name']} - {metrica['categoria']}")
    
    if len(metricas) > 10:
        print(f"... y {len(metricas) - 10} más")
        
    print(f"\n=== DIMENSIONES DISPONIBLES: {len(dimensiones)} ===")
    for i, dimension in enumerate(dimensiones[:10], 1):
        print(f"{i}. {dimension['nombre']} - {dimension['display_name']} - {dimension['categoria']}")
    
    if len(dimensiones) > 10:
        print(f"... y {len(dimensiones) - 10} más")
    
    # Mostrar algunas métricas y dimensiones recomendadas para modelos predictivos
    mostrar_metricas_recomendadas()
    
    # Guardar listas completas en CSV
    guardar_lista_metricas_dimensiones(metricas, dimensiones, args.output)
    
    # Mostrar ejemplo de datos si se solicita
    if args.ejemplo:
        # Métricas y dimensiones de ejemplo para comportamiento de compra
        metricas_ejemplo = ['transactions', 'purchaseRevenue', 'activeUsers']
        dimensiones_ejemplo = ['date', 'sessionSource', 'deviceCategory']
        
        explorar_datos_ejemplo(client, args.property_id, metricas_ejemplo, dimensiones_ejemplo)
    
if __name__ == "__main__":
    main()