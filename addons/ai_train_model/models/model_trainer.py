# -*- coding: utf-8 -*-

import os
import base64
import tempfile
import subprocess
import json
from datetime import datetime
from pathlib import Path
from odoo import models, fields
from odoo.exceptions import UserError

class EntrenadorModelo(models.Model):
    _name = 'ai_train_model.entrenador'
    _description = 'Entrenador de Modelos Predictivos'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Nombre del entrenamiento',
        required=True,
        help='Identificador para este entrenamiento de modelo',
        tracking=True
    )
    
    tipo_modelo = fields.Selection([
        ('conversiones', 'Modelo de Conversiones'),
        ('engagement', 'Modelo de Engagement'),
        ('todos', 'Modelo Completo')
    ], string='Tipo de Modelo', 
       required=True,
       default='todos',
       help='Tipo de modelo a entrenar',
       tracking=True
    )
    
    descarga_id = fields.Many2one(
        'ai_train_model.descarga_ga4',
        string='Datos de entrenamiento',
        required=True,
        help='Seleccione la descarga de GA4 que contiene los datos para entrenar el modelo',
        tracking=True
    )
    
    directorio_modelos = fields.Char(
        string='Directorio de modelos',
        required=True,
        default='/tmp/modelos',
        help='Ruta donde se guardarán los modelos entrenados'
    )
    
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('entrenando', 'Entrenando'),
        ('completado', 'Completado'),
        ('error', 'Error')
    ], string='Estado', 
       default='borrador',
       tracking=True
    )
    
    progreso = fields.Float(
        string='Progreso',
        default=0.0,
        tracking=True
    )
    
    estado_entrenamiento = fields.Text(
        string='Estado del entrenamiento',
        readonly=True
    )
    
    modelos_generados = fields.Binary(
        string='Modelos entrenados',
        attachment=True,
        readonly=True
    )
    
    nombre_archivo = fields.Char(
        string='Nombre del archivo',
        readonly=True
    )
        
    def _definir_metricas_objetivo(self):
        """Define las métricas objetivo según el tipo de modelo.
        
        El script de entrenamiento buscará estas métricas específicas de GA4 
        que están disponibles en el CSV descargado.
        """
        metricas = {
            'conversiones': [
                'eventCount', 'eventsPerSession', 'screenPageViews'
            ],
            'engagement': [
                'engagementRate', 'sessions', 'activeUsers'
            ],
            'todos': [
                'eventCount', 'eventsPerSession', 'screenPageViews',
                'engagementRate', 'sessions', 'activeUsers',
                'bounceRate', 'sessionsPerUser', 'userEngagementDuration'
            ]
        }
        
        # Validar si el archivo CSV existe y obtener sus columnas
        if self.descarga_id and self.descarga_id.archivo_csv:
            try:
                with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
                    temp_file.write(base64.b64decode(self.descarga_id.archivo_csv))
                    temp_file.flush()
                    import pandas as pd
                    df = pd.read_csv(temp_file.name)
                    columnas_disponibles = df.columns.tolist()
                    print(f"Columnas disponibles en el CSV: {columnas_disponibles}")
                    
                    # Validar que las métricas necesarias estén disponibles
                    metricas_requeridas = metricas[self.tipo_modelo]
                    metricas_faltantes = [m for m in metricas_requeridas if m not in columnas_disponibles]
                    if metricas_faltantes:
                        raise UserError(
                            f"Faltan las siguientes métricas en el CSV: {', '.join(metricas_faltantes)}. "
                            f"Por favor, asegúrese de incluir estas métricas al descargar los datos de GA4."
                        )
            except Exception as e:
                raise UserError(f"Error al leer el archivo CSV: {str(e)}")
        
        return metricas[self.tipo_modelo]

    def action_descargar_modelo(self):
        """Abre la URL del informe del modelo entrenado."""
        self.ensure_one()
        if not self.modelos_generados:
            raise UserError('No hay un modelo entrenado disponible para descargar.')
            
        return {
            'type': 'ir.actions.act_url',
            'url': f'/ai_train_model/model_report/{self.id}',
            'target': 'new',  # Abre en una nueva pestaña/ventana
        }

    def action_entrenar_modelo(self):
        """Inicia el proceso de entrenamiento del modelo."""
        self.ensure_one()
        
        if not self.descarga_id.archivo_csv:
            raise UserError('No hay datos de entrenamiento disponibles. Por favor, asegúrese de que la descarga de GA4 contiene datos.')
        
        try:
            # Crear directorio temporal para archivos
            with tempfile.TemporaryDirectory() as temp_dir:
                # Escribir archivo CSV
                csv_path = os.path.join(temp_dir, 'datos_entrenamiento.csv')
                with open(csv_path, 'wb') as f:
                    f.write(base64.b64decode(self.descarga_id.archivo_csv))
                
                # Asegurar que existe el directorio de modelos
                os.makedirs(self.directorio_modelos, exist_ok=True)
                
                # Actualizar estado
                self.write({
                    'estado': 'entrenando',
                    'progreso': 0.0,
                    'estado_entrenamiento': 'Iniciando entrenamiento...'
                })
                
                # Preparar comando
                script_dir = Path(os.path.dirname(os.path.realpath(__file__))).parent / 'project'
                script_path = script_dir / 'entrenar_modelo.py'
                
                # Definir métricas objetivo según el tipo de modelo
                metricas = self._definir_metricas_objetivo()
                
                cmd = [
                    'python3', str(script_path),
                    '--archivos', csv_path,
                    '--objetivos'] + metricas + [
                    '--salida', self.directorio_modelos,
                    '--modelo-salida', 'modelo_final.joblib'
                ]
                
                # Ejecutar entrenamiento
                proceso = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                stdout, stderr = proceso.communicate()
                
                if proceso.returncode != 0:
                    raise Exception(f"Error en el entrenamiento: {stderr}")
                
                # Comprimir modelos generados
                import shutil
                zip_path = os.path.join(temp_dir, 'modelos_entrenados.zip')
                shutil.make_archive(
                    os.path.splitext(zip_path)[0],  # Nombre base
                    'zip',                          # Formato
                    self.directorio_modelos         # Directorio a comprimir
                )
                
                # Leer métricas del entrenamiento
                metricas_path = os.path.join(self.directorio_modelos, 'resultados_modelo.json')
                if os.path.exists(metricas_path):
                    with open(metricas_path, 'r') as f:
                        resultados = json.load(f)
                    resumen = "\nResumen de resultados:\n"
                    for metrica, valores in resultados.items():
                        resumen += f"{metrica}:\n"
                        for k, v in valores.items():
                            resumen += f"  - {k}: {v:.4f}\n"
                else:
                    resumen = "\nNo se encontraron métricas detalladas del entrenamiento."
                
                # Guardar el archivo zip
                with open(zip_path, 'rb') as f:
                    zip_data = base64.b64encode(f.read())
                
                # Actualizar registro
                fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.write({
                    'estado': 'completado',
                    'progreso': 100.0,
                    'estado_entrenamiento': 'Entrenamiento completado exitosamente.\n' + stdout + resumen,
                    'modelos_generados': zip_data,
                    'nombre_archivo': f'modelos_entrenados_{fecha}.zip'
                })
                
                # Descargar el modelo automáticamente
                return self.action_descargar_modelo()
                
        except Exception as e:
            self.write({
                'estado': 'error',
                'estado_entrenamiento': f'Error durante el entrenamiento: {str(e)}'
            })
            raise UserError(str(e))


