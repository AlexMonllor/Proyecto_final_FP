# -*- coding: utf-8 -*-
# from odoo import http


# class AiTrainModel(http.Controller):
#     @http.route('/ai_train_model/ai_train_model', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ai_train_model/ai_train_model/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ai_train_model.listing', {
#             'root': '/ai_train_model/ai_train_model',
#             'objects': http.request.env['ai_train_model.ai_train_model'].search([]),
#         })

#     @http.route('/ai_train_model/ai_train_model/objects/<model("ai_train_model.ai_train_model"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ai_train_model.object', {
#             'object': obj
#         })

