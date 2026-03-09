# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class GeminiFeedback(models.Model):
    """
    Almacena correcciones manuales sobre datos extraídos por Gemini AI.
    Se usa para mejorar futuras extracciones del mismo proveedor o estructura.
    """
    _name = "gemini.feedback"
    _description = "Gemini AI Feedback"
    _order = "create_date desc"

    partner_id = fields.Many2one("res.partner", string="Proveedor", index=True)
    gemini_partner_name = fields.Char(string="Proveedor extraído por Gemini")
    gemini_date = fields.Char(string="Fecha extraída por Gemini")
    gemini_amount = fields.Float(string="Importe extraído por Gemini")
    gemini_description = fields.Char(string="Descripción extraída por Gemini")
    correct_partner_name = fields.Char(string="Nombre correcto del proveedor")
    correct_date = fields.Char(string="Fecha correcta")
    correct_amount = fields.Float(string="Importe correcto")
    correct_description = fields.Char(string="Descripción correcta")
    notes = fields.Text(
        string="Notas para Gemini",
        help="Explica a Gemini dónde encontrar este dato en documentos de este proveedor",
    )
    source_model = fields.Selection(
        [
            ("account.analytic.line", "Apunte analítico"),
            ("account.move", "Factura de compra"),
        ],
        string="Origen",
    )
    analytic_line_id = fields.Many2one(
        "account.analytic.line", string="Apunte analítico", ondelete="set null"
    )
    move_id = fields.Many2one("account.move", string="Factura", ondelete="set null")
    active = fields.Boolean(default=True)

    @api.model
    def get_feedback_context_for_prompt(self, partner_id=None, source_model=None):
        """
        Devuelve ejemplos concretos de asientos correctos para incluir en el prompt.
        - partner_id: si se pasa, filtra por proveedor
        - source_model: si se pasa, filtra por origen ('account.move', 'account.analytic.line')
        """
        domain = [("active", "=", True), ("notes", "!=", False), ("notes", "!=", "")]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        if source_model:
            domain.append(("source_model", "=", source_model))
        feedbacks = self.search(domain, limit=5, order="create_date desc")
        if not feedbacks:
            return ""

        lines = [
            "\n\n=== EJEMPLOS REALES APROBADOS POR EL USUARIO ===",
            "Para documentos similares a los siguientes, usa EXACTAMENTE estas líneas de asiento:",
        ]
        for fb in feedbacks:
            name = fb.partner_id.name if fb.partner_id else fb.gemini_partner_name or "desconocido"
            ref = fb.correct_description or fb.gemini_description or ""
            lines.append(f"\n--- Ejemplo (emisor: {name}, ref: {ref}) ---")
            lines.append(fb.notes)
        lines.append("\n=== FIN DE EJEMPLOS ===\n")
        return "\n".join(lines)

