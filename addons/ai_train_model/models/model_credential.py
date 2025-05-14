# -*- coding: utf-8 -*-

import os
import base64
import tempfile
from odoo import models, fields
from ..project.verificar_permisos_ga import verificar_credenciales, verificar_acceso_api, listar_cuentas_y_propiedades_disponibles


class VerificadorGA4(models.Model):
    _name = 'ai_train_model.verificador_ga4'
    _description = 'Verificador de Permisos de Google Analytics 4'

    name = fields.Char(string='Nombre de la verificación', required=True, 
                        help='Identificador para esta verificación de credenciales')
    archivo_credenciales = fields.Binary(string='Archivo de credenciales', required=True,
                                        help='Archivo JSON con las credenciales de GA4')
    nombre_archivo = fields.Char(string='Nombre del archivo')
    estado_verificacion = fields.Text(string='Estado de la verificación', readonly=True,
                                    help='Resultado de la verificación de permisos y acceso')

    def verificar_permisos_ga4(self):
        """Verifica los permisos y acceso a Google Analytics 4 usando el archivo de credenciales"""
        self.ensure_one()

        if not self.archivo_credenciales:
            self.estado_verificacion = "ERROR: No se ha subido ningún archivo de credenciales"
            return

        try:
            # Decodificar y guardar el archivo temporalmente
            decoded_file = base64.b64decode(self.archivo_credenciales)
            fd, temp_path = tempfile.mkstemp(suffix='.json')
            try:
                with os.fdopen(fd, 'wb') as temp:
                    temp.write(decoded_file)

                # Verificar credenciales
                credenciales = verificar_credenciales(temp_path)
                if not credenciales:
                    self.estado_verificacion = "ERROR: Las credenciales de GA4 no son válidas"
                    return

                # Verificar acceso a la API
                analytics_data_client, analytics_admin_client = verificar_acceso_api(credenciales)
                if not analytics_data_client or not analytics_admin_client:
                    self.estado_verificacion = "ERROR: No se pudo establecer conexión con la API de Google Analytics"
                    return

                # Listar cuentas y propiedades
                import io
                from contextlib import redirect_stdout

                # Capturar la salida del método en una variable
                f = io.StringIO()
                with redirect_stdout(f):
                    listar_cuentas_y_propiedades_disponibles(analytics_admin_client)
                
                # Guardar el resultado
                self.estado_verificacion = f.getvalue()
                f.close()

            finally:
                # Limpiar archivo temporal
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    pass  # Ignorar errores al eliminar archivo temporal

        except Exception as e:
            self.estado_verificacion = f"ERROR en la verificación: {str(e)}"

