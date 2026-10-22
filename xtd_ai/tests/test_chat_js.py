import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class TestChatHoot(odoo.tests.HttpCase):
    def test_safe_renderer_hoot(self):
        """Hoot tests of the safe markdown renderer (static/tests/*.test.js)."""
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&filter=%22%40xtd_ai%22",
            "",
            "",
            login="admin",
            timeout=600,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=lambda message: "[HOOT]" not in message,
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestChatWebClientSmoke(odoo.tests.HttpCase):
    """The full web client must boot for an AI user with the chat assets loaded.

    Regression: a component used in the systray template was not declared, which
    crashed the whole backend for every AI user while every unit test passed.
    ``browser_js`` fails on any uncaught JS error in the page.
    """

    def test_web_client_boots_for_ai_user(self):
        from odoo.tests.common import new_test_user

        new_test_user(
            self.env,
            "xtd_ai_smoke",
            groups="base.group_user,xtd_ai.group_xtd_ai_user",
        )
        self.browser_js(
            "/odoo",
            """
            const button = document.querySelector('.o_main_navbar .o_xtd_ai_toggle');
            if (!button) {
                console.error('xtd_ai systray button missing');
            } else {
                console.log('test successful');
            }
            """,
            "odoo.isReady",
            login="xtd_ai_smoke",
            timeout=120,
        )
