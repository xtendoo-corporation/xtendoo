# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVolumeInLiters(TransactionCase):
    def setUp(self):
        super().setUp()
        self.template = self.env["product.template"].create(
            {"name": "Test product volume_in_liters"}
        )
        self.param = self.env["ir.config_parameter"].sudo()

    def _get_uom(self):
        return self.template._get_volume_uom_id_from_ir_config_parameter()

    def test_default_cubic_meters(self):
        self.param.set_param("product.volume_in_cubic_feet", False)
        self.assertEqual(self._get_uom(), self.env.ref("uom.product_uom_cubic_meter"))

    def test_cubic_feet(self):
        self.param.set_param("product.volume_in_cubic_feet", "1")
        self.assertEqual(self._get_uom(), self.env.ref("uom.product_uom_cubic_foot"))

    def test_liters(self):
        self.param.set_param("product.volume_in_cubic_feet", "2")
        self.assertEqual(self._get_uom(), self.env.ref("uom.product_uom_litre"))

    def test_res_config_settings_liters_option(self):
        settings = self.env["res.config.settings"].create(
            {"product_volume_volume_in_cubic_feet": "2"}
        )
        settings.execute()
        self.assertEqual(
            self.param.get_param("product.volume_in_cubic_feet"), "2"
        )
