from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    payment_method_line_id = fields.Many2one(string="Método de pago")
