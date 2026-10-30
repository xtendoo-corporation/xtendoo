"""Action levels of the agent (ANALISIS_PERMISOS §6.1): operation class × profile.

Levels: ``N0`` read, ``N1`` do it and offer "Deshacer", ``N2`` confirmation card,
``N3`` prepare and take the user to the screen, ``N4`` forbidden.

Only the *Equilibrado* (balanced) profile is in force in this wave; the other
profiles and the per-class overrides are read from ``ir.config_parameter`` so
the settings table of wave 2 only has to write those parameters:

- ``xtd_ai.policy.profile``: ``balanced`` (default), ``prudent`` or ``agile``.
- ``xtd_ai.policy.level.<op_class>``: ``N1``..``N4``; it can only *raise* the
  level of the profile (an administrator hardens, never opens).
- ``xtd_ai.policy.discount_threshold``: line discount (%) above which a change
  is ``money`` (default 15).
- ``xtd_ai.policy.purchase_confirm_limit``: amount up to which confirming a
  purchase may be offered as a card (wave 2; default 1000).
"""

from odoo import api, models

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
    def _xtd_ai_profile(self):
        profile = str(self._xtd_ai_param("profile", DEFAULT_PROFILE)).strip()
        return profile if profile in PROFILES else DEFAULT_PROFILE

    @api.model
    def _xtd_ai_float_param(self, name, default):
        try:
            return float(self._xtd_ai_param(name, default))
        except (TypeError, ValueError):
            return default

    @api.model
    def _xtd_ai_discount_threshold(self):
        return self._xtd_ai_float_param(
            "discount_threshold", DEFAULT_DISCOUNT_THRESHOLD
        )

    @api.model
    def _xtd_ai_purchase_confirm_limit(self):
        return self._xtd_ai_float_param(
            "purchase_confirm_limit", DEFAULT_PURCHASE_CONFIRM_LIMIT
        )

    @api.model
    def _xtd_ai_level(self, op_class):
        """Level of an operation class for the active profile (unknown: N4)."""
        row = POLICY_TABLE.get(op_class)
        if row is None:
            return "N4"
        level = row[PROFILES.index(self._xtd_ai_profile())]
        override = str(self._xtd_ai_param(f"level.{op_class}", "")).strip().upper()
        return max_level(level, override) if override in LEVELS else level
