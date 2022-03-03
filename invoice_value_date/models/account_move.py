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
        compute="_get_default_value_date",
        store=True,
    )

    @api.model
    def create(self, vals):
        date = False
        print("*"*80)
        print(vals)
        # if vals['type']:
        if vals.get('type'):
            if vals['type'] == 'out_refund':
                date = self._get_invoice_date(vals)
            else:
                date = self._get_sale_order_date(vals)
        if date is not False:
            vals['date_value'] = date
        res = super(AccountMove, self).create(vals)
        return res

    def _get_sale_order_date(self, vals):
        sale_order_date = None
        if not vals.get('invoice_origin'):
            return sale_order_date
        for origin in vals['invoice_origin'].split(', '):
            sale_order = self.env['sale.order'].search([('name', '=', origin)], limit=1)
            if sale_order and (sale_order_date is None or sale_order.date_order.date() > sale_order_date):
                sale_order_date = sale_order.date_order.date()
        return sale_order_date

    def _get_default_value_date(self):
        for invoice in self:
            result_date = False
            if invoice.type == 'out_refund':
                result_date = invoice.invoice_date
            else:
                if invoice.invoice_origin is not False:
                    for origin in invoice.invoice_origin.split(', '):
                        sale_order = self.env['sale.order'].search([('name', '=', origin)], limit=1)
                        if sale_order and (result_date is False or sale_order.date_order.date() > result_date):
                            result_date = sale_order.date_order.date()
                    if result_date is False:
                        result_date = invoice.invoice_date
                else:
                    result_date = invoice.invoice_date
            invoice.date_value = result_date

    def _get_invoice_date(self, vals):
        if vals['invoice_date']:
            return vals['invoice_date']
        return None
