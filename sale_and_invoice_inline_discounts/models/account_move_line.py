from odoo import api, fields, models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    account_line_discount_ids = fields.Many2many(string="Inline Discount", comodel_name='sale.inline.discount'
                                          )

    @api.onchange('account_line_discount_ids')
    def onchange_account_discount_global_ids(self):
        percentage = 0.00
        for discount in self.account_line_discount_ids:
            percentage += discount.percentage
        self.discount = percentage

