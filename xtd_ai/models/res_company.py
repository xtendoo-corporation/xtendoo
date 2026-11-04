from odoo import fields, models

from .xtd_ai_policy import PROFILE_LABELS


class ResCompany(models.Model):
    _inherit = "res.company"

    # Empty: the global parameter of waves 1A/1B applies (Equilibrado by default)
    xtd_ai_profile = fields.Selection(
        list(PROFILE_LABELS.items()),
        string="Perfil del agente IA",
    )
    # Always filled (default and migration): 0 is a real value, «any discount
    # asks for a card», not «empty, use the 15 %».
    xtd_ai_discount_threshold = fields.Float(
        string="Descuento máximo sin tarjeta (%)",
        default=lambda self: self.env[
            "xtd.ai.policy"
        ]._xtd_ai_default_discount_threshold(),
        help="Por encima de este descuento de línea, crear o cambiar la línea "
        "pide tarjeta. 0: cualquier descuento pide tarjeta.",
    )
    xtd_ai_policy_rule_ids = fields.One2many(
        "xtd.ai.policy.rule", "company_id", string="Tabla de políticas del agente IA"
    )

    # -- safety brakes (ANALISIS_PERMISOS §6.4) --------------------------------
    xtd_ai_paused = fields.Boolean(
        string="Agente IA en pausa",
        help="Nadie puede usar el agente en esta compañía hasta que se reactive.",
    )
    xtd_ai_max_writes_hour = fields.Integer(
        string="Escrituras por hora y usuario",
        default=60,
        help="Acciones del agente (hechas o en tarjeta) por usuario en una hora. "
        "0: sin límite.",
    )
    xtd_ai_max_writes_message = fields.Integer(
        string="Escrituras por mensaje",
        default=15,
        help="Acciones del agente en la respuesta a un mismo mensaje. 0: sin límite.",
    )
    xtd_ai_fiscal_brake = fields.Boolean(
        string="Veri*Factu, SII o TicketBAI activo",
        compute="_compute_xtd_ai_fiscal_brake",
        help="Publicar o enviar facturas queda siempre en manos del usuario (N3).",
    )

    def _compute_xtd_ai_fiscal_brake(self):
        for company in self:
            company.xtd_ai_fiscal_brake = company._xtd_ai_has_fiscal_reporting()

    def _xtd_ai_has_fiscal_reporting(self):
        """The company reports invoices to the tax agency (Veri*Factu, SII or
        TicketBAI): whatever the profile, publishing or sending invoices is N3."""
        self.ensure_one()
        checks = (
            ("l10n_es_edi_verifactu_required", bool),
            ("l10n_es_sii_tax_agency", bool),
            ("l10n_es_tbai_is_enabled", bool),
        )
        return any(name in self._fields and test(self[name]) for name, test in checks)
