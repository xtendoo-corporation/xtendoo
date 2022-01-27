# Copyright 2021 Xtendoo (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, exceptions, fields, models

class SettlementLine(models.Model):
    _inherit = "sale.commission.settlement.line"

    invoice_id = fields.Many2one(
        comodel_name='account.move', string='Factura', Store=True,
        default=lambda self: self._get_invoice_id(),
        compute="_invoice_id")

    def _invoice_id(self):
        self.invoice_id=self.invoice_line_id.move_id

    @api.model
    def _get_invoice_id(self):
        return self.invoice_line_id.move_id