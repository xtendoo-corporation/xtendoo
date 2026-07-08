from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.models import Model
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMoveUpdateJournal(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal_editor_group = cls.env.ref(
            "xtendoo_account_move_update_journal.group_journal_editor"
        )
        cls.sale_journal = cls.company_data["default_journal_sale"]
        cls.alt_sale_journal = cls.sale_journal.copy(
            {
                "name": "Secondary Sale Journal",
                "code": "SSJ2",
            }
        )
        cls.misc_journal = cls.company_data["default_journal_misc"].copy(
            {
                "name": "Secondary Misc Journal",
                "code": "SMJ2",
            }
        )
        cls.editor_user = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Journal Editor",
                "login": "journal_editor",
                "password": "journal_editor",
                "group_ids": [
                    Command.link(cls.env.ref("account.group_account_user").id),
                    Command.link(cls.env.ref("account.group_account_manager").id),
                    Command.link(cls.journal_editor_group.id),
                ],
            }
        )
        cls.account_manager_user = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Regular Accountant",
                "login": "regular_accountant",
                "password": "regular_accountant",
                "group_ids": [
                    Command.link(cls.env.ref("account.group_account_user").id),
                    Command.link(cls.env.ref("account.group_account_manager").id),
                ],
            }
        )

    def _create_reset_to_draft_invoice(self, journal=None):
        move = self.init_invoice(
            "out_invoice",
            self.partner_a,
            fields.Date.today(),
            amounts=[1000.0],
            journal=journal or self.sale_journal,
            post=False,
        )
        move.action_post()
        move.button_draft()
        return move

    def test_can_update_journal_depends_on_group_and_state(self):
        move = self._create_reset_to_draft_invoice()

        self.assertTrue(move.with_user(self.editor_user).can_update_journal)
        self.assertFalse(move.with_user(self.account_manager_user).can_update_journal)
        move.with_user(self.editor_user).action_post()
        self.assertFalse(move.with_user(self.editor_user).can_update_journal)

    def test_editor_can_change_journal_and_logs_in_chatter(self):
        move = self._create_reset_to_draft_invoice()

        move.with_user(self.editor_user).write({"journal_id": self.alt_sale_journal.id})

        self.assertEqual(move.journal_id, self.alt_sale_journal)
        self.assertTrue(
            any(
                "Journal updated by Journal Editor" in (message.body or "")
                and self.sale_journal.display_name in (message.body or "")
                and self.alt_sale_journal.display_name in (message.body or "")
                for message in move.message_ids
            )
        )

    def test_non_editor_keeps_standard_restriction(self):
        move = self._create_reset_to_draft_invoice()

        with self.assertRaisesRegex(
            UserError,
            "You cannot edit the journal of an account move if it has been posted once",
        ):
            move.with_user(self.account_manager_user).write(
                {"journal_id": self.alt_sale_journal.id}
            )

    def test_editor_cannot_change_journal_with_secure_sequence(self):
        move = self._create_reset_to_draft_invoice()
        Model.write(move, {"secure_sequence_number": 42})

        with self.assertRaisesRegex(
            UserError,
            "integridad fiscal protegida",
        ):
            move.with_user(self.editor_user).write(
                {"journal_id": self.alt_sale_journal.id}
            )

    def test_editor_cannot_change_journal_with_inalterable_hash(self):
        move = self._create_reset_to_draft_invoice()
        Model.write(move, {"inalterable_hash": "fake_hash"})

        with self.assertRaisesRegex(
            UserError,
            "integridad fiscal protegida",
        ):
            move.with_user(self.editor_user).write(
                {"journal_id": self.alt_sale_journal.id}
            )

    def test_editor_logs_warning_on_journal_type_mismatch(self):
        move = self._create_reset_to_draft_invoice()

        with self.assertLogs(
            "odoo.addons.xtendoo_account_move_update_journal.models.account_move",
            level="WARNING",
        ) as logs:
            with self.assertRaisesRegex(
                ValidationError,
                "Cannot create a sale document in a non sale journal",
            ):
                move.with_user(self.editor_user).write(
                    {"journal_id": self.misc_journal.id}
                )

        self.assertTrue(
            any("Changing journal type on account.move" in line for line in logs.output)
        )
