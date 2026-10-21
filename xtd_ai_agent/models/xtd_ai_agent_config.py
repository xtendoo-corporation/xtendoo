import json
import logging
import os

from odoo import api, models, tools
from odoo.exceptions import AccessError

from ..agent.errors import AgentError, ProviderNotConfigured
from ..agent.pricing import DEFAULT_PRICES, parse_price_table
from ..agent.types import LLMRequest, Message
from ..providers import PROVIDERS, ProviderSettings, build_provider

_logger = logging.getLogger(__name__)

PARAM = "xtd_ai_agent."
KEY_PARAM = PARAM + "anthropic_api_key"
KEY_ENV = "ANTHROPIC_API_KEY"
WORKSPACE_ENV = "ANTHROPIC_WORKSPACE_ID"
DEFAULT_MODEL = "claude-haiku-5-5"
EFFORTS = ("low", "medium", "high", "xhigh", "max")


class XtdAiAgentConfig(models.AbstractModel):
    """Settings of the in-process agent. Reads use sudo: parameters are system-only."""

    _name = "xtd.ai.agent.config"
    _description = "AI agent in-process configuration"

    @api.model
    def _xtd_ai_param(self, name, default=""):
        # sudo: system parameters, only the agent code reads them
        value = self.env["ir.config_parameter"].sudo().get_param(PARAM + name)
        return value if value not in (None, False, "") else default

    # -- API key -----------------------------------------------------------
    @api.model
    def _xtd_ai_api_key(self):
        """The Anthropic key: the environment variable wins over the parameter."""
        env_key = (os.environ.get(KEY_ENV) or "").strip()
        if env_key:
            return env_key
        # sudo: system parameter
        return (
            self.env["ir.config_parameter"].sudo().get_param(KEY_PARAM) or ""
        ).strip()

    @api.model
    def _xtd_ai_api_key_state(self):
        """``{"set": bool, "from_env": bool}``. Never the key itself."""
        from_env = bool((os.environ.get(KEY_ENV) or "").strip())
        stored = bool(self.env["ir.config_parameter"].sudo().get_param(KEY_PARAM))
        return {"set": from_env or stored, "from_env": from_env}

    # -- provider ----------------------------------------------------------
    @api.model
    def _xtd_ai_provider_settings(self, **overrides):
        provider = self._xtd_ai_param("provider", "anthropic")
        if provider not in PROVIDERS:
            provider = "anthropic"
        effort = self._xtd_ai_param("effort", "low")
        try:
            timeout = float(self._xtd_ai_param("timeout", 30.0))
        except ValueError:
            timeout = 30.0
        values = {
            "provider": provider,
            "model": self._xtd_ai_param("model", DEFAULT_MODEL),
            "effort": effort if effort in EFFORTS else "low",
            "timeout": timeout if timeout > 0 else 30.0,
            # Ajustes first; the container environment as a fallback (Doodba deploys)
            "workspace_id": self._xtd_ai_param("workspace_id", "")
            or (os.environ.get(WORKSPACE_ENV) or "").strip(),
            "log_error_details": self._xtd_ai_param("log_error_details", "")
            in (
                "True",
                "true",
                "1",
            ),
            "api_key": self._xtd_ai_api_key(),
            "fake_script": self._xtd_ai_param("fake_script", ""),
        }
        values.update(overrides)
        return ProviderSettings(**values)

    @api.model
    def _xtd_ai_build_provider(self, settings=None):
        """Hook (tests replace it). Raises ``ProviderNotConfigured``."""
        return build_provider(settings or self._xtd_ai_provider_settings())

    @api.model
    def _xtd_ai_config_error(self):
        """Spanish message when the agent cannot run, else ``False``."""
        try:
            settings = self._xtd_ai_provider_settings()
            if settings.provider == "anthropic" and not settings.api_key:
                raise ProviderNotConfigured("no key")
            if settings.provider == "fake" and not settings.fake_script:
                raise ProviderNotConfigured("no script")
        except ProviderNotConfigured:
            return self.env._(
                "El agente IA no está configurado: falta la clave de Anthropic. "
                "Un administrador debe indicarla en Ajustes → Agente IA."
            )
        return False

    # -- prices ------------------------------------------------------------
    @api.model
    def _xtd_ai_prices(self):
        prices = DEFAULT_PRICES.copy()
        raw = self._xtd_ai_param("prices_json", "")
        if raw:
            try:
                prices.update(parse_price_table(json.loads(raw)))
            except (ValueError, TypeError):
                _logger.warning("Invalid xtd_ai_agent.prices_json: using defaults")
        return prices

    @api.model
    def _xtd_ai_default_prices_json(self):
        return json.dumps(
            {
                model: {
                    k: v
                    for k, v in (
                        ("input", p.input),
                        ("output", p.output),
                        ("cache_read", p.cache_read),
                        ("cache_write", p.cache_write),
                    )
                    if v is not None
                }
                for model, p in DEFAULT_PRICES.items()
            },
            indent=2,
        )

    # -- job runner --------------------------------------------------------
    @api.model
    def _xtd_ai_jobrunner_active(self):
        """True when the queue_job runner is loaded (``server_wide_modules``)."""
        modules = tools.config["server_wide_modules"] or []
        if isinstance(modules, str):
            modules = modules.split(",")
        return "queue_job" in [m.strip() for m in modules]

    # -- connection test ---------------------------------------------------
    @api.model
    def _xtd_ai_test_connection(self):
        """One tiny request, no business data. Returns ``(ok, message)``."""
        if not self.env.su and not self.env.user.has_group("base.group_system"):
            raise AccessError(self.env._("Solo los administradores del sistema."))
        try:
            settings = self._xtd_ai_provider_settings(max_tokens=16)
            provider = self._xtd_ai_build_provider(settings)
        except ProviderNotConfigured:
            return False, self._xtd_ai_config_error() or self.env._(
                "El proveedor no está configurado."
            )
        try:
            response = provider.complete(
                LLMRequest(
                    system="Responde solo con la palabra OK.",
                    tools=(),
                    messages=(Message(role="user", text="Prueba de conexión."),),
                )
            )
        except AgentError as exc:
            return False, self.env._("Error de conexión: %s", str(exc))
        except Exception as exc:  # noqa: BLE001 - shown to the admin, type only
            return False, self.env._(
                "Error inesperado en la conexión: %s", type(exc).__name__
            )
        return True, self.env._(
            "Conexión correcta con %(provider)s (modelo %(model)s).",
            provider=provider.name,
            model=response.model or provider.model,
        )
