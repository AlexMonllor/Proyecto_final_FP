# -*- coding: utf-8 -*-
{
    'name': "Modulo de Entrenamiento de IA",
    'summary': """
        Modulo de Entrenamiento de IA""",

    'description': """
Long description of module's purpose
    """,

    'author': "Alex Monllor Jerez",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ga4_data.xml',
        'views/view_credential.xml',
        'views/view_download.xml',
        'views/view_trainer.xml',
        'views/menus.xml',
        'views/templates.xml',
        'wizards/import_wizard_view.xml',
    ],
    
    # Archivos de requisitos Python
    'external_dependencies': {
        'python': [
            'pandas',
            'numpy',
            'scikit-learn',
            'joblib',
            'matplotlib',
            'seaborn'
        ],
    },
    # only loaded in demonstration mode

}

