"""Browser test: a card with preview lines is confirmed in the real chat panel.

Regression of the OwlError «ctx.action.lines is null» (the card template read
``action.lines.length`` of a confirmed card). ``browser_js`` fails on any uncaught
JS error, so an OWL render error fails the test. It needs Chrome/Chromium; without
it the test is skipped (the Python side is covered by ``test_chat_routes``).
"""

import json
import shutil

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

AI_GROUPS = "base.group_user,xtd_ai.group_xtd_ai_user,base.group_partner_manager"

TOUR = """
const wait = async (check, what, ms = 20000) => {
    const end = Date.now() + ms;
    while (Date.now() < end) {
        const found = check();
        if (found) { return found; }
        await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("timeout waiting for " + what);
};
(async () => {
    const toggle = await wait(
        () => document.querySelector(".o_main_navbar .o_xtd_ai_toggle"), "systray"
    );
    toggle.click();
    const confirm = await wait(
        () => document.querySelector(".o_xtd_ai_card_pending .o_xtd_ai_confirm"),
        "pending card"
    );
    const rows = document.querySelectorAll(".o_xtd_ai_card_pending table tr").length;
    if (rows !== 1) { throw new Error("pending card rows: " + rows); }
    confirm.click();
    const done = await wait(
        () => document.querySelector(".o_xtd_ai_card_confirmed"), "confirmed card"
    );
    // give OWL time to re-render the confirmed card (where it used to break)
    await new Promise((resolve) => setTimeout(resolve, 1500));
    if (document.querySelector(".o_dialog .o_error_dialog, .o_notification_error")) {
        throw new Error("error dialog after confirming");
    }
    const link = done.querySelector(".o_xtd_ai_card_state a");
    if (!link || !link.textContent.includes("Tour Card SL")) {
        throw new Error("confirmed card without its result link");
    }
    console.log("test successful");
})().catch((error) => console.error("TOUR FAILED: " + error.message));
"""


@tagged("post_install", "-at_install")
class TestChatCardTour(HttpCase):
    def test_confirm_card_renders_without_owl_error(self):
        if not (shutil.which("chromium") or shutil.which("google-chrome")):
            self.skipTest("no Chrome/Chromium to run browser_js")
        user = new_test_user(self.env, "xtd_ai_tour", groups=AI_GROUPS)
        # no automatic continuation: the test never calls an agent
        self.env["ir.config_parameter"].sudo().set_param("xtd_ai.auto_continue", "False")
        conversation = self.env["xtd.ai.conversation"].with_user(user)._xtd_ai_open()
        run, _token = conversation._xtd_ai_start_run("crea el contacto")
        run.sudo()._xtd_ai_finish("done")
        action = self.env["xtd.ai.pending_action"].sudo().create(
            {
                "run_id": run.id,
                "conversation_id": conversation.id,
                "user_id": user.id,
                "tool_name": "create_contact",
                "arguments": {"name": "Tour Card SL"},
                "preview": {
                    "summary": "Crear contacto «Tour Card SL»",
                    "lines": [{"field": "name", "value": "Tour Card SL"}],
                },
                "cids": [user.company_id.id],
            }
        )
        message = self.env["xtd.ai.message"].sudo().create(
            {
                "conversation_id": conversation.id,
                "role": "assistant",
                "body": "listo",
                "run_id": run.id,
            }
        )
        action.sudo().message_id = message
        self.browser_js(
            "/odoo",
            TOUR,
            "odoo.isReady",
            login="xtd_ai_tour",
            timeout=120,
            success_signal="test successful",
        )
        self.assertEqual(action.state, "confirmed")
        self.assertTrue(json.dumps(action.preview))
