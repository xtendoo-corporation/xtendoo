{
    'name': 'Xtendoo Website Lottie',
    'summary': 'Snippet reutilizable para animaciones Lottie en Website',
    'description': 'Permite cargar animaciones Lottie JSON en páginas web de Odoo mediante un snippet reutilizable y assets frontend propios.',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'author': 'Xtendoo Software S.L.U.',
    'website': 'https://xtendoo.es',
    'license': 'OPL-1',
    'depends': ['website'],
    'data': [
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'xtendoo_website_lottie/static/lib/lottie/lottie.min.js',
            'xtendoo_website_lottie/static/src/js/lottie_init.js',
            'xtendoo_website_lottie/static/src/scss/lottie.scss',
        ],
    },
    'installable': True,
    'application': False,
}
