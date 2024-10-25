from odoo import models, fields, api


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    shipping_partner_id = fields.Many2one('res.partner', string='Dirección de entrega', readonly=True)

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + ", sub.partner_shipping_id as shipping_partner_id"

    def _sub_select(self):
        return super(AccountInvoiceReport, self)._sub_select() + ", ai.partner_shipping_id as partner_shipping_id"

    def _group_by(self):
        return super(AccountInvoiceReport, self)._group_by() + ", ai.partner_shipping_id"
