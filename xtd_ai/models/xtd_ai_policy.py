"""Action levels of the agent (ANALISIS_PERMISOS §6.1): operation class × profile.

Levels: ``N0`` read, ``N1`` do it and offer "Deshacer", ``N2`` confirmation card,
``N3`` prepare and take the user to the screen, ``N4`` forbidden.

Per company (Ajustes > Agente IA):

- ``res.company.xtd_ai_profile``: ``prudent``, ``balanced`` (default) or ``agile``.
- ``xtd.ai.policy.rule`` (policy table): per operation class, a level that may
  harden the profile or relax it down to ``FLOOR`` (never below); per tool, a
  level that can only harden. ``FIXED`` classes (read, publish or post, pay,
  administration) are not editable: publishing stays N3 with no option.
- ``res.company.xtd_ai_discount_threshold`` / ``xtd_ai_purchase_confirm_limit``.

Compatibility with waves 1A/1B: when a company has no value of its own, the
``ir.config_parameter`` ``xtd_ai.policy.profile``, ``.discount_threshold`` and
``.purchase_confirm_limit`` still apply, and ``xtd_ai.policy.level.<op_class>``
still raises (never lowers) the level of every company.
"""

from datetime import timedelta

from odoo import api, fields, models

from ..tools.errors import XtdAiToolError

PARAM = "xtd_ai.policy."
LEVELS = ("N0", "N1", "N2", "N3", "N4")
PROFILES = ("prudent", "balanced", "agile")
DEFAULT_PROFILE = "balanced"
DEFAULT_DISCOUNT_THRESHOLD = 15.0
DEFAULT_PURCHASE_CONFIRM_LIMIT = 1000.0

# Operation classes: rows of the table of §6.1. Columns: prudent, balanced, agile.
# "agile" lowers money edits to N1 below the thresholds; that nuance belongs to
# wave 2 and is not offered yet (the table keeps it at N2).
POLICY_TABLE = {
    "read": ("N0", "N0", "N0"),
    "create_draft": ("N2", "N1", "N1"),
    "create_master": ("N2", "N1", "N1"),
    "edit_low": ("N2", "N1", "N1"),
    "edit_money": ("N2", "N2", "N2"),
    # anything a tool marks as legacy "always confirm" (kind="create")
    "confirm": ("N2", "N2", "N2"),
    "send_external": ("N3", "N2", "N2"),
    "transition": ("N3", "N3", "N2"),
    # internal transitions without documents or messages to third parties (move
    # an opportunity or a task between stages, mark an opportunity won or lost):
    # always a card, in every profile
    "transition_internal": ("N2", "N2", "N2"),
    "post": ("N3", "N3", "N3"),
    "payment": ("N4", "N4", "N4"),
    "admin": ("N4", "N4", "N4"),
}


# Operation classes nobody can edit: read, publish or post (always N3, user
# decision), payments and administration (N4, red lines of §5).
FIXED_CLASSES = frozenset({"read", "post", "payment", "admin"})
# Classes about publishing or sending documents: N3 under Veri*Factu / SII
FISCAL_CLASSES = frozenset({"post", "send_external", "transition"})
# The most an administrator can relax a class: the Ágil column of §6.1.
FLOOR = {op: row[PROFILES.index("agile")] for op, row in POLICY_TABLE.items()}

OP_CLASS_LABELS = {
    "read": "Leer",
    "create_draft": "Crear borrador de documento",
    "create_master": "Crear dato maestro (contacto, producto)",
    "edit_low": "Editar campos de bajo riesgo",
    "edit_money": "Editar precios, descuentos altos o impuestos",
    "confirm": "Acciones que siempre piden tarjeta",
    "send_external": "Enviar algo al exterior (correo)",
    "transition": "Transiciones con efectos (confirmar venta o compra, validar)",
    "transition_internal": "Transiciones internas (etapa, ganar o perder)",
    "post": "Publicar o contabilizar",
    "payment": "Pagar, remesas",
    "admin": "Administración",
}
LEVEL_LABELS = {
    "N0": "N0 Leer",
    "N1": "N1 Hacer con «Deshacer»",
    "N2": "N2 Tarjeta de confirmación",
    "N3": "N3 Preparar y llevar a la pantalla",
    "N4": "N4 Prohibido",
}
PROFILE_LABELS = {
    "prudent": "Prudente",
    "balanced": "Equilibrado",
    "agile": "Ágil",
}


def max_level(*levels):
    return max((lvl for lvl in levels if lvl in LEVELS), key=LEVELS.index, default="N0")


class XtdAiPolicy(models.AbstractModel):
    _name = "xtd.ai.policy"
    _description = "AI agent action policy"

    @api.model
    def _xtd_ai_param(self, name, default):
        # sudo: system parameters; agent users cannot read ir.config_parameter
        value = self.env["ir.config_parameter"].sudo().get_param(PARAM + name)
        return default if value in (None, False, "") else value

    @api.model
    def _xtd_ai_company(self):
        # sudo: the policy of the company is read by the gateway for any user
        return self.env.company.sudo()

    @api.model
    def _xtd_ai_profile(self):
        profile = (
            self._xtd_ai_company().xtd_ai_profile
            or str(self._xtd_ai_param("profile", DEFAULT_PROFILE)).strip()
        )
        return profile if profile in PROFILES else DEFAULT_PROFILE

    @api.model
    def _xtd_ai_float_param(self, name, default):
        try:
            return float(self._xtd_ai_param(name, default))
        except (TypeError, ValueError):
            return default

    @api.model
    def _xtd_ai_discount_threshold(self):
        company = self._xtd_ai_company()
        if company.xtd_ai_discount_threshold:
            return company.xtd_ai_discount_threshold
        return self._xtd_ai_float_param(
            "discount_threshold", DEFAULT_DISCOUNT_THRESHOLD
        )

    @api.model
    def _xtd_ai_purchase_confirm_limit(self):
        company = self._xtd_ai_company()
        if company.xtd_ai_purchase_confirm_limit:
            return company.xtd_ai_purchase_confirm_limit
        return self._xtd_ai_float_param(
            "purchase_confirm_limit", DEFAULT_PURCHASE_CONFIRM_LIMIT
        )

    @api.model
    def _xtd_ai_profile_level(self, op_class, profile=None):
        row = POLICY_TABLE.get(op_class)
        if row is None:
            return "N4"
        return row[PROFILES.index(profile or self._xtd_ai_profile())]

    @api.model
    def _xtd_ai_rule(self, op_class=None, tool=None):
        domain = [
            ("company_id", "=", self._xtd_ai_company().id),
            ("level", "!=", False),
        ]
        domain.append(
            ("op_class", "=", op_class) if op_class else ("tool_name", "=", tool)
        )
        # sudo: policy table of the company, managed in the settings
        return self.env["xtd.ai.policy.rule"].sudo().search(domain, limit=1)

    @api.model
    def _xtd_ai_level(self, op_class):
        """Level of an operation class for the company (unknown: N4)."""
        if op_class not in POLICY_TABLE:
            return "N4"
        level = self._xtd_ai_profile_level(op_class)
        if op_class not in FIXED_CLASSES:
            rule = self._xtd_ai_rule(op_class=op_class)
            if rule:
                # the table may harden, or relax down to the Ágil floor
                level = max_level(rule.level, FLOOR[op_class])
        override = str(self._xtd_ai_param(f"level.{op_class}", "")).strip().upper()
        return max_level(level, override) if override in LEVELS else level

    @api.model
    def _xtd_ai_tool_level(self, tool_name, level):
        """A tool row of the table can only harden the level of its call."""
        rule = self._xtd_ai_rule(tool=tool_name)
        return max_level(level, rule.level) if rule else level

    @api.model
    def _xtd_ai_tool_brakes(self, tool, level):
        """Brakes of the company that no profile or table can lower (§6.1).

        Veri*Factu, SII or TicketBAI: anything about publishing or sending
        invoices (accounting tools that post, send or move a document on) is
        N3, the user does it."""
        op_class = tool.get("op_class")
        if op_class in FISCAL_CLASSES and (
            op_class == "post" or tool.get("skill") == "contabilidad"
        ):
            if self._xtd_ai_company()._xtd_ai_has_fiscal_reporting():
                level = max_level(level, "N3")
        return level

    @api.model
    def _xtd_ai_check_paused(self):
        if self._xtd_ai_company().xtd_ai_paused:
            raise XtdAiToolError(
                "paused",
                self.env._(
                    "El agente IA está en pausa en esta compañía: no hagas nada "
                    "más y díselo al usuario (lo reactiva un administrador en "
                    "Ajustes)."
                ),
            )

    @api.model
    def _xtd_ai_check_rate(self, run, write_tools):
        """Stop the agent when it writes too fast (§6.4): writes (done or as a
        card) per user in the last hour and per message (run)."""
        company = self._xtd_ai_company()
        # sudo: users cannot read the audit log
        audit = self.env["xtd.ai.audit"].sudo()
        base = [
            ("event", "=", "tool_call"),
            ("outcome", "in", ("ok", "pending")),
            ("tool_name", "in", list(write_tools)),
        ]
        per_message = company.xtd_ai_max_writes_message
        if per_message and (
            audit.search_count(base + [("run_id", "=", run.id)]) >= per_message
        ):
            raise self._xtd_ai_rate_error(per_message, self.env._("en este mensaje"))
        per_hour = company.xtd_ai_max_writes_hour
        if per_hour:
            since = fields.Datetime.now() - timedelta(hours=1)
            count = audit.search_count(
                base + [("user_id", "=", self.env.uid), ("create_date", ">=", since)]
            )
            if count >= per_hour:
                raise self._xtd_ai_rate_error(per_hour, self.env._("en una hora"))

    @api.model
    def _xtd_ai_rate_error(self, limit, when):
        return XtdAiToolError(
            "rate_limited",
            self.env._(
                "Límite de seguridad: el agente ya ha hecho %(limit)s acciones "
                "%(when)s. Para aquí, no lo intentes de nuevo y dile al usuario "
                "que lo revise y siga él o que lo pida más tarde.",
                limit=limit,
                when=when,
            ),
        )
