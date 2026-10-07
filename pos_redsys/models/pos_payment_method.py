from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [("redsys", "Redsys")]

    redsys_merchant_code = fields.Char(
        string="Redsys merchant code",
        help="Merchant code (FUC) shown in canales.redsys.es.",
        copy=False,
    )
    redsys_terminal_number = fields.Char(
        string="Redsys terminal number",
        default="1",
        copy=False,
    )
    redsys_agent_url = fields.Char(
        string="Redsys local agent URL",
        default="http://localhost:8765",
        help="URL, reachable from the cashier's browser, of the program that "
        "talks to the Redsys TPV-PC installed on the POS computer.",
        copy=False,
    )
    redsys_test_mode = fields.Boolean(
        string="Redsys test mode",
        help="Run transactions in the Redsys test environment.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += [
            "redsys_merchant_code",
            "redsys_terminal_number",
            "redsys_agent_url",
            "redsys_test_mode",
        ]
        return params
