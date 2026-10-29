from odoo import api, models

from ..tools.errors import XtdAiDraftOnlyError

# Fields whose modification on an existing partner is blocked during an AI run.
_PROTECTED = [
    "name",
    "vat",
    "company_registry",
    "email",
    "phone",
    "mobile",
    "website",
    "street",
    "street2",
    "zip",
    "city",
    "state_id",
    "country_id",
    "active",
    "bank_ids",
    "parent_id",
    "company_name",
    "type",
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    _xtd_ai_protected_partner_fields = _PROTECTED

    @api.model_create_multi
    def create(self, vals_list):
        # Creating a child contact makes the ORM sync commercial fields with a
        # write() on the new record: that internal write must not be blocked.
        return (
            super(ResPartner, self.with_context(_xtd_ai_partner_create=True))
            .create(vals_list)
            .with_env(self.env)
        )

    def write(self, vals):
        ctx = self.env.context
        if ctx.get("xtd_ai_run") and not ctx.get("_xtd_ai_partner_create"):
            blocked = [f for f in vals if f in self._xtd_ai_protected_partner_fields]
            if blocked and self:
                raise XtdAiDraftOnlyError(
                    self.env._(
                        "El agente IA no puede modificar contactos existentes (%s).",
                        ", ".join(blocked),
                    )
                )
        return super().write(vals)

    def unlink(self):
        # Deliberate: the draft-only guard must refuse deletion during an AI run.
        # pylint: disable=no-raise-unlink
        if self and self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._("El agente IA no puede borrar contactos.")
            )
        return super().unlink()
