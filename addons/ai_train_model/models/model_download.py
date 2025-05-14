# -*- coding: utf-8 -*-

import os
import tempfile
import pandas as pd
from datetime import datetime
from odoo import models, fields, api
from ..project.descargar_datos_predictivos import (
    initialize_analytics_client,
    descargar_datos_paginados,
    guardar_datos_csv,
)


class DescargaGA4(models.Model):
    _name = 'ai_train_model.descarga_ga4'
    _description = 'Descarga de datos de Google Analytics 4'
    _rec_name = 'name'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Nombre de la descarga',
        required=True,
        help='Identificador para esta descarga de datos',
        tracking=True
    )
    property_id = fields.Char(
        string='ID de la propiedad GA4',
        required=True,
        help='ID de la propiedad de GA4 de donde se descargarán los datos'
    )
    credencial_id = fields.Many2one(
        'ai_train_model.verificador_ga4',
        string='Credenciales GA4',
        required=True,
        help='Credenciales verificadas para acceder a GA4'
    )
    fecha_inicio = fields.Date(
        string='Fecha de inicio',
        required=True,
        default=fields.Date.today,
        help='Fecha desde la que se descargarán los datos'
    )
    fecha_fin = fields.Date(
        string='Fecha fin',
        required=True,
        default=fields.Date.today,
        help='Fecha hasta la que se descargarán los datos'
    )
    metricas_ids = fields.Many2many(
        'ai_train_model.metricas_ga4',
        string='Métricas a descargar',
        help='Seleccione las métricas que desea incluir en la descarga'
    )
    dimensiones_ids = fields.Many2many(
        'ai_train_model.dimensiones_ga4',
        string='Dimensiones a descargar',
        help='Seleccione las dimensiones que desea incluir en la descarga'
    )
    archivo_csv = fields.Binary(
        string='Archivo CSV descargado',
        readonly=True
    )
    nombre_archivo = fields.Char(
        string='Nombre del archivo',
        readonly=True
    )
    estado_descarga = fields.Text(
        string='Estado de la descarga',
        readonly=True
    )
    progreso = fields.Float(
        string='Progreso de descarga',
        readonly=True,
        default=0.0
    )
    estado_actual = fields.Char(
        string='Estado actual',
        readonly=True
    )

    @api.model
    def _download_ga4_data(self, download_id):
        """Método interno para descargar datos en segundo plano"""
        download = self.browse(download_id)
        try:
            # Preparar credenciales
            fd_cred, temp_cred_path = tempfile.mkstemp(suffix='.json')
            try:
                with os.fdopen(fd_cred, 'wb') as temp_cred:
                    temp_cred.write(download.credencial_id.archivo_credenciales)

                # Iniciar cliente GA4
                client = initialize_analytics_client(temp_cred_path)
                start_date = download.fecha_inicio.strftime('%Y-%m-%d')
                end_date = download.fecha_fin.strftime('%Y-%m-%d')
                
                # Preparar métricas y dimensiones
                metricas = [m.nombre_tecnico for m in download.metricas_ids]
                dimensiones = [d.nombre_tecnico for d in download.dimensiones_ids]
                
                # Descargar datos
                datos = descargar_datos_paginados(
                    client, 
                    download.property_id,
                    start_date,
                    end_date,
                    dimensiones,
                    metricas
                )
                
                if not datos:
                    raise ValueError("No se encontraron datos para los criterios seleccionados")

                # Procesar datos
                df = pd.DataFrame(datos)
                df.replace(['unknown', 'null', '(none)', '(not set)', ''], 0, inplace=True)
                df.replace({pd.NA: 0, None: 0}, inplace=True)
                df.fillna(0, inplace=True)
                datos = df.to_dict('records')

                # Guardar CSV
                fd_csv, temp_csv_path = tempfile.mkstemp(suffix='.csv')
                try:
                    guardar_datos_csv(datos, temp_csv_path)
                    with open(temp_csv_path, 'rb') as temp_csv:
                        csv_content = temp_csv.read()
                        
                    fecha_actual = datetime.now().strftime("%Y%m%d")
                    nombre_archivo = f"ga4_datos_personalizados_{fecha_actual}.csv"
                    
                    download.write({
                        'archivo_csv': csv_content,
                        'nombre_archivo': nombre_archivo,
                        'estado_actual': 'Completado',
                        'progreso': 100,
                        'estado_descarga': f"✓ Datos descargados exitosamente\n"
                                        f"Total de registros: {len(datos)}\n"
                                        f"Métricas: {', '.join(metricas)}\n"
                                        f"Dimensiones: {', '.join(dimensiones)}\n"
                                        f"Archivo: {nombre_archivo}"
                    })
                finally:
                    os.unlink(temp_csv_path)
            finally:
                os.unlink(temp_cred_path)
        except Exception as e:
            download.write({
                'estado_actual': 'Error',
                'progreso': 0,
                'estado_descarga': f"ERROR durante la descarga: {str(e)}"
            })
            self._cr.commit()
            raise

    def action_descargar_datos(self):
        """Descarga los datos de GA4 según los parámetros configurados"""
        self.ensure_one()

        if not self.metricas_ids or not self.dimensiones_ids:
            self.write({
                'estado_actual': 'Error',
                'estado_descarga': "ERROR: Debe seleccionar al menos una métrica y una dimensión",
                'progreso': 0
            })
            return

        if not self.credencial_id or not self.credencial_id.archivo_credenciales:
            self.write({
                'estado_actual': 'Error',
                'estado_descarga': "ERROR: No se han configurado las credenciales",
                'progreso': 0
            })
            return

        try:
            # Preparar credenciales
            self.write({
                'estado_actual': 'Preparando credenciales...',
                'progreso': 10,
                'estado_descarga': ''
            })

            # Crear archivo temporal para las credenciales
            fd_cred, temp_cred_path = tempfile.mkstemp(suffix='.json')
            try:
                # Guardar credenciales en archivo temporal
                with os.fdopen(fd_cred, 'wb') as temp_cred:
                    temp_cred.write(self.credencial_id.archivo_credenciales)

                self.write({'estado_actual': 'Iniciando conexión con GA4...', 'progreso': 20})
                
                # Inicializar cliente
                client = initialize_analytics_client(temp_cred_path)
                
                # Preparar fechas en formato correcto
                start_date = self.fecha_inicio.strftime('%Y-%m-%d')
                end_date = self.fecha_fin.strftime('%Y-%m-%d')
                
                self.write({'estado_actual': 'Preparando parámetros...', 'progreso': 30})

                # Obtener métricas y dimensiones seleccionadas
                metricas = [m.nombre_tecnico for m in self.metricas_ids]
                dimensiones = [d.nombre_tecnico for d in self.dimensiones_ids]
                
                self.write({'estado_actual': 'Descargando datos...', 'progreso': 40})
                
                # Descargar datos
                datos = descargar_datos_paginados(
                    client, 
                    self.property_id, 
                    start_date, 
                    end_date, 
                    dimensiones, 
                    metricas
                )

                if not datos:
                    raise ValueError("No se encontraron datos para los criterios seleccionados")

                self.write({'estado_actual': 'Procesando datos...', 'progreso': 60})
                
                # Procesar datos
                df = pd.DataFrame(datos)
                df.replace(['unknown', 'null', '(none)', '(not set)', ''], 0, inplace=True)
                df.replace({pd.NA: 0, None: 0}, inplace=True)
                df.fillna(0, inplace=True)
                datos = df.to_dict('records')

                self.write({'estado_actual': 'Guardando resultados...', 'progreso': 80})

                # Guardar CSV
                fd_csv, temp_csv_path = tempfile.mkstemp(suffix='.csv')
                try:
                    guardar_datos_csv(datos, temp_csv_path)
                    with open(temp_csv_path, 'rb') as temp_csv:
                        csv_content = temp_csv.read()

                    fecha_actual = datetime.now().strftime("%Y%m%d")
                    nombre_archivo = f"ga4_datos_personalizados_{fecha_actual}.csv"

                    self.write({
                        'archivo_csv': csv_content,
                        'nombre_archivo': nombre_archivo,
                        'estado_actual': 'Completado',
                        'progreso': 100,
                        'estado_descarga': f"✓ Datos descargados exitosamente\n"
                                        f"Total de registros: {len(datos)}\n"
                                        f"Métricas: {', '.join(metricas)}\n"
                                        f"Dimensiones: {', '.join(dimensiones)}\n"
                                        f"Archivo: {nombre_archivo}"
                    })
                finally:
                    os.unlink(temp_csv_path)
            finally:
                os.unlink(temp_cred_path)

        except Exception as e:
            self.write({
                'estado_actual': 'Error',
                'progreso': 0,
                'estado_descarga': f"ERROR durante la descarga: {str(e)}"
            })

    def action_importar_csv(self):
        """Importa datos desde un archivo CSV"""
        self.ensure_one()

        if not self.metricas_ids or not self.dimensiones_ids:
            self.write({
                'estado_actual': 'Error',
                'estado_descarga': "ERROR: Debe seleccionar al menos una métrica y una dimensión antes de importar",
                'progreso': 0
            })
            return

        self.write({
            'estado_actual': 'Esperando archivo...',
            'progreso': 0,
            'estado_descarga': 'Por favor, seleccione un archivo CSV para importar'
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Importar CSV',
            'res_model': 'ai_train_model.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_descarga_id': self.id,
                'default_metricas': [(6, 0, self.metricas_ids.ids)],
                'default_dimensiones': [(6, 0, self.dimensiones_ids.ids)]
            }
        }


class MetricasGA4(models.Model):
    _name = 'ai_train_model.metricas_ga4'
    _description = 'Métricas disponibles en GA4'

    name = fields.Char(string='Nombre de la métrica', required=True)
    nombre_tecnico = fields.Char(string='Nombre técnico', required=True)
    descripcion = fields.Text(string='Descripción')
    categoria = fields.Selection([
        ('conversiones', 'Conversiones'),
        ('engagement', 'Engagement'),
        ('ecommerce', 'E-commerce'),
        ('usuarios', 'Usuarios'),
        ('otros', 'Otros')
    ], string='Categoría', required=True)


class DimensionesGA4(models.Model):
    _name = 'ai_train_model.dimensiones_ga4'
    _description = 'Dimensiones disponibles en GA4'

    name = fields.Char(string='Nombre de la dimensión', required=True)
    nombre_tecnico = fields.Char(string='Nombre técnico', required=True)
    descripcion = fields.Text(string='Descripción')
    categoria = fields.Selection([
        ('usuario', 'Usuario'),
        ('sesion', 'Sesión'),
        ('pagina', 'Página'),
        ('tecnologia', 'Tecnología'),
        ('geografico', 'Geográfico'),
        ('otros', 'Otros')
    ], string='Categoría', required=True)
