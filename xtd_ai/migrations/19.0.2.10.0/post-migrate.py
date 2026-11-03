from odoo import SUPERUSER_ID, api

from odoo.addons.xtd_ai.models.xtd_ai_policy import (
    DEFAULT_DISCOUNT_THRESHOLD,
    DEFAULT_PROFILE,
    DEFAULT_PURCHASE_CONFIRM_LIMIT,
    FIXED_CLASSES,
    LEVELS,
    POLICY_TABLE,
    PROFILES,
    max_level,
)


def migrate(cr, version):
    """Policy of waves 1A/1B (``ir.config_parameter``) into the settings of
    every company: profile, thresholds and the per-class levels (which could
    only harden, so they become hardening rows of the table). The parameters
    stay as a fallback and keep hardening, so nothing changes in behaviour."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env["ir.config_parameter"]
    profile = (params.get_param("xtd_ai.policy.profile") or "").strip()
    if profile not in PROFILES:
        profile = DEFAULT_PROFILE
    vals = {}
    if profile != DEFAULT_PROFILE:
        vals["xtd_ai_profile"] = profile
    for key, field, default in (
        ("discount_threshold", "xtd_ai_discount_threshold", DEFAULT_DISCOUNT_THRESHOLD),
        (
            "purchase_confirm_limit",
            "xtd_ai_purchase_confirm_limit",
            DEFAULT_PURCHASE_CONFIRM_LIMIT,
        ),
    ):
        try:
            value = float(params.get_param(f"xtd_ai.policy.{key}") or default)
        except ValueError:
            value = default
        if value != default:
            vals[field] = value
    companies = env["res.company"].search([])
    if vals:
        companies.write(vals)
    Rule = env["xtd.ai.policy.rule"]
    for company in companies:
        Rule._xtd_ai_ensure_rows(company)
        for op_class in POLICY_TABLE:
            level = (params.get_param(f"xtd_ai.policy.level.{op_class}") or "").upper()
            if op_class in FIXED_CLASSES or level not in LEVELS:
                continue
            row = Rule.search(
                [("company_id", "=", company.id), ("op_class", "=", op_class)]
            )
            base = POLICY_TABLE[op_class][PROFILES.index(profile)]
            if max_level(level, base) != base:  # only a hardening is kept
                row.level = level
