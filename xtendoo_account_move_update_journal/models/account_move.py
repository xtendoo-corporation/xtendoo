import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.models import Model

_logger = logging.getLogger(__name__)

GROUP_XMLID = (
    "xtendoo_account_move_update_journal.group_journal_editor"
)
SKIP_JOURNAL_RESTRICTION_CONTEXT = (
    "xtendoo_skip_journal_change_restriction"
)


class AccountMove(models.Model):
    _inherit = "account.move"

    can_update_journal = fields.Boolean(
        compute="_compute_can_update_journal",
        compute_sudo=False,
    )

    def _is_current_user_journal_editor(self):
        group = self.env.ref(GROUP_XMLID, raise_if_not_found=False)
        if not group:
            return False
        self.env.cr.execute(
            """
            SELECT 1
              FROM res_groups_users_rel
             WHERE gid = %s
               AND uid = %s
             LIMIT 1
            """,
            [group.id, self.env.user.id],
        )
        return bool(self.env.cr.fetchone()) and self.env.user.has_group(
            "account.group_account_manager"
        )

    @api.depends_context("uid")
    def _compute_can_update_journal(self):
        can_update = self._is_current_user_journal_editor()
        for move in self:
            move.can_update_journal = can_update and move.state == "draft"

    def _get_protected_integrity_fields(self):
        return [
            field_name
            for field_name in ("inalterable_hash", "inalterability_hash")
            if field_name in self._fields
        ]

    def _check_journal_change_fiscal_integrity(self):
        protected_hash_fields = self._get_protected_integrity_fields()
        for move in self:
            protected_hash = any(
                move[field_name] for field_name in protected_hash_fields
            )
            if move.secure_sequence_number or protected_hash:
                raise UserError(
                    _(
                        "No se puede cambiar el diario de este asiento porque "
                        "tiene integridad fiscal protegida."
                    )
                )

    def _log_journal_type_mismatch(self, new_journal):
        if not new_journal.exists():
            return
        for move in self.filtered(lambda m: m.journal_id.type != new_journal.type):
            _logger.warning(
                "Changing journal type on account.move %s by user %s (%s): "
                "%s [%s] -> %s [%s]",
                move.id,
                self.env.user.name,
                self.env.user.id,
                move.journal_id.display_name,
                move.journal_id.type,
                new_journal.display_name,
                new_journal.type,
            )

    def _post_journal_change_message(self, original_journals):
        timestamp = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        timestamp_text = fields.Datetime.to_string(timestamp)
        for move in self:
            old_journal = original_journals[move.id]
            move.message_post(
                body=_(
                    "Journal updated by %(user)s on %(date)s. "
                    "Previous journal: %(old)s. New journal: %(new)s.",
                    user=self.env.user.display_name,
                    date=timestamp_text,
                    old=old_journal.display_name,
                    new=move.journal_id.display_name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    def _raise_if_review_write_forbidden(self, move, vals):
        if vals.get("checked") and not move._is_user_able_to_review():
            raise AccessError(
                _("You don't have the access rights to perform this action.")
            )
        if (
            vals.get("state") == "draft"
            and move.checked
            and not move._is_user_able_to_review()
        ):
            raise ValidationError(
                _("Validated entries can only be changed by your accountant.")
            )

    def _raise_if_hash_protected_write(self, move, vals):
        protected_fields = (
            move._get_integrity_hash_fields() + self._get_protected_integrity_fields()
        )
        violated_fields = set(vals).intersection(protected_fields)
        if move.inalterable_hash and violated_fields:
            raise UserError(
                _(
                    "This document is protected by a hash. "
                    "Therefore, you cannot edit the following fields: %s.",
                    ", ".join(
                        field["string"]
                        for field in self.fields_get(violated_fields).values()
                    ),
                )
            )

    def _raise_if_forbidden_journal_change(
        self, move, vals, skip_journal_restriction
    ):
        if "journal_id" not in vals or move.journal_id.id == vals["journal_id"]:
            return

        name_reset_in_vals = "name" in vals and (
            vals["name"] == "/" or not vals["name"]
        )
        journal_change_allowed_by_name = (
            move.name == "/" or not move.name or name_reset_in_vals
        )
        if (
            not skip_journal_restriction
            and move.posted_before
            and not journal_change_allowed_by_name
        ):
            raise UserError(
                _(
                    'You cannot edit the journal of an account move if it has been '
                    'posted once, unless the name is removed or set to "/". '
                    "This might create a gap in the sequence."
                )
            )
        if (
            not skip_journal_restriction
            and move.name
            and move.name != "/"
            and move.sequence_number not in (0, 1)
            and not move.quick_edit_mode
            and not name_reset_in_vals
        ):
            raise UserError(
                _(
                    'You cannot edit the journal of an account move with a '
                    'sequence number assigned, unless the name is removed or set '
                    'to "/". This might create a gap in the sequence.'
                )
            )

    def _raise_if_locked_or_readonly_write(self, move, vals):
        if move.state == "posted" and (
            ("name" in vals and move.name != vals["name"])
            or ("date" in vals and move.date != vals["date"])
        ):
            move._check_fiscal_lock_dates()
            move.line_ids._check_tax_lock_date()

        if "state" in vals and move.state == "posted" and vals["state"] != "posted":
            move._check_fiscal_lock_dates()
            move.line_ids._check_tax_lock_date()

        move_state = vals.get("state", move.state)
        unmodifiable_fields = (
            "invoice_line_ids",
            "line_ids",
            "invoice_date",
            "date",
            "partner_id",
            "invoice_payment_term_id",
            "currency_id",
            "fiscal_position_id",
            "invoice_cash_rounding_id",
        )
        readonly_fields = [val for val in vals if val in unmodifiable_fields]
        if (
            not self.env.context.get("skip_readonly_check")
            and move_state == "posted"
            and readonly_fields
        ):
            raise UserError(
                _(
                    "You cannot modify the following readonly fields on a posted "
                    "move: %s",
                    ", ".join(readonly_fields),
                )
            )

    def _handle_sequence_override_regex(self, move, vals):
        if (
            move.journal_id.sequence_override_regex
            and vals.get("name")
            and vals["name"] != "/"
            and not re.match(move.journal_id.sequence_override_regex, vals["name"])
        ):
            if not self.env.user.has_group("account.group_account_manager"):
                raise UserError(
                    _(
                        "The Journal Entry sequence is not conform to the current "
                        "format. Only the Accountant can change it."
                    )
                )
            move.journal_id.sequence_override_regex = False

    def _validate_write_with_journal_change_override(
        self, vals, skip_journal_restriction
    ):
        for move in self:
            self._raise_if_review_write_forbidden(move, vals)
            self._raise_if_hash_protected_write(move, vals)
            self._raise_if_forbidden_journal_change(
                move, vals, skip_journal_restriction
            )
            self._raise_if_locked_or_readonly_write(move, vals)
            self._handle_sequence_override_regex(move, vals)

    def _write_with_journal_change_override(self, vals):
        if not vals:
            return True

        vals = dict(vals)
        self._sanitize_vals(vals)

        skip_journal_restriction = self.env.context.get(
            SKIP_JOURNAL_RESTRICTION_CONTEXT
        )
        self._validate_write_with_journal_change_override(
            vals, skip_journal_restriction
        )

        if {"sequence_prefix", "sequence_number", "journal_id", "name"} & vals.keys():
            self._update_sequence_made_gap(invalidate_current=True)

        stolen_moves = self.browse(set(move for move in self._stolen_move(vals)))
        container = {"records": self | stolen_moves}
        with self.env.protecting(
            self._get_protected_vals(vals, self)
        ), self._check_balanced(container):
            with self._sync_dynamic_lines(container):
                if (
                    "is_manually_modified" not in vals
                    and not self.env.context.get("skip_is_manually_modified")
                ):
                    vals["is_manually_modified"] = True

                res = Model.write(
                    self.with_context(skip_account_move_synchronization=True),
                    vals,
                )

                if "journal_id" in vals and "name" not in vals:
                    draft_move = self.filtered(lambda move: not move.posted_before)
                    draft_move.name = False
                    draft_move._compute_name()

                if "date" in vals or "state" in vals:
                    posted_move = self.filtered(lambda move: move.state == "posted")
                    posted_move._check_fiscal_lock_dates()
                    posted_move.line_ids._check_tax_lock_date()

                if vals.get("state") == "posted":
                    self.flush_recordset()
                    self._hash_moves()

            self._synchronize_business_models(set(vals.keys()))

            for move in self:
                if "tax_totals" in vals:
                    Model.write(move, {"tax_totals": vals["tax_totals"]})

        if any(field in vals for field in ["journal_id", "currency_id"]):
            self.line_ids._check_constrains_account_id_journal_id()

        return res

    def write(self, vals):
        if self.env.context.get(SKIP_JOURNAL_RESTRICTION_CONTEXT):
            return self._write_with_journal_change_override(vals)

        if (
            not vals
            or "journal_id" not in vals
            or not self._is_current_user_journal_editor()
        ):
            return super().write(vals)

        new_journal = self.env["account.journal"].browse(vals["journal_id"])
        moves_to_bypass = self.filtered(
            lambda move: move.state == "draft"
            and move.journal_id.id != vals["journal_id"]
        )
        if not moves_to_bypass:
            return super().write(vals)

        remaining_moves = self - moves_to_bypass
        original_journals = {
            move.id: move.journal_id for move in moves_to_bypass
        }

        moves_to_bypass._check_journal_change_fiscal_integrity()
        moves_to_bypass._log_journal_type_mismatch(new_journal)

        result = True
        if remaining_moves:
            result = remaining_moves.write(dict(vals))

        bypass_result = moves_to_bypass.with_context(
            **{SKIP_JOURNAL_RESTRICTION_CONTEXT: True}
        ).write(dict(vals))
        moves_to_bypass._post_journal_change_message(original_journals)
        return result and bypass_result
