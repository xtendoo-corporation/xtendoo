# Copyright 2017 Tecnativa - David Vidal
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue

            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            price = price * (1 - (line.discount2 or 0.0) / 100.0)
            price = price * (1 - (line.discount3 or 0.0) / 100.0)

            taxes = line.invoice_line_tax_ids.compute_all(price, self.currency_id, line.quantity, line.product_id,
                                                          self.partner_id)['taxes']

            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['base'] = round_curr(val['base'])
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])
        return tax_grouped


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    discount2 = fields.Float(
        'Discount 2 (%)',
        digits=dp.get_precision('Discount'),
    )
    discount3 = fields.Float(
        'Discount 3 (%)',
        digits=dp.get_precision('Discount'),
    )

    @api.multi
    @api.depends('discount2', 'discount3')
    def _compute_price(self):
        for line in self:
            prev_price_unit = line.price_unit
            prev_discount = line.discount
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            price_unit *= (1 - (line.discount2 or 0.0) / 100.0)
            price_unit *= (1 - (line.discount3 or 0.0) / 100.0)
            line.update({
                'price_unit': price_unit,
                'discount': 0.0,
            })
            super(AccountInvoiceLine, line)._compute_price()
            line.update({
                'price_unit': prev_price_unit,
                'discount': prev_discount,
            })
