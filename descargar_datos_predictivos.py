#!/usr/bin/env python3
import argparse
import pandas as pd
import sys
import csv
import os
from datetime import datetime
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
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

def descargar_datos_paginados(client, property_id, start_date, end_date, dimensiones, metricas):
    """
    Descarga datos paginados para manejar el límite de 10,000 filas y el límite de 10 métricas por solicitud.
    
    Args:
        client: Cliente de Analytics Data.
        property_id: ID de la propiedad de GA4.
        start_date: Fecha de inicio en formato YYYY-MM-DD.
        end_date: Fecha de fin en formato YYYY-MM-DD.
        dimensiones: Lista de dimensiones a incluir.
        metricas: Lista de métricas a incluir.
    
    Returns:
        Lista de filas con los datos descargados.
    """
    if not property_id.startswith("properties/"):
        property_id = f"properties/{property_id}"

    all_rows = []
    offset = 0
    limit = 100000
    max_dimensions = 9
    max_metrics = 10

    # Dividir dimensiones y métricas en grupos
    dimension_groups = [dimensiones[i:i + max_dimensions] for i in range(0, len(dimensiones), max_dimensions)]
    metric_groups = [metricas[i:i + max_metrics] for i in range(0, len(metricas), max_metrics)]

    while True:
        combined_rows = []
        for dimension_group in dimension_groups:
            for metric_group in metric_groups:
                request = RunReportRequest(
                    property=property_id,
                    dimensions=[Dimension(name=d) for d in dimension_group],
                    metrics=[Metric(name=m) for m in metric_group],
                    date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                    offset=offset,
                    limit=limit,
                )

                response = client.run_report(request)

                for row in response.rows:
                    row_data = {}
                    for i, dimension_value in enumerate(row.dimension_values):
                        row_data[dimension_group[i]] = dimension_value.value
                    for i, metric_value in enumerate(row.metric_values):
                        row_data[metric_group[i]] = metric_value.value
                    combined_rows.append(row_data)

        all_rows.extend(combined_rows)

        if len(combined_rows) < limit:
            break

        offset += limit

    return all_rows

def guardar_datos_csv(data, output_file):
    """
    Guarda los datos combinados en un único archivo CSV.
    """
    if not data:
        print("No hay datos para guardar.")
        return

    all_fieldnames = set()
    for row in data:
        all_fieldnames.update(row.keys())
    all_fieldnames = sorted(all_fieldnames)

    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=all_fieldnames)
        writer.writeheader()
        writer.writerows(data)

def main():
    parser = argparse.ArgumentParser(description='Descargar datos para modelos predictivos de GA4')
    parser.add_argument('--key-file', required=True, help='Ruta al archivo JSON de credenciales')
    parser.add_argument('--property-id', required=True, help='ID de la propiedad de GA4')
    parser.add_argument('--start-date', default='2020-01-01', help='Fecha de inicio (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2025-01-01', help='Fecha de fin (YYYY-MM-DD)')
    parser.add_argument('--modelo', default='conversiones', choices=['conversiones', 'engagement', 'todos'],help='Tipo de modelo predictivo a preparar')
    parser.add_argument('--output', help='Nombre del archivo CSV de salida. Si no se especifica, se genera automáticamente.')

    args = parser.parse_args()
    
    carpeta_descargas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DescargasCSV")
    os.makedirs(carpeta_descargas, exist_ok=True)

    if not args.output:
        fecha_actual = datetime.now().strftime("%Y%m%d")
        args.output = f"ga4_datos_{args.modelo}_{fecha_actual}.csv"

    args.output = os.path.join(carpeta_descargas, os.path.basename(args.output))

    client = initialize_analytics_client(args.key_file)
    
    if args.modelo == "conversiones":
        metricas = [
            'conversions', 'transactions', 'purchaseRevenue', 'sessions', 'activeUsers', 'sessionConversionRate', 
            'engagementRate', 'totalUsers', 'eventCount', 'addToCarts', 'checkouts', 'ecommercePurchases'
        ]
        dimensiones = [
            'date', 'sessionSource', 'sessionMedium', 'deviceCategory', 'country', 'region', 'city', 
            'dayOfWeek', 'sessionDefaultChannelGrouping', 'landingPage', 'newVsReturning'
        ]
    elif args.modelo == "engagement":
        metricas = [
            'engagementRate', 'sessions', 'activeUsers', 'screenPageViews', 'userEngagementDuration', 'bounceRate', 
            'eventsPerSession', 'sessionsPerUser', 'eventCount', 'addToCarts', 'checkouts', 'ecommercePurchases'
        ]
        dimensiones = [
            'date', 'sessionSource', 'sessionMedium', 'deviceCategory', 'country', 'region', 'city', 
            'dayOfWeek', 'sessionDefaultChannelGrouping', 'landingPage', 'newVsReturning'
        ]
    else:
        metricas = [
            'conversions', 'transactions', 'purchaseRevenue', 'itemsPurchased', 'sessionConversionRate', 
            'engagementRate', 'sessions', 'activeUsers', 'screenPageViews', 'userEngagementDuration', 'bounceRate', 
            'eventsPerSession', 'sessionsPerUser', 'totalUsers', 'eventCount', 'addToCarts', 'checkouts', 'ecommercePurchases'
        ]
        dimensiones = [
            'date', 'sessionSource', 'sessionMedium', 'deviceCategory', 'country', 'region', 'city', 
            'dayOfWeek', 'sessionDefaultChannelGrouping', 'landingPage', 'newVsReturning'
        ]

    dimensiones = [d for d in dimensiones if d]

    # Descargar datos solo para el rango de fechas indicado (sin dividir en periodos)
    all_data = descargar_datos_paginados(client, args.property_id, args.start_date, args.end_date, dimensiones, metricas)
    
    df = pd.DataFrame(all_data)
    
    if df.empty:
        print("❌ Error: No se descargaron datos. Verifica los parámetros de entrada.")
        sys.exit(1)
    
    df.replace(['unknown', 'null', '(none)', '(not set)', ''], 0, inplace=True)
    df.replace({pd.NA: 0, None: 0}, inplace=True)
    df.fillna(0, inplace=True)
    
    try:
        guardar_datos_csv(df.to_dict(orient='records'), args.output)
        print(f"\nDatos guardados en: {args.output}")

        metricas_presentes = [m for m in metricas if m in df.columns]
        if metricas_presentes:
            nombre_metricas = os.path.splitext(args.output)[0] + '_solo_metricas.csv'
            df_metricas = df[metricas_presentes]
            guardar_datos_csv(df_metricas.to_dict(orient='records'), nombre_metricas)
            print(f"Archivo solo métricas guardado en: {nombre_metricas}")
        else:
            print("No se encontraron métricas presentes en los datos para crear el archivo solo métricas.")
    except Exception as e:
        print(f"❌ Error al guardar los datos en CSV: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()