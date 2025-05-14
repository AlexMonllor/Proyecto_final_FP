# -*- coding: utf-8 -*-

from odoo import models, fields
import base64
import io
import pandas as pd
import tempfile
import os
import chardet

class ImportCSVWizard(models.TransientModel):
    _name = 'ai_train_model.import.wizard'
    _description = 'Asistente para importar datos CSV'

    descarga_id = fields.Many2one('ai_train_model.descarga_ga4', string='Descarga', required=True)
    archivo_csv = fields.Binary(string='Archivo CSV', required=True)
    nombre_archivo = fields.Char(string='Nombre del archivo')
    metricas = fields.Many2many('ai_train_model.metricas_ga4', string='Métricas')
    dimensiones = fields.Many2many('ai_train_model.dimensiones_ga4', string='Dimensiones')

    def action_importar(self):
        """Procesa e importa el archivo CSV seleccionado"""
        self.ensure_one()
        
        if not self.archivo_csv:
            return self._show_error('Por favor, seleccione un archivo CSV para importar')

        try:
            # Verificar extensión
            if not (self.nombre_archivo or '').lower().endswith('.csv'):
                return self._show_error('El archivo debe tener extensión .csv')

            # Decodificar archivo
            csv_data = base64.b64decode(self.archivo_csv)
            
            # Detectar codificación del archivo
            detected = chardet.detect(csv_data)
            encoding = detected['encoding'] or 'utf-8'
            
            # Intentar leer el archivo con la codificación detectada
            try:
                # Guardar temporalmente el archivo para que pandas lo pueda leer
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                    temp_file.write(csv_data)
                    temp_path = temp_file.name

                try:
                    # Intentar leer con la codificación detectada
                    df = pd.read_csv(temp_path, encoding=encoding)
                except UnicodeDecodeError:
                    # Si falla, intentar con otras codificaciones comunes
                    for enc in ['utf-8', 'latin1', 'cp1252']:
                        try:
                            df = pd.read_csv(temp_path, encoding=enc)
                            encoding = enc
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        raise ValueError("No se pudo decodificar el archivo con ninguna codificación conocida")
                finally:
                    # Limpiar archivo temporal
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass

                if df.empty:
                    return self._show_error('El archivo CSV está vacío')

                # Procesar datos
                df = df.copy()
                # Convertir todas las columnas a string
                df = df.astype(str)
                
                # Limpiar datos
                df.replace(['unknown', 'null', '(none)', '(not set)', '', 'nan', 'NaN'], '0', inplace=True)
                df.fillna('0', inplace=True)
                
                # Convertir DataFrame a CSV con codificación utf-8
                output = io.StringIO()
                df.to_csv(output, index=False)
                processed_csv_data = output.getvalue().encode('utf-8')
                
                # Actualizar el registro de descarga
                self.descarga_id.write({
                    'archivo_csv': base64.b64encode(processed_csv_data),
                    'nombre_archivo': self.nombre_archivo or 'datos_importados.csv',
                    'estado_actual': 'Completado',
                    'progreso': 100,
                    'estado_descarga': f"✓ Datos importados exitosamente\n"
                                     f"Total de registros: {len(df)}\n"
                                     f"Columnas: {', '.join(df.columns)}\n"
                                     f"Codificación detectada: {encoding}\n"
                                     f"Archivo: {self.nombre_archivo or 'datos_importados.csv'}"
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Archivo CSV importado correctamente',
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except Exception as e:
                return self._show_error(f'Error al procesar el archivo: {str(e)}')
                
        except Exception as e:
            return self._show_error(f'Error al importar el archivo: {str(e)}')
    
    def _show_error(self, message):
        """Muestra un mensaje de error"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'danger',
                'sticky': True,
            }
        }
