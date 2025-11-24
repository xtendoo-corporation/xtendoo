# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    'name': 'Xtendoo - Work Order Management',
    'summary': 'Gestión integral de partes de trabajo unificada',
    'description': """
Xtendoo Work Order Management
=============================
Módulo unificado que consolida toda la funcionalidad de gestión de partes
de trabajo en una sola aplicación compacta y reutilizable.

Características principales:
- Gestión completa de órdenes de trabajo
- Seguimiento de estados y etapas
- Portal del cliente
- Informes y reportes
- Integración con ventas, inventario y contabilidad
    """,
    'category': 'Services/Work Orders',
    'version': '18.0.1.0',
    'license': 'AGPL-3',
    'author': 'Xtendoo Software SLU',
    'website': 'https://www.xtendoo.es',
    'depends': [
        'base',
        'mail',
        'project',
        'sale_management',
        'stock',
        'hr_timesheet',
        'base_geolocalize',
        'portal',
        'contacts',
        'resource',
        'account',
        'repair',
        'maintenance',
        'hr',
    ],
    'data': [
        # Security
        'security/xtendoo_fsm_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/fsm_data.xml',
        'data/fsm_sequence.xml',
        'data/mail_template_data.xml',

        # Reports
        'report/fsm_order_report.xml',

        # Actions (cargar antes de las vistas)
        'views/fsm_actions.xml',

        # Views con acciones (cargar antes del menú)
        'views/fsm_order_views.xml',
        'views/fsm_stage_views.xml',
        'views/fsm_tag_views.xml',
        'views/sale_order_views.xml',

        # Menú (cargar al final)
        'views/fsm_menu.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
    'auto_install': False,
}
