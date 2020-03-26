# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models, api

import logging


class DeliveryZonePartnerLine(models.Model):
    _name = 'delivery.zone.partner.line'
    _table = 'delivery_zone_partner_line'
    _description = 'Partner delivery zone line'
    _rec_name = 'delivery_zone_id'

    delivery_zone_id = fields.Many2one(
        'partner.delivery.zone',
        string='Delivery Zone',
        ondelete='cascade',
        required=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
    )

    @api.multi
    def _get_next_sequence(self):
        return self.env['ir.sequence'].next_by_code('res.partner.delivery.zone')

    sequence = fields.Integer(
        string='Sequence',
        default=_get_next_sequence,
    )
    display_name = fields.Char(
        related='partner_id.display_name',
        store=False,
        readonly=True,
    )
    street = fields.Char(
        related='partner_id.street',
        store=False,
        readonly=True,
    )
    street2 = fields.Char(
        related='partner_id.street2',
        store=False,
        readonly=True,
    )
    city = fields.Char(
        related='partner_id.city',
        store=False,
        readonly=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        string='State',
        related='partner_id.state_id',
        readonly=True,
    )
    zip = fields.Char(
        related='partner_id.zip',
        store=False,
        readonly=True,
    )
    phone = fields.Char(
        related='partner_id.phone',
        store=False,
        readonly=True,
    )

    ref = fields.Char(
        related='partner_id.ref',
        store=False,
        readonly=True,
    )

    _sql_constraints = [
        ('unique_delivery_zone',
         'unique (delivery_zone_id, partner_id)',
         'Partner cannot be subscribed multiple times to the same list!')
    ]

    @api.model
    def create(self, values):
        return super(DeliveryZonePartnerLine, self).create(values)

    @api.multi
    def write(self, values):
        return super(DeliveryZonePartnerLine, self).write(values)
