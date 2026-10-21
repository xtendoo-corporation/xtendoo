from odoo import fields, models
from odoo.exceptions import AccessError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xtd_ai_force_confirmation = fields.Boolean(
        string="Confirmación obligatoria para todos",
        config_parameter="xtd_ai_gateway.force_confirmation",
        help="Obliga a confirmar todas las acciones del agente IA, "
        "aunque el usuario lo tenga desactivado.",
    )
    xtd_ai_audit_retention_days = fields.Integer(
        string="Retención de la auditoría (días)",
        config_parameter="xtd_ai_gateway.audit_retention_days",
        default=365,
    )

    def action_xtd_ai_rotate_secret(self):
        if not self.env.user.has_group("xtd_ai_gateway.group_xtd_ai_manager"):
            raise AccessError(
                self.env._("Solo el administrador del agente IA puede hacerlo.")
            )
        self.env["xtd.ai.token"]._xtd_ai_rotate_secret()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Agente IA"),
                "message": self.env._(
                    "Clave rotada: las ejecuciones en curso dejan de ser válidas."
                ),
                "type": "success",
                "sticky": False,
            },
        }
