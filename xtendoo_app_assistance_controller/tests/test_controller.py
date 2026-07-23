from odoo.tests.common import HttpCase


class TestXtendooAppAssistanceController(HttpCase):
    def test_assistance_endpoint(self):
        response = self.url_open(
            "/xtendoo/app/assistance", method="POST", data={"test": "value"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", response.text)
