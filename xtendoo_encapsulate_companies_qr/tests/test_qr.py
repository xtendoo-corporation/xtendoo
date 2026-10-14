from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductQR(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_on = cls.env.company
        cls.company_on.qr_product_enabled = True
        cls.company_off = cls.env["res.company"].create({"name": "QR Off"})
        cls.product = cls.env["product.template"].create(
            {"name": "Producto QR", "default_code": "QR001"}
        )

    def test_generate_qr_enabled_company(self):
        self.product.action_generate_qr()
        self.assertTrue(self.product.qr_image)
        self.assertTrue(self.product.qr_company_enabled)

    def test_disabled_company_cannot_use(self):
        product = self.product.with_company(self.company_off)
        self.assertFalse(product.qr_company_enabled)
        with self.assertRaises(UserError):
            product.action_generate_qr()

    def test_document_url_uses_base_url(self):
        self.env["ir.config_parameter"].sudo().set_param("web.base.url", "https://erp.example.com/")
        self.product.qr_document = "UERG"  # base64 dummy
        self.product.action_generate_qr()
        self.assertTrue(self.product.qr_access_token)
        self.assertEqual(
            self.product._get_qr_url(),
            "https://erp.example.com/qr/producto/%s" % self.product.qr_access_token,
        )
