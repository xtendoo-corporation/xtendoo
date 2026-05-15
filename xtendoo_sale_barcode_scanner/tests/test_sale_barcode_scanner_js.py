from odoo.tests import HttpCase, tagged


def unit_test_error_checker(message):
    return "[HOOT]" not in message


@tagged("-at_install", "post_install")
class TestSaleBarcodeScannerJs(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        admin_user = cls.env.ref("base.user_admin")
        cls.test_login = admin_user.login
        admin_user._change_password(cls.test_login)

    @staticmethod
    def _generate_hoot_hash(test_string):
        value = 0
        for char in test_string:
            value = (value << 5) - value + ord(char)
            value &= 0xFFFFFFFF
        return f"{value:08x}"

    def test_sale_barcode_scanner_hoot_suite(self):
        suite_name = "@xtendoo_sale_barcode_scanner/xtendoo_sale_barcode_scanner"
        suite_hash = self._generate_hoot_hash(suite_name)
        self.browser_js(
            f"/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&id={suite_hash}",
            "",
            "",
            login=self.test_login,
            timeout=1800,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )




