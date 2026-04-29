from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PosCashMoveWizard(models.TransientModel):
    _name = "pos.cash.move.wizard"
    _description = "POS Cash Move Wizard"

    def _default_session(self):
        # Devuelve la sesión abierta si solo hay una, si no hay ninguna devuelve False
        sessions = self.env['pos.session'].search([('state', '=', 'opened')])
        if len(sessions) == 1:
            return sessions.id
        return False

    session_id = fields.Many2one(
        "pos.session",
        string="Sesión TPV",
        domain="[('state', '=', 'opened')]",
        required=True,
        default=_default_session,
        help="Selecciona la sesión de TPV abierta sobre la que realizar el movimiento. Si solo hay una, se selecciona automáticamente."
    )
    move_type = fields.Selection(
        [("in", "Entrada de dinero (Cash In)"), ("out", "Salida de dinero (Cash Out)")],
        string="Tipo de Movimiento",
        required=True,
        default="in",
    )
    amount = fields.Monetary(string="Importe", required=True)
    reason = fields.Char(string="Motivo", required=True)
    currency_id = fields.Many2one(
        related="session_id.currency_id",
        store=False,
        readonly=True,
    )

    def action_confirm(self):
        self.ensure_one()
        if self.session_id.state != 'opened':
            raise UserError(_("La sesión seleccionada debe estar abierta para realizar un movimiento de caja."))
        if self.amount <= 0:
            raise UserError(_("El importe debe ser mayor que cero."))
        try:
            self.session_id.try_cash_in_out(
                self.move_type,
                self.amount,
                self.reason,
                None,
                extras={}
            )
        except AttributeError:
            raise UserError(_("El método nativo try_cash_in_out no está disponible en esta versión."))
        return {'type': 'ir.actions.act_window_close'}
