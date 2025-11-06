# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xtendoo_invoice_ai_openai_api_key = fields.Char(
        string="OpenAI API Key",
        help="Your OpenAI API Key for ChatGPT integration",
    )
    xtendoo_invoice_ai_openai_base = fields.Char(
        string="OpenAI Base URL",
        help="Optional: Custom OpenAI base URL for enterprise endpoints",
    )
    xtendoo_invoice_ai_openai_model = fields.Char(
        string="OpenAI Model",
        default="gpt-4o",
        help="OpenAI model to use (must support vision, e.g., gpt-4o, gpt-4-turbo)",
    )
    xtendoo_invoice_ai_max_pages = fields.Integer(
        string="Max Pages to Process",
        default=10,
        help="Maximum number of pages to process from a PDF",
    )
    xtendoo_invoice_ai_temperature = fields.Float(
        string="Temperature",
        default=0.0,
        help="OpenAI temperature parameter (0.0 = deterministic, 1.0 = creative)",
    )
    xtendoo_invoice_ai_tolerance = fields.Float(
        string="Total Tolerance",
        default=0.02,
        help="Maximum difference allowed between AI totals and calculated totals",
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icp = self.env["ir.config_parameter"].sudo()
        res.update(
            xtendoo_invoice_ai_openai_api_key=icp.get_param(
                "xtendoo_invoice_ai.openai_api_key", default=""
            ),
            xtendoo_invoice_ai_openai_base=icp.get_param(
                "xtendoo_invoice_ai.openai_base", default=""
            ),
            xtendoo_invoice_ai_openai_model=icp.get_param(
                "xtendoo_invoice_ai.openai_model", default="gpt-4o"
            ),
            xtendoo_invoice_ai_max_pages=int(
                icp.get_param("xtendoo_invoice_ai.max_pages", default=10)
            ),
            xtendoo_invoice_ai_temperature=float(
                icp.get_param("xtendoo_invoice_ai.temperature", default=0.0)
            ),
            xtendoo_invoice_ai_tolerance=float(
                icp.get_param("xtendoo_invoice_ai.tolerance", default=0.02)
            ),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(
            "xtendoo_invoice_ai.openai_api_key",
            self.xtendoo_invoice_ai_openai_api_key or "",
        )
        icp.set_param(
            "xtendoo_invoice_ai.openai_base",
            self.xtendoo_invoice_ai_openai_base or "",
        )
        icp.set_param(
            "xtendoo_invoice_ai.openai_model",
            self.xtendoo_invoice_ai_openai_model or "gpt-4o",
        )
        icp.set_param(
            "xtendoo_invoice_ai.max_pages",
            self.xtendoo_invoice_ai_max_pages or 10,
        )
        icp.set_param(
            "xtendoo_invoice_ai.temperature",
            self.xtendoo_invoice_ai_temperature or 0.0,
        )
        icp.set_param(
            "xtendoo_invoice_ai.tolerance",
            self.xtendoo_invoice_ai_tolerance or 0.02,
        )
# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class XtendooInvoiceAIJob(models.Model):
    """Histórico de trabajos de extracción de facturas con IA"""

    _name = "xtendoo.invoice.ai.job"
    _description = "Invoice AI Extraction Job"
    _order = "create_date desc"
    _rec_name = "filename"

    filename = fields.Char(string="File Name", required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
        string="State",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        default=lambda self: self.env.user,
        required=True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice Created",
        readonly=True,
    )
    error_message = fields.Text(string="Error Message", readonly=True)

    # Métricas
    tokens_used = fields.Integer(string="Tokens Used", readonly=True)
    processing_time = fields.Float(string="Processing Time (s)", readonly=True)
    pages_processed = fields.Integer(string="Pages Processed", readonly=True)

    # Metadatos
    detected_language = fields.Char(string="Detected Language", readonly=True)
    detected_country = fields.Char(string="Detected Country", readonly=True)
    supplier_name = fields.Char(string="Supplier Name", readonly=True)
    invoice_number = fields.Char(string="Invoice Number", readonly=True)
    invoice_amount = fields.Float(string="Invoice Amount", readonly=True)

    def action_view_invoice(self):
        """Acción para ver la factura creada"""
        self.ensure_one()
        if not self.invoice_id:
            return {}
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.invoice_id.id,
            "target": "current",
        }

