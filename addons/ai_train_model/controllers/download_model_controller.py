from odoo import http
from odoo.http import request, content_disposition
import base64

class ModelDownloadController(http.Controller):
    @http.route('/ai_train_model/model_report/<int:model_id>', type='http', auth="user", website=True)
    def view_model_report(self, model_id, **kw):
        model = request.env['ai_train_model.entrenador'].browse(model_id)
        if not model.estado_entrenamiento:
            return request.not_found()
        
        # Crear un HTML con el informe
        html_content = f"""
        <html>
            <head>
                <title>Informe del Modelo - {model.name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 800px; margin: 0 auto; }}
                    .header {{ background-color: #875A7B; color: white; padding: 20px; border-radius: 5px; }}
                    .content {{ padding: 20px; background-color: #f8f9fa; border-radius: 5px; margin-top: 20px; }}
                    .metrics {{ white-space: pre-wrap; font-family: monospace; }}
                    .download-btn {{
                        background-color: #28a745;
                        color: white;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 5px;
                        display: inline-block;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{model.name}</h1>
                        <p>Tipo de modelo: {model.tipo_modelo}</p>
                        <p>Estado: {model.estado}</p>
                    </div>
                    <div class="content">
                        <h2>Resultados del Entrenamiento</h2>
                        <div class="metrics">
                            {model.estado_entrenamiento}
                        </div>
                        <a href="/ai_train_model/download_model/{model.id}" class="download-btn">
                            Descargar Modelo
                        </a>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return request.make_response(html_content, headers=[('Content-Type', 'text/html;charset=utf-8')])

    @http.route('/ai_train_model/download_model/<int:model_id>', type='http', auth="user")
    def download_model(self, model_id, **kw):
        model = request.env['ai_train_model.entrenador'].browse(model_id)
        if not model.modelos_generados:
            return request.not_found()
            
        return request.make_response(
            base64.b64decode(model.modelos_generados),
            headers=[
                ('Content-Type', 'application/zip'),
                ('Content-Disposition', content_disposition(model.nombre_archivo or 'modelo_entrenado.zip'))
            ]
        )
