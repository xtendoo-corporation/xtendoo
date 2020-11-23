from odoo import api, fields, models, _
from datetime import date
import logging


class PartnerVisitLine(models.Model):
    _name = "partner.visit.line"
    _description = "Partner Visit Lines"

    user_id = fields.Many2one('res.users', 'User')
    partner_id = fields.Many2one('res.partner', 'Partner')
    date = fields.Datetime('Date Visit')
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')

    def get_partner_user_today(self):
        return self.search([('date', '=', date.today()), ('user_id', '=', self.env.user.id)])

    def create_if_not_exist(self, partner_id):
        record = self.search(
                [('date', '=', date.today()), ('user_id', '=', self.env.user.id), ('partner_id', '=', partner_id)])
        if record:
            return record

        record = self.create([{'user_id': self.env.user.id, 'partner_id': partner_id, 'date': date.today()}])
        self.env["partner.visit"].calculate_next_visit_depend_period(partner_id)

        return record

    def write_sale_id(self, sale_id, partner_id):
        for record in self.create_if_not_exist(partner_id):
            record['sale_order_id'] = sale_id