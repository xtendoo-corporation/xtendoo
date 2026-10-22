from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    xtd_ai_confirm_writes = fields.Boolean(
        string="Confirmar acciones del agente IA",
        default=True,
        help=(
            "Si está activo, el agente IA pide confirmación antes de crear borradores."
        ),
    )

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["xtd_ai_confirm_writes"]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["xtd_ai_confirm_writes"]

    @api.model
    def _xtd_ai_force_confirmation(self):
        # sudo: system parameter
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtd_ai.force_confirmation", "False")
        )
        return str(value).strip().lower() in ("1", "true", "yes")

    def _xtd_ai_needs_confirmation(self, kind):
        """Whether a write tool of ``kind`` needs confirmation for this user."""
        self.ensure_one()
        return (
            kind == "create"
            or self._xtd_ai_force_confirmation()
            or bool(
                self.sudo().xtd_ai_confirm_writes
            )  # sudo: own preference, always readable
        )
