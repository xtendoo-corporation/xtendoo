# -- coding: utf-8 --
from odoo import api, models, fields, _


class AccountPayment(models.Model):
    _inherit = "account.payment"


    lock_date = fields.Boolean(
        string="Lock date",
        default=lambda self: self._get_lock_date()
    )

    def _get_lock_date(self):
        return not self.env.user.create_direct_invoice


