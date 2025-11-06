# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class XtendooInvoiceAIJob(models.Model):
    _name = "xtendoo.invoice.ai.job"
    _description = "AI Invoice Import Job"
    _order = "create_date desc"

    filename = fields.Char(string="File Name", required=True)
    state = fields.Selection(
        [
            ("processing", "Processing"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        string="State",
        default="processing",
        required=True,
    )
    invoice_id = fields.Many2one("account.move", string="Invoice", ondelete="set null")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        default=lambda self: self.env.user,
        required=True,
    )
    processing_time = fields.Float(string="Processing Time (s)")
    tokens_used = fields.Integer(string="Tokens Used")
    pages_processed = fields.Integer(string="Pages Processed")
    detected_language = fields.Char(string="Detected Language")
    detected_country = fields.Char(string="Detected Country")
    supplier_name = fields.Char(string="Supplier Name")
    invoice_number = fields.Char(string="Invoice Number")
    invoice_amount = fields.Float(string="Invoice Amount")
    error_message = fields.Text(string="Error Message")

    def action_view_invoice(self):
        """Acción para ver la factura relacionada"""
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            "name": _("Invoice"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "view_type": "form",
        }

