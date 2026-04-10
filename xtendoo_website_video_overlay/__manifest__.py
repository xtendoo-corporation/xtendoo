{
    'name': 'Xtendoo Website Video Overlay',
    'summary': 'Snippet de imagen con overlay y reproducción de vídeo HTML5 interno en modal global',
    'description': 'Permite ubicar vídeos servidos nativamente desde Odoo sin depender de iframes ni YouTube.',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'author': 'Xtendoo Software S.L.U.',
    'website': 'https://xtendoo.es',
    'license': 'OPL-1',
    'depends': ['website'],
    'data': [
        'views/snippets/s_video_overlay.xml',
        'views/snippets/snippets.xml',
        'views/snippets/options.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'xtendoo_website_video_overlay/static/src/scss/video_overlay.scss',
            'xtendoo_website_video_overlay/static/src/js/video_overlay.js',
        ],
        'website.assets_wysiwyg': [
            'xtendoo_website_video_overlay/static/src/js/video_overlay_options.js',
        ],
    },
    'post_init_hook': '_post_init_cleanup',
    'installable': True,
    'application': False,
}
