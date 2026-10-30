from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    xtd_ai_confirm_writes = fields.Boolean(
        string="Confirmar acciones del agente IA",
        # Balanced profile (ANALISIS_PERMISOS 6.1): drafts and low-risk edits are
        # done with "Deshacer"; a user may harden it to always get a card.
        default=False,
        help=(
            "Si está activo, el agente IA pide confirmación con una tarjeta para "
            "todo lo que escribe, también borradores y cambios de bajo riesgo."
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
