# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models, _


class DaruclimeFSMTag(models.Model):
    _name = 'daruclima.fsm.tag'
    _description = 'Etiqueta de Orden de Trabajo'
    _order = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
        translate=True
    )

    color = fields.Integer(
        string='Color',
        default=0
    )

    active = fields.Boolean(
        string='Activo',
        default=True
    )

    description = fields.Text(
        string='Descripción'
    )

    order_count = fields.Integer(
        string='Número de Órdenes',
        compute='_compute_order_count'
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'El nombre de la etiqueta debe ser único.'),
    ]

    @api.depends('name')
    def _compute_order_count(self):
        """Compute the number of FSM orders associated with this tag"""
        for record in self:
            # Buscar órdenes FSM que tengan esta etiqueta
            orders = self.env['daruclima.fsm.order'].search([
                ('tag_ids', 'in', record.id)
            ])
            record.order_count = len(orders)

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.name))
        return result
