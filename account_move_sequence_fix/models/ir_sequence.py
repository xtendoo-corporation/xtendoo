# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import models, api
from odoo.exceptions import UserError
from odoo import _

_logger = logging.getLogger(__name__)


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def next_by_id(self, sequence_date=None):
        """Override to ensure the sequence id is valid before calling the query."""
        self.ensure_one()

        # Check if the sequence has a valid id
        if not self.id or not isinstance(self.id, int):
            _logger.error(
                "Attempted to get next sequence number with invalid id: %s (type: %s)",
                self.id,
                type(self.id)
            )
            raise UserError(_(
                "Cannot get next sequence number: Invalid sequence record. "
                "Please contact your system administrator."
            ))

        return super().next_by_id(sequence_date=sequence_date)

    def _next(self, sequence_date=None):
        """Override to add extra validation before processing."""
        if not self:
            raise UserError(_("No sequence record found to get next number."))

        # Ensure we have a valid recordset with proper ids
        for seq in self:
            if not seq.id or not isinstance(seq.id, int):
                _logger.error(
                    "Invalid sequence id found: %s (type: %s) for sequence: %s",
                    seq.id,
                    type(seq.id),
                    seq.name if hasattr(seq, 'name') else 'Unknown'
                )
                raise UserError(_(
                    "Cannot process sequence: Invalid sequence record. "
                    "Please verify the journal configuration."
                ))

        return super()._next(sequence_date=sequence_date)

