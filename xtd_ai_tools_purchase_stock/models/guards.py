from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiDraftOnlyError


def check_draft_only(env, message):
    """Raise ``XtdAiDraftOnlyError`` when running inside an AI run (CONTRACT §7)."""
    if env.context.get("xtd_ai_run"):
        raise XtdAiDraftOnlyError(message)
