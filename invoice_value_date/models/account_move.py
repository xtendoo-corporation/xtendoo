# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_default_date(self):
        return fields.Date.from_string(fields.Date.today())

    date_value = fields.Date(
        string='Date Value',
        help="Keep empty to use the current date",
        copy=False,
    )

    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        if vals['type'] == 'out_refund':
            date = self._get_invoice_date(vals)
        else:
            date = self._get_sale_order_date(vals)
        if date:
            res.write({'date_value': date})
        return res

    def _get_sale_order_date(self, vals):
        sale_order_date = None
        if not vals['invoice_origin']:
            return sale_order_date
        for origin in vals['invoice_origin'].split(', '):
            sale_order = self.env['sale.order'].search([('name', '=', origin)], limit=1)
            if sale_order and (sale_order_date is None or sale_order.date_order > sale_order_date):
                sale_order_date = sale_order.date_order
        return sale_order_date

    def _get_invoice_date(self, vals):
        if vals['invoice_date']:
            return vals['invoice_date']
        return None
