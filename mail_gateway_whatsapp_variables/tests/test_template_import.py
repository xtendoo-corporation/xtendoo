# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from unittest.mock import MagicMock, patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestTemplateImportButtons(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "gateway",
                "gateway_type": "whatsapp",
                "token": "token",
                "whatsapp_security_key": "key",
                "webhook_secret": "MY-SECRET",
                "whatsapp_account_id": "123",
                "member_ids": [(4, cls.env.user.id)],
            }
        )
        cls.meta_data = {
            "data": [
                {
                    "id": "tmpl_1",
                    "name": "same_text_buttons",
                    "category": "MARKETING",
                    "language": "es",
                    "status": "APPROVED",
                    "components": [
                        {"type": "BODY", "text": "Hola"},
                        {
                            "type": "BUTTONS",
                            "buttons": [
                                {"type": "QUICK_REPLY", "text": "Más info"},
                                {
                                    "type": "URL",
                                    "text": "Más info",
                                    "url": "https://example.com",
                                },
                                {"type": "QUICK_REPLY", "text": "Más info"},
                            ],
                        },
                    ],
                }
            ]
        }

    def _import(self):
        response = MagicMock()
        response.json.return_value = self.meta_data
        with patch(
            "odoo.addons.mail_gateway_whatsapp.models.mail_gateway.requests.get",
            return_value=response,
        ):
            self.gateway.button_import_whatsapp_template()
        return self.env["mail.whatsapp.template"].search(
            [("gateway_id", "=", self.gateway.id)]
        )

    def test_import_same_text_buttons(self):
        template = self._import()
        self.assertEqual(len(template), 1)
        buttons = template.button_ids.sorted("sequence")
        self.assertEqual(
            [(b.sequence, b.button_type) for b in buttons],
            [(0, "quick_reply"), (1, "url"), (2, "quick_reply")],
        )
        self.assertEqual(set(buttons.mapped("name")), {"Más info"})

    def test_reimport_does_not_duplicate(self):
        template = self._import()
        ids = template.button_ids.ids
        template = self._import()
        self.assertEqual(sorted(template.button_ids.ids), sorted(ids))
        # sync of a single template goes through the same path
        vals = template._prepare_values_to_import(
            self.gateway, self.meta_data["data"][0]
        )
        template.write(vals)
        self.assertEqual(sorted(template.button_ids.ids), sorted(ids))

    def test_reimport_matches_by_position_and_type(self):
        template = self._import()
        self.meta_data["data"][0]["components"][1]["buttons"][1]["url"] = (
            "https://example.org"
        )
        template = self._import()
        url_button = template.button_ids.filtered(
            lambda b: b.button_type == "url"
        )
        self.assertEqual(len(template.button_ids), 3)
        self.assertEqual(url_button.website_url, "https://example.org")
        self.assertEqual(
            len(template.button_ids.filtered(lambda b: b.button_type == "quick_reply")),
            2,
        )

    def test_sql_constraint_replaced(self):
        self.env.cr.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'mail_whatsapp_template_button_unique_name_per_template'"
        )
        rows = self.env.cr.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIn("button_type", rows[0][0])
        self.assertIn("sequence", rows[0][0])
