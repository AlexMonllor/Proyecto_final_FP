#!/usr/bin/env python3
"""
Script para cargar datos de Google Analytics a BigQuery
"""
import os
import argparse
from google.cloud import bigquery

def cargar_a_bigquery(archivo_csv, dataset_id, tabla_id, proyecto_id=None):
    """
    Carga datos desde un archivo CSV a BigQuery
    
    Args:
        archivo_csv: Ruta del archivo CSV con los datos
        dataset_id: ID del dataset en BigQuery
        tabla_id: ID de la tabla en BigQuery
        proyecto_id: ID del proyecto de Google Cloud (si es None, usa el proyecto por defecto)
    """
    # Crear cliente de BigQuery
    cliente = bigquery.Client(project=proyecto_id)
    
    # Definir referencia al dataset y tabla
    tabla_ref = cliente.dataset(dataset_id).table(tabla_id)
    
    # Configurar el trabajo de carga
    configuracion_trabajo = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Ignora la cabecera
        autodetect=True,  # Detecta automáticamente el esquema
    )

    print(f"Cargando datos de {archivo_csv} a {dataset_id}.{tabla_id}")
    
    # Cargar datos a BigQuery
    with open(archivo_csv, "rb") as archivo:
        trabajo_carga = cliente.load_table_from_file(
            archivo, tabla_ref, job_config=configuracion_trabajo
        )
    
    # Esperar a que termine el trabajo de carga
    trabajo_carga.result()
    
    print(f"Carga completada. Filas cargadas: {trabajo_carga.output_rows}")

def main():
    parser = argparse.ArgumentParser(description='Cargar datos de Google Analytics a BigQuery')
    parser.add_argument('--archivo', required=True, help='Ruta del archivo CSV con datos')
    parser.add_argument('--proyecto', help='ID del proyecto de Google Cloud')
    parser.add_argument('--dataset', required=True, help='ID del dataset en BigQuery')
    parser.add_argument('--tabla', required=True, help='ID de la tabla en BigQuery')
    
    args = parser.parse_args()
    
    # Verificar que el archivo existe
    if not os.path.exists(args.archivo):
        print(f"Error: El archivo {args.archivo} no existe.")
        return
    
    # Cargar datos a BigQuery
    cargar_a_bigquery(args.archivo, args.dataset, args.tabla, args.proyecto)

if __name__ == "__main__":
    main()