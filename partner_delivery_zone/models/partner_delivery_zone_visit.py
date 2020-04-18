# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from datetime import date


class PartnerDeliveryZoneVisit(models.Model):
    _name = 'partner.delivery.zone.visit'
    _description = 'Partner delivery zone visit'

    delivery_zone_id = fields.Many2one(
        'partner.delivery.zone',
        'Delivery Zone',
    )
    partner_id = fields.Many2one(
        'res.partner',
        'Partner',
    )
    date = fields.Datetime('Date Visit')
    sale_order_id = fields.Many2one(
        'sale.order',
        'Sale Order',
    )

    def get_visit_zone_today(self, delivery_zone_id):
        return self.search([('date', '=', date.today()), ('delivery_zone_id', '=', delivery_zone_id)])

    def get_partners_visit_today(self, delivery_zone_id):
        return self.get_visit_zone_today(delivery_zone_id).mapped(lambda x: x.partner_id.id)

    def create_if_not_exist(self, delivery_zone_id, partner_id):
        record = self.search(
            [('delivery_zone_id', '=', delivery_zone_id),
             ('partner_id', '=', partner_id),
             ('date', '=', date.today())])
        if record:
            return record

        record = self.create(
            [{'delivery_zone_id': delivery_zone_id,
              'partner_id': partner_id,
              'date': date.today()}])
        return record

    def write_sale_id(self, delivery_zone_id, partner_id, sale_id):
        for record in self.create_if_not_exist(delivery_zone_id, partner_id):
            record['sale_order_id'] = sale_id

