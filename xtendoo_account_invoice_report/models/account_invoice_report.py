from odoo import models, fields, api

class AccountInvoiceReportExtended(models.Model):
    _inherit = "account.invoice.report"

    price_unit = fields.Float(string='Precio unitario', readonly=True)
    discount = fields.Float(string='Descuento (%)', readonly=True)

    @api.model
    def _select(self):
        return super(AccountInvoiceReportExtended, self)._select() + '''
            , line.price_unit
            , line.discount
        '''
