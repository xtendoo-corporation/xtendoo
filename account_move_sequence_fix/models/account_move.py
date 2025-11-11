# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import models, api
from odoo.exceptions import UserError
from odoo import _

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        """Override to ensure journal sequences are properly set before posting."""
        # Check and fix journal sequences before posting
        for move in self:
            if move.journal_id and move.journal_id.secure_sequence_id:
                sequence = move.journal_id.secure_sequence_id

                # Verify the sequence has a valid id
                if not sequence.id or not isinstance(sequence.id, int):
                    _logger.error(
                        "Journal %s has invalid secure_sequence_id: %s (type: %s)",
                        move.journal_id.name,
                        sequence.id,
                        type(sequence.id)
                    )

                    # Try to fix by reloading the journal
                    move.journal_id.invalidate_recordset(['secure_sequence_id'])
                    sequence = move.journal_id.secure_sequence_id

                    # If still invalid, raise an error
                    if not sequence or not sequence.id or not isinstance(sequence.id, int):
                        raise UserError(_(
                            "The journal '%s' has an invalid secure sequence configuration. "
                            "Please contact your system administrator to fix this issue.\n\n"
                            "Technical details: secure_sequence_id=%s (type: %s)"
                        ) % (move.journal_id.name, sequence.id if sequence else None, type(sequence.id) if sequence else None))

        return super()._post(soft=soft)

    def write(self, vals):
        """Override to validate sequence assignment."""
        # If writing a journal_id, ensure it has valid sequences
        if 'journal_id' in vals:
            journal = self.env['account.journal'].browse(vals['journal_id'])
            if journal and journal.secure_sequence_id:
                sequence = journal.secure_sequence_id
                if not sequence.id or not isinstance(sequence.id, int):
                    _logger.error(
                        "Attempting to set journal %s with invalid secure_sequence_id: %s",
                        journal.name,
                        sequence.id
                    )
                    # Reload the journal to get fresh data
                    journal.invalidate_recordset(['secure_sequence_id'])
                    sequence = journal.secure_sequence_id

                    if not sequence or not sequence.id or not isinstance(sequence.id, int):
                        raise UserError(_(
                            "Cannot use journal '%s' because it has an invalid sequence configuration. "
                            "Please contact your system administrator."
                        ) % journal.name)

        return super().write(vals)

