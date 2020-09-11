# -- coding: utf-8 --
from odoo import api, models, fields
from odoo.exceptions import ValidationError

class AccountPayment(models.Model):
    _inherit = "account.payment"


    lock_date = fields.Boolean(
        string="Lock date",
        default=lambda self: self._get_lock_date()
    )

    def _get_lock_date(self):
        return not self.env.user.administration

    @api.multi
    def cancel(self):
        if not self.env.user.administration:
            raise ValidationError(("No tiene permisos para cancelar Pagos"))
        res = super(AccountPayment, self).cancel()
        return res


