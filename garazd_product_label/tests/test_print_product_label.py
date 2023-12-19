from odoo.tests.common import TransactionCase
from odoo.tools import test_reports


class TestPrintProductLabel(TransactionCase):

    def setUp(self):
        super(TestPrintProductLabel, self).setUp()
        self.product_chair = self.env.ref('product.product_product_12')
        self.product_drawer = self.env.ref('product.product_product_27')

    def test_print_wizard(self):
        ctx = {
            'active_model': 'product.product',
            'default_product_ids': [
                self.product_chair.id,
                self.product_drawer.id,
            ],
        }
        wizard = self.env['print.product.label'].with_context(ctx).create({})
        self.assertEqual(len(wizard.label_ids), 2)

        test_reports.try_report(
            self.env.cr,
            self.env.uid,
            'garazd_product_label.report_product_label_57x35_template',
            ids=wizard.label_ids.ids,
            our_module='garazd_product_label'
        )
