from odoo import fields, models

from .xtd_ai_policy import PROFILE_LABELS


class ResCompany(models.Model):
    _inherit = "res.company"

    # Empty: the global parameter of waves 1A/1B applies (Equilibrado by default)
    xtd_ai_profile = fields.Selection(
        list(PROFILE_LABELS.items()),
        string="Perfil del agente IA",
    )
    xtd_ai_discount_threshold = fields.Float(
        string="Descuento máximo sin tarjeta (%)",
        help="Por encima de este descuento de línea, el cambio pide tarjeta.",
    )
    xtd_ai_purchase_confirm_limit = fields.Float(
        string="Importe máximo de compra con tarjeta simple",
    )
    xtd_ai_policy_rule_ids = fields.One2many(
        "xtd.ai.policy.rule", "company_id", string="Tabla de políticas del agente IA"
    )
