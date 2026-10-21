import json

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from ..agent.pricing import parse_price_table
from ..providers import PROVIDERS
from .xtd_ai_agent_config import DEFAULT_MODEL, EFFORTS, KEY_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xtd_ai_agent_provider = fields.Selection(
        [("anthropic", "Anthropic"), ("fake", "Simulado (pruebas)")],
        string="Proveedor",
        default="anthropic",
        config_parameter="xtd_ai_agent.provider",
    )
    xtd_ai_agent_model = fields.Char(
        string="Modelo",
        default=DEFAULT_MODEL,
        config_parameter="xtd_ai_agent.model",
    )
    xtd_ai_agent_effort = fields.Selection(
        [(e, e) for e in EFFORTS],
        string="Esfuerzo",
        default="low",
        config_parameter="xtd_ai_agent.effort",
    )
    xtd_ai_agent_timeout = fields.Float(
        string="Timeout por llamada (s)",
        default=30.0,
        config_parameter="xtd_ai_agent.timeout",
    )
    xtd_ai_agent_workspace_id = fields.Char(
        string="Workspace de Anthropic",
        config_parameter="xtd_ai_agent.workspace_id",
    )
    xtd_ai_agent_log_error_details = fields.Boolean(
        string="Registrar el detalle de los errores 400",
        config_parameter="xtd_ai_agent.log_error_details",
    )
    xtd_ai_agent_prices_json = fields.Char(
        string="Tabla de precios (JSON)",
        config_parameter="xtd_ai_agent.prices_json",
        help="USD por millón de tokens: "
        '{"modelo": {"input": 1.0, "output": 5.0, "cache_read": 0.1}}',
    )
    # The key is write-only and never stored in the transient table: the field
    # is not stored, its inverse writes the system parameter. Reading returns
    # nothing, so the key never goes back to the browser.
    xtd_ai_agent_api_key_input = fields.Char(
        string="Clave de Anthropic",
        compute="_compute_xtd_ai_agent_api_key_input",
        inverse="_inverse_xtd_ai_agent_api_key_input",
        store=False,
    )
    xtd_ai_agent_api_key_set = fields.Boolean(
        compute="_compute_xtd_ai_agent_status", store=False
    )
    xtd_ai_agent_api_key_env = fields.Boolean(
        compute="_compute_xtd_ai_agent_status", store=False
    )
    xtd_ai_agent_jobrunner_active = fields.Boolean(
        compute="_compute_xtd_ai_agent_status", store=False
    )

    def _compute_xtd_ai_agent_api_key_input(self):
        for record in self:
            record.xtd_ai_agent_api_key_input = False

    def _inverse_xtd_ai_agent_api_key_input(self):
        for record in self:
            value = (record.xtd_ai_agent_api_key_input or "").strip()
            if not value:
                continue
            self._xtd_ai_agent_check_admin()
            # sudo: system parameter, the caller is a system administrator
            self.env["ir.config_parameter"].sudo().set_param(KEY_PARAM, value)
        # drop the typed value from the cache so reads (web_save) return nothing
        self.invalidate_recordset(["xtd_ai_agent_api_key_input"])

    @api.depends_context("uid")
    def _compute_xtd_ai_agent_status(self):
        config = self.env["xtd.ai.agent.config"]
        state = config._xtd_ai_api_key_state()
        for record in self:
            record.xtd_ai_agent_api_key_set = state["set"]
            record.xtd_ai_agent_api_key_env = state["from_env"]
            record.xtd_ai_agent_jobrunner_active = config._xtd_ai_jobrunner_active()

    def _xtd_ai_agent_check_admin(self):
        if not self.env.su and not self.env.user.has_group("base.group_system"):
            raise AccessError(
                self.env._("Solo los administradores del sistema pueden hacerlo.")
            )

    def set_values(self):
        res = super().set_values()
        raw = (self.xtd_ai_agent_prices_json or "").strip()
        if raw:
            try:
                parse_price_table(json.loads(raw))
            except (ValueError, TypeError, AttributeError):
                raise UserError(
                    self.env._("La tabla de precios no es un JSON válido.")
                ) from None
        if self.xtd_ai_agent_provider not in PROVIDERS:
            raise UserError(self.env._("Proveedor no válido."))
        return res

    def action_xtd_ai_agent_clear_key(self):
        self._xtd_ai_agent_check_admin()
        # sudo: system parameter, the caller is a system administrator
        self.env["ir.config_parameter"].sudo().set_param(KEY_PARAM, False)
        return self._xtd_ai_agent_notify(self.env._("Clave borrada."), "success")

    def action_xtd_ai_agent_test_connection(self):
        self._xtd_ai_agent_check_admin()
        ok, message = self.env["xtd.ai.agent.config"]._xtd_ai_test_connection()
        return self._xtd_ai_agent_notify(message, "success" if ok else "danger")

    def _xtd_ai_agent_notify(self, message, kind):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Agente IA"),
                "message": message,
                "type": kind,
                "sticky": kind != "success",
            },
        }
