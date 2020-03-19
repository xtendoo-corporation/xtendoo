# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import datetime

import logging

class PartnerDeliveryZone(models.Model):
    _name = 'partner.delivery.zone'
    _description = 'Partner delivery zone'

    date = datetime.utcnow()

    name = fields.Char(
        string='Zone',
        required=True,
    )
    partner_zones_ids = fields.One2many(
        'delivery.zone.partner.line',
        'delivery_zone_id',
        string='Partner Zones Line',
        auto_join=True,
    )
    visit_ids = fields.One2many(
        'partner.delivery.zone.visit',
        'delivery_zone_id',
        string='Delivery Zone Visit',
        auto_join=True,
    )
    sale_order_ids = fields.One2many(
        'sale.order',
        'delivery_zone_id',
        string='Delivery Zone',
        auto_join=True,
    )

    @api.multi
    def set_values(self):
        super(PartnerDeliveryZone, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("partner.delivery.zone", self.code or '')

    @api.multi
    def get_quotations_today(self):
        return self.env['sale.order'].search(
            [('delivery_zone_id', '=', self.id),
             ('state', '=', 'draft'),
             ('date_order', '>=', datetime.combine(self.date, datetime.min.time())),
             ('date_order', '<=', datetime.combine(self.date, datetime.max.time()))]
        )

    @api.multi
    def get_orders_today(self):
        return self.env['sale.order'].search(
            [('delivery_zone_id', '=', self.id),
             ('state', '!=', 'draft'),
             ('date_order', '>=', datetime.combine(self.date, datetime.min.time())),
             ('date_order', '<=', datetime.combine(self.date, datetime.max.time()))]
        )

    @api.multi
    def get_pickings_today(self):
        return self.env['stock.picking'].search(
            [('delivery_zone_id', '=', self.id),
             ('scheduled_date', '>=', datetime.combine(self.date, datetime.min.time())),
             ('scheduled_date', '<=', datetime.combine(self.date, datetime.max.time()))]
        )

    @api.multi
    def get_invoices_today(self):
        return self.env['account.invoice'].search(
            [('delivery_zone_id', '=', self.id),
             ('state', '!=', 'draft'),
             ('date_invoice', '=', self.date)]
        )

    @api.multi
    def get_payments_today(self):
        return self.env['account.payment'].search(
            [('delivery_zone_id', '=', self.id),
             ('payment_date', '=', self.date)]
        )

