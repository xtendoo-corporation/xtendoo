# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class AIFeedbackExample(models.Model):
    """
    Almacena ejemplos de correcciones para mejorar la IA mediante few-shot learning.
    Cada ejemplo contiene lo que la IA extrajo vs. lo que debería haber extraído.
    """

    _name = "xtendoo.ai.feedback.example"
    _description = "AI Feedback Example for Few-Shot Learning"
    _order = "create_date desc"

    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
    )

    supplier_name = fields.Char(
        string="Supplier Name",
        help="Supplier name from the invoice",
    )

    # Datos que la IA extrajo (incorrectos o incompletos)
    ai_extracted_json = fields.Text(
        string="AI Extracted (Before)",
        help="What AI originally extracted",
        required=True,
    )

    # Datos correctos (después de corrección del usuario)
    corrected_json = fields.Text(
        string="Corrected Data (After)",
        help="Correct data after user corrections",
        required=True,
    )

    # Metadatos
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        help="If unchecked, this example won't be used for training",
    )

    notes = fields.Text(
        string="Notes",
        help="Additional notes about this correction",
    )

    # Tipo de corrección
    correction_type = fields.Selection([
        ('supplier', 'Supplier Data'),
        ('lines', 'Invoice Lines'),
        ('taxes', 'Tax Calculation'),
        ('totals', 'Totals'),
        ('dates', 'Dates'),
        ('other', 'Other'),
    ], string="Correction Type")

    quality_score = fields.Float(
        string="Quality Score",
        help="How useful this example is (0-10). Higher scores are used more frequently.",
        default=5.0,
    )

