# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campos FSM
    is_fsm_service = fields.Boolean(
        string='Es Servicio FSM',
        help="Este producto se usa en servicios de campo"
    )
    is_fsm_material = fields.Boolean(
        string='Es Material FSM',
        help="Este producto se usa como material en servicios de campo"
    )
    fsm_category_ids = fields.Many2many(
        'daruclima.fsm.tag',
        string='Categorías FSM',
        help="Categorías de servicio para este producto"
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Campos FSM heredados
    is_fsm_service = fields.Boolean(
        related='product_tmpl_id.is_fsm_service',
        store=True
    )
    is_fsm_material = fields.Boolean(
        related='product_tmpl_id.is_fsm_material',
        store=True
    )
