# Copyright 2019 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

import logging


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice', 'invoice_id.date','discount2', 'discount3')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None

        # to avoid coupling these calculations must be passed to a method
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        price *= (1 - (self.discount2 or 0.0) / 100.0)
        price *= (1 - (self.discount3 or 0.0) / 100.0)

        logging.info('***************************** price **********************************')
        logging.info(price)

        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                          partner=self.invoice_id.partner_id)
        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            currency = self.invoice_id.currency_id
            date = self.invoice_id._get_currency_rate_date()
            price_subtotal_signed = currency._convert(price_subtotal_signed, self.invoice_id.company_id.currency_id,
                                                      self.company_id or self.env.user.company_id,
                                                      date or fields.Date.today())
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign

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
            price_unit = price
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id,
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