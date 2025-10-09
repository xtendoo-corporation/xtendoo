# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuración FSM
    fsm_auto_create_project = fields.Boolean(
        string='Crear Proyecto Automáticamente',
        config_parameter='xtendoo_fsm.auto_create_project',
        help="Crear automáticamente un proyecto para cada orden de trabajo"
    )
    fsm_enable_geolocation = fields.Boolean(
        string='Habilitar Geolocalización',
        config_parameter='xtendoo_fsm.enable_geolocation',
        help="Habilitar funciones de geolocalización para órdenes de trabajo"
    )
    fsm_invoice_policy = fields.Selection([
        ('manual', 'Manual'),
        ('timesheet', 'Basado en Hojas de Tiempo'),
        ('delivery', 'Al Completar Orden')
    ], string='Política de Facturación FSM',
        config_parameter='xtendoo_fsm.invoice_policy',
        default='manual'
    )
