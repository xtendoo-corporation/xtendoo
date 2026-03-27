from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PosSessionPinWizard(models.TransientModel):
    _name = "pos.session.pin.wizard"
    _description = "Wizard para validar PIN de apertura POS"

    session_id = fields.Many2one("pos.session", required=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", required=True, readonly=True, default=lambda self: self.env.user
    )
    pos_pin = fields.Char(string="PIN del usuario")

    def action_validate_pin(self):
        self.ensure_one()

        # Buscar usuario por PIN
        user = self.env["res.users"].search(
            [
                ("pin", "=", self.pos_pin),
                "|",
                ("company_id", "=", self.session_id.company_id.id),
                ("company_id", "=", False),
            ],
            limit=1,
        )

        if not user:
            raise ValidationError(
                _(
                    "PIN incorrecto o usuario no encontrado. "
                    "Por favor, verifique su PIN e intente nuevamente."
                )
            )

        # Actualizamos la sesión con el nuevo usuario si es necesario
        self.session_id.sudo().write({"user_id": user.id})

        # --- FLOW 1: Cambio de usuario tras venta ---
        if self.env.context.get("switch_user_after_sale"):
            return {
                "type": "ir.actions.client",
                "tag": "pos_conventional_new_order",
                "params": {
                    "default_session_id": self.session_id.id,
                    "default_user_id": user.id,
                },
            }

        # --- FLOW 2: Apertura de nuevo pedido con PIN obligatorio ---
        if self.env.context.get("force_new_order_flow"):
            return {
                "type": "ir.actions.act_window",
                "res_model": "pos.order",
                "view_mode": "form",
                "target": "current",
                "context": {
                    "default_session_id": self.session_id.id,
                    "default_user_id": user.id,
                    "pos_conventional_pin_validated": True,
                },
            }

        # Validar en el opening wizard si vinimos de ahí
        self.env["pos.session.opening.wizard"]._validate_user_pin(
            {
                "session_id": self.session_id,
                "user_id": user,
                "pos_pin": self.pos_pin,
            }
        )

        # Al validar, abrir el popup de apertura OWL
        return {
            "type": "ir.actions.client",
            "tag": "pos_conventional_opening_popup",
            "name": _("Control de apertura"),
            "target": "new",
            "context": {
                "session_id": self.session_id.id,
                "config_id": self.session_id.config_id.id,
            },
        }
