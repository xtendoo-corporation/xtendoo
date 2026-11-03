from odoo import api, models

from odoo.addons.xtd_ai.tools.errors import XtdAiToolError

SALES_MANAGER_GROUP = "sales_team.group_sale_manager"


class XtdAiRecordRegistry(models.AbstractModel):
    _inherit = "xtd.ai.record.registry"

    @api.model
    def _xtd_ai_record_specs(self):
        specs = super()._xtd_ai_record_specs()
        specs["crm.lead"] = {
            "label": self.env._("oportunidad"),
            "skill": "crm",
            # creation stays in create_opportunity (first stage, salesperson)
            "create": False,
            "update": True,
            # open opportunities only: won and lost (archived) ones are history
            "domain": [
                ("type", "=", "opportunity"),
                ("active", "=", True),
                ("stage_id.is_won", "=", False),
            ],
            "chatter": True,
            "external": "_xtd_ai_external_crm_lead",
            "check": "_xtd_ai_check_crm_lead",
            "effects": "_xtd_ai_effects_crm_lead",
            "fields": {
                "name": {"label": self.env._("Nombre"), "risk": "low"},
                "description": {"label": self.env._("Notas"), "risk": "low"},
                "probability": {"label": self.env._("Probabilidad"), "risk": "low"},
                # forecast and commissions read it: card with before -> after
                "expected_revenue": {
                    "label": self.env._("Ingreso esperado"),
                    "risk": "money",
                },
                "date_deadline": {
                    "label": self.env._("Cierre previsto"),
                    "risk": "low",
                },
                "tag_ids": {"label": self.env._("Etiquetas"), "risk": "low"},
                "priority": {"label": self.env._("Prioridad"), "risk": "low"},
                "user_id": {
                    "label": self.env._("Comercial"),
                    "risk": "low",
                    "domain": [("share", "=", False), ("active", "=", True)],
                },
                "team_id": {"label": self.env._("Equipo de ventas"), "risk": "low"},
                # transitions have their own tools (cards); identity of the
                # customer and its contact data are not edited here
                "stage_id": {"risk": "forbidden"},
                "active": {"risk": "forbidden"},
                "lost_reason_id": {"risk": "forbidden"},
                "partner_id": {"risk": "forbidden"},
                "email_from": {"risk": "forbidden"},
                "type": {"risk": "forbidden"},
            },
        }
        return specs

    @api.model
    def _xtd_ai_external_crm_lead(self, lead):
        """Text of the lead written outside the company: a web form or portal
        user created it, it came from the website, or it has incoming emails."""
        if lead.create_uid.share:
            return True
        website = self.env.ref("utm.utm_medium_website", raise_if_not_found=False)
        if website and lead.medium_id == website:
            return True
        return any(
            message.message_type == "email"
            or (
                message.message_type == "comment"
                and message.author_id
                and not any(not user.share for user in message.author_id.user_ids)
            )
            for message in lead.message_ids
        )

    @api.model
    def _xtd_ai_check_crm_lead(self, lead, vals):
        probability = vals.get("probability")
        if probability is not None and not 0 < probability < 100:
            raise XtdAiToolError(
                "validation",
                self.env._(
                    "La probabilidad debe estar entre 1 y 99: 0 y 100 son perder o "
                    "ganar (close_opportunity)."
                ),
            )
        user_id = vals.get("user_id")
        if (
            user_id
            and user_id != self.env.uid
            and not self.env.user.has_group(SALES_MANAGER_GROUP)
        ):
            raise XtdAiToolError(
                "forbidden",
                self.env._(
                    "Solo un responsable de ventas puede asignar oportunidades a "
                    "otro comercial."
                ),
            )

    @api.model
    def _xtd_ai_effects_crm_lead(self, lead, vals):
        effects = []
        if lead and "expected_revenue" in vals:
            effects.append(
                self.env._("Cambia la previsión del pipeline y el ingreso ponderado.")
            )
        return effects
