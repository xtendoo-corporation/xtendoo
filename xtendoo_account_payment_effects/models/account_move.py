from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_invoice_in_payment_state(self):
        # Core hook (account/models/account_move.py): "this method will be
        # overridden in the accountant module to enable the 'in_payment' state".
        # We provide our own minimal override so invoices stay "En proceso de
        # pago" between payment registration and remesa confirmation, without
        # depending on OCA or Enterprise.
        return "in_payment"
