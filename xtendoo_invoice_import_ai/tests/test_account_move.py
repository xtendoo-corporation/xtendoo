# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import TransactionCase


class TestAccountMove(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.general_journal = cls.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        if not cls.general_journal:
            cls.general_journal = cls.env["account.journal"].create(
                {
                    "name": "Test General Journal",
                    "code": "TGJ",
                    "type": "general",
                    "company_id": cls.env.company.id,
                }
            )

    def test_create_multi_draft_moves(self):
        """Creating multiple draft moves must not fail on singleton access."""
        moves = self.env["account.move"].create(
            [
                {
                    "date": fields.Date.today(),
                    "journal_id": self.general_journal.id,
                    "move_type": "entry",
                },
                {
                    "date": fields.Date.today(),
                    "journal_id": self.general_journal.id,
                    "move_type": "entry",
                },
            ]
        )

        self.assertEqual(len(moves), 2)
        self.assertEqual(moves.mapped("state"), ["draft", "draft"])

