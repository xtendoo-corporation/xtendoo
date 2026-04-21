{
    'name': 'Xtendoo Website Dark Mode',
    'summary': 'Toggle de modo oscuro/claro configurable para la website',
    'description': 'Añade un botón al menú superior de la website para alternar entre modo claro y oscuro, con paleta oscura configurable por website.',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'author': 'Xtendoo Software S.L.U.',
    'website': 'https://xtendoo.es',
    'license': 'OPL-1',
    'depends': ['website'],
    'data': [
        'views/website_templates.xml',
        'views/res_config_settings_views.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'xtendoo_website_darkmode/static/src/scss/darkmode.scss',
            'xtendoo_website_darkmode/static/src/js/darkmode_toggle.js',
        ],
    },
    'installable': True,
    'application': False,
}

