# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    fsm_order_id = fields.Many2one(
        'daruclima.fsm.order',
        string='Orden de Trabajo FSM',
        help="Orden de trabajo FSM relacionada con esta reparación"
    )
