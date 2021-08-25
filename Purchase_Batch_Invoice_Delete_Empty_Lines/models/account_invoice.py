# -- coding: utf-8 --
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare

class AccountInvoice(models.Model):
   _inherit = 'account.invoice'
   def _prepare_invoice_line_from_po_line(self, line):
       if line.product_id.purchase_method == 'purchase':
           qty = line.product_qty - line.qty_invoiced
       else:
           qty = line.qty_received - line.qty_invoiced
       if float_compare(qty, 0.0, precision_rounding=line.product_uom.rounding) <= 0:
           qty = 0.0
           return {}
       taxes = line.taxes_id
       invoice_line_tax_ids = line.order_id.fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
       invoice_line = self.env['account.invoice.line']
       date = self.date or self.date_invoice
       data = {
           'purchase_line_id': line.id,
           'name': line.order_id.name + ': ' + line.name,
           'origin': line.order_id.origin,
           'uom_id': line.product_uom.id,
           'product_id': line.product_id.id,
           'account_id': invoice_line.with_context({'journal_id': self.journal_id.id, 'type': 'in_invoice'})._default_account(),
           'price_unit': line.order_id.currency_id._convert(
               line.price_unit, self.currency_id, line.company_id, date or fields.Date.today(), round=False),
           'quantity': qty,
           'discount': 0.0,
           'account_analytic_id': line.account_analytic_id.id,
           'analytic_tag_ids': line.analytic_tag_ids.ids,
           'invoice_line_tax_ids': invoice_line_tax_ids.ids
       }
       account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, line.order_id.fiscal_position_id, self.env.user.company_id)
       if account:
           data['account_id'] = account.id
       return data
   # Load all unsold PO lines
   @api.onchange('purchase_id')
   def purchase_order_change(self):
       if not self.purchase_id:
           return {}
       if not self.partner_id:
           self.partner_id = self.purchase_id.partner_id.id
       vendor_ref = self.purchase_id.partner_ref
       if vendor_ref and (not self.reference or (
               vendor_ref + ", " not in self.reference and not self.reference.endswith(vendor_ref))):
           self.reference = ", ".join([self.reference, vendor_ref]) if self.reference else vendor_ref
       if not self.invoice_line_ids:
           #as there's no invoice line yet, we keep the currency of the PO
           self.currency_id = self.purchase_id.currency_id
       new_lines = self.env['account.invoice.line']
       for line in self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id'):
           data = self._prepare_invoice_line_from_po_line(line)
           if data != {}:
               new_line = new_lines.new(data)
               new_line._set_additional_fields(self)
               new_lines += new_line
       self.invoice_line_ids += new_lines
       self.payment_term_id = self.purchase_id.payment_term_id
       self.env.context = dict(self.env.context, from_purchase_order_change=True)
       self.purchase_id = False
       return {}
