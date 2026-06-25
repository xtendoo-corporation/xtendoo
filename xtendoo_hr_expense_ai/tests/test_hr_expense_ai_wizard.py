# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


AI_EXPENSE_RESPONSE = json.dumps(
    {
        "document_type": "expense",
        "document_type_reason": "Receipt from restaurant",
        "supplier": {"name": "Burger King", "vat": "B12345678"},
        "date": "2026-06-15",
        "description": "Lunch meeting",
        "currency": "EUR",
        "total_amount": 25.50,
        "tax_amount": 2.55,
        "product_hint": "Meals",
    }
)


class TestHrExpenseAIWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Configure AI connector params
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("xtendoo_ai_connector.ai_provider", "gemini")
        ICP.set_param("xtendoo_ai_connector.ai_api_key", "fake-key")
        ICP.set_param("xtendoo_ai_connector.ai_model", "gemini-2.5-flash")

        # Create an employee
        cls.employee = cls.env["hr.employee"].create({
            "name": "Test Employee",
        })

        # Create a product that can be expensed
        cls.product = cls.env["product.product"].create({
            "name": "Expensable Product",
            "can_be_expensed": True,
            "type": "service",
        })

        # Create an expense
        cls.expense = cls.env["hr.expense"].create({
            "name": "Draft Expense",
            "employee_id": cls.employee.id,
            "product_id": cls.product.id,
            "total_amount_currency": 0.0,
        })

        # Create a fake attachment
        cls.attachment = cls.env["ir.attachment"].create({
            "name": "receipt.pdf",
            "datas": base64.b64encode(b"fake-pdf-content"),
            "mimetype": "application/pdf",
        })

    def _make_wizard(self):
        return self.env["hr.expense.ai.wizard"].create({
            "expense_id": self.expense.id,
            "attachment_file": self.attachment.datas,
            "attachment_name": self.attachment.name,
        })

    def test_action_analyze_no_attachment_raises(self):
        wizard = self.env["hr.expense.ai.wizard"].create({
            "expense_id": self.expense.id
        })
        with self.assertRaises(UserError):
            wizard.action_analyze()

    @patch("odoo.addons.xtendoo_hr_expense_ai.wizards.hr_expense_ai_wizard.HrExpenseAIWizard._get_ai_provider")
    def test_full_flow_analyze_and_apply(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = AI_EXPENSE_RESPONSE
        mock_get_provider.return_value = mock_provider

        wizard = self._make_wizard()
        wizard.action_analyze()

        self.assertEqual(wizard.state, "preview")
        self.assertTrue(wizard.ai_json_result)

        wizard.action_apply()

        self.assertEqual(self.expense.name, "Lunch meeting")
        self.assertEqual(self.expense.total_amount_currency, 25.50)
        self.assertEqual(str(self.expense.date), "2026-06-15")
        self.assertTrue(self.expense.ai_processed)

    def test_hr_expense_ai_fields_exist(self):
        self.assertIn("ai_document_type", self.expense._fields)
        self.assertIn("ai_processed", self.expense._fields)
        self.assertIn("ai_has_corrections", self.expense._fields)

    def test_ai_has_corrections_set_on_write_after_processing(self):
        self.expense.write({"ai_processed": True, "ai_has_corrections": False})
        self.expense.write({"name": "MANUAL-CHANGE"})
        self.assertTrue(self.expense.ai_has_corrections)

    @patch("odoo.addons.xtendoo_hr_expense_ai.wizards.hr_expense_ai_wizard.HrExpenseAIWizard._get_ai_provider")
    def test_flow_analyze_and_apply_new_expense(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_prompt.return_value = AI_EXPENSE_RESPONSE
        mock_get_provider.return_value = mock_provider

        # Create wizard WITHOUT expense_id
        wizard = self.env["hr.expense.ai.wizard"].create({
            "attachment_file": self.attachment.datas,
            "attachment_name": self.attachment.name,
        })
        wizard.action_analyze()

        self.assertEqual(wizard.state, "preview")
        self.assertTrue(wizard.ai_json_result)

        action = wizard.action_apply()

        # Check that it redirected to the new expense
        self.assertEqual(action.get("res_model"), "hr.expense")
        new_expense_id = action.get("res_id")
        self.assertTrue(new_expense_id)

        new_expense = self.env["hr.expense"].browse(new_expense_id)
        self.assertEqual(new_expense.name, "Lunch meeting")
        self.assertEqual(new_expense.total_amount_currency, 25.50)
        self.assertEqual(str(new_expense.date), "2026-06-15")
        self.assertTrue(new_expense.ai_processed)

