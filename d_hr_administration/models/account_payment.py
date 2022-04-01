# -- coding: utf-8 --
from odoo import api, models, fields
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = ['account.payment', 'administrator.mixin.rule']
    _name = "account.payment"

    lock_date = fields.Boolean(
        string="Lock date",
        compute='_set_lock_date',
    )

    def _get_lock_date(self):
        return not self.env["res.users"].has_group(
            "d_hr_administration.administration"
        )
    def _set_lock_date(self):
        self.lock_date = not self.env["res.users"].has_group(
            "d_hr_administration.administration"
        )

    @api.multi
    def cancel(self):
        if not self.env["res.users"].has_group(
                "d_hr_administration.administration"
        ):
            raise ValidationError(("No tiene permisos para cancelar Pagos"))
        res = super(AccountPayment, self).cancel()
        return res
