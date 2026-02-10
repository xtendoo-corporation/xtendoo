from odoo import api, fields, models


class PosSessionClosingPaymentLine(models.TransientModel):
    _name = "pos.session.closing.payment.line"
    _description = "Línea de método de pago en cierre de sesión"

    wizard_id = fields.Many2one(
        "pos.session.closing.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade"
    )
    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Método de pago",
        required=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="wizard_id.currency_id",
        readonly=True
    )
    amount_expected = fields.Monetary(
        string="Esperado",
        currency_field="currency_id",
        readonly=True,
        help="Total esperado según los pagos registrados"
    )
    amount_counted = fields.Monetary(
        string="Contado",
        currency_field="currency_id",
        help="Importe contado/introducido por el usuario"
    )
    difference = fields.Monetary(
        string="Diferencia",
        currency_field="currency_id",
        compute="_compute_difference",
        store=True,
        help="Diferencia entre el importe contado y el esperado"
    )
    is_cash = fields.Boolean(
        related="payment_method_id.is_cash_count",
        string="Es efectivo",
        readonly=True
    )
    payment_method_name = fields.Char(
        related="payment_method_id.name",
        string="Nombre del método",
        readonly=True
    )

    @api.depends("amount_counted", "amount_expected")
    def _compute_difference(self):
        for line in self:
            line.difference = line.amount_counted - line.amount_expected

