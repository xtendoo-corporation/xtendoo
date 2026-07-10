# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import logging
from odoo import _, api, fields, models
_logger = logging.getLogger(__name__)
class GeminiFeedback(models.Model):
    """
    Almacena correcciones manuales sobre datos extraídos por Gemini AI.
    Se guarda UN registro por cada corrección (sesión). NO se fusiona ni se elimina.
    Al aplicar el feedback se usan TODOS los registros del emisor de más antiguo
    a más reciente, de forma que el más reciente prevalece campo a campo.
    """
    _name = "gemini.feedback"
    _description = "Gemini AI Feedback"
    _order = "write_date desc"
    partner_id = fields.Many2one("res.partner", string="Proveedor", index=True)
    gemini_partner_name = fields.Char(string="Proveedor extraído por Gemini")
    gemini_date = fields.Char(string="Fecha extraída por Gemini")
    gemini_amount = fields.Float(string="Importe extraído por Gemini")
    gemini_description = fields.Char(string="Descripción extraída por Gemini")
    correct_partner_name = fields.Char(string="Nombre correcto del proveedor")
    correct_date = fields.Char(string="Fecha correcta")
    correct_amount = fields.Float(string="Importe correcto")
    correct_description = fields.Char(string="Descripción correcta")
    correct_lines_json = fields.Text(
        string="Líneas correctas (JSON)",
        help="JSON con las líneas corregidas. Para facturas incluye tax_id (ID real de Odoo).",
    )
    notes = fields.Text(
        string="Notas para Gemini",
        help="Instrucciones para Gemini sobre este emisor.",
    )
    source_model = fields.Selection(
        [
            ("account.analytic.line", "Apunte analítico"),
            ("account.move", "Asiento contable"),
        ],
        string="Origen",
    )
    analytic_line_id = fields.Many2one(
        "account.analytic.line", string="Apunte analítico", ondelete="set null"
    )
    move_id = fields.Many2one("account.move", string="Asiento", ondelete="set null")
    active = fields.Boolean(default=True)
    def merge_with_new(self, new_vals):
        """
        Fusiona este registro con los nuevos datos.
        - correct_lines_json: siempre se sobreescribe.
        - Cabecera: se actualiza solo si el nuevo valor no está vacío.
        """
        self.ensure_one()
        update = {}
        if new_vals.get("correct_lines_json"):
            update["correct_lines_json"] = new_vals["correct_lines_json"]
        for f in ("correct_partner_name", "correct_date", "correct_description",
                  "partner_id", "gemini_partner_name", "gemini_date", "gemini_description"):
            if new_vals.get(f):
                update[f] = new_vals[f]
        if new_vals.get("move_id"):
            update["move_id"] = new_vals["move_id"]
        if new_vals.get("notes"):
            update["notes"] = new_vals["notes"]
        if update:
            self.write(update)
    @api.model
    def find_for_entry_emisor(self, partner_id=None, partner_name=None):
        """
        Devuelve el feedback MAS RECIENTE para un emisor.
        Se usa al guardar nuevo feedback (action_teach_gemini).
        NO elimina los registros anteriores.
        """
        domain = [("active", "=", True), ("source_model", "=", "account.move")]
        r = self.browse()
        if partner_id:
            r |= self.search(
                domain + [("partner_id", "=", partner_id)], order="write_date desc"
            )
        if partner_name and not r:
            r |= self.search(
                domain + ["|",
                          ("correct_partner_name", "ilike", partner_name),
                          ("gemini_partner_name", "ilike", partner_name)],
                order="write_date desc",
            )
        return r[0] if r else self.browse()
    @api.model
    def find_all_for_emisor(self, partner_id=None, partner_name=None):
        """
        Devuelve TODOS los feedbacks para un emisor de MAS ANTIGUO a MAS RECIENTE.
        - El viejo aporta datos que el nuevo no tocó.
        - El nuevo sobreescribe los datos que sí cambió.
        Así no se pierde ninguna corrección de sesiones anteriores.
        """
        domain = [("active", "=", True), ("source_model", "=", "account.move")]
        r = self.browse()
        if partner_id:
            r |= self.search(
                domain + [("partner_id", "=", partner_id)], order="write_date asc"
            )
        if partner_name and not r:
            r |= self.search(
                domain + ["|",
                          ("correct_partner_name", "ilike", partner_name),
                          ("gemini_partner_name", "ilike", partner_name)],
                order="write_date asc",
            )
        return r
    @api.model
    def get_feedback_context_for_prompt(self, partner_id=None, source_model=None,
                                        partner_name=None):
        """Devuelve el contexto de aprendizaje para un emisor concreto."""
        domain = [("active", "=", True)]
        if source_model:
            domain.append(("source_model", "=", source_model))
        feedback = self.browse()
        if partner_id:
            feedback = self.search(domain + [("partner_id", "=", partner_id)],
                                   limit=1, order="write_date desc")
        if not feedback and partner_name:
            feedback = self.search(
                domain + ["|",
                          ("correct_partner_name", "ilike", partner_name),
                          ("gemini_partner_name", "ilike", partner_name)],
                limit=1, order="write_date desc",
            )
        if not feedback:
            return ""
        fb = feedback[0]
        emisor = (fb.correct_partner_name or fb.gemini_partner_name
                  or (fb.partner_id.name if fb.partner_id else "desconocido"))
        lines = [
            "\n\n=== INSTRUCCIONES OBLIGATORIAS BASADAS EN CORRECCIONES PREVIAS ===",
            f"El usuario ya ha corregido documentos del emisor '{emisor}'.",
            "Ajusta importes al documento actual, NO cambies account_code:",
        ]
        if fb.correct_lines_json:
            lines.append(f"  {fb.correct_lines_json}")
        if fb.notes:
            lines.append(f"\n  NOTAS: {fb.notes}")
        lines.append("\n=== FIN DE INSTRUCCIONES ===\n")
        return "\n".join(lines)
    @api.model
    def get_all_feedback_context_for_prompt(self):
        """
        Para cada emisor, pasa TODOS sus feedbacks de MAS ANTIGUO a MAS RECIENTE.
        Gemini los procesa en orden: el mas reciente prevalece sobre los anteriores campo a campo.
        Asi no se pierde ninguna correccion de sesiones distintas.
        NOTA: tax_id es un campo interno de Odoo. Python lo aplica directamente
        en _apply_feedback_taxes_to_invoice_lines sin que Gemini tenga que conocerlo.
        """
        feedbacks = self.search(
            [
                ("active", "=", True),
                ("correct_lines_json", "!=", False),
                ("correct_lines_json", "!=", ""),
            ],
            order="write_date asc",
            limit=50,
        )
        if not feedbacks:
            return ""
        # Agrupar por emisor manteniendo orden cronologico (asc = viejo primero)
        emisor_feedbacks = {}
        for fb in feedbacks:
            emisor = (
                fb.correct_partner_name
                or fb.gemini_partner_name
                or (fb.partner_id.name if fb.partner_id else None)
            )
            if not emisor:
                continue
            key = emisor.strip().lower()
            if key not in emisor_feedbacks:
                emisor_feedbacks[key] = (emisor, [])
            emisor_feedbacks[key][1].append(fb)
        if not emisor_feedbacks:
            return ""
        lines = [
            "\n\n=== INSTRUCCIONES OBLIGATORIAS POR EMISOR ===",
            "Para cada emisor se listan sus correcciones de MAS ANTIGUA a MAS RECIENTE.",
            "Debes procesar TODAS las correcciones de un emisor en ese orden.",
            "El registro MAS RECIENTE prevalece sobre los anteriores campo a campo.",
            "1. Lee el documento e identifica el emisor.",
            "2. Aplica TODAS sus correcciones en orden (la ultima manda).",
            "3. Si el emisor no aparece: deduce los datos normalmente.",
        ]
        for key, (emisor, fbs) in emisor_feedbacks.items():
            lines.append(f"\n=== Emisor: '{emisor}' ({len(fbs)} correcciones) ===")
            for idx, fb in enumerate(fbs):
                tag = "MAS RECIENTE - MAXIMA PRIORIDAD" if idx == len(fbs) - 1 else f"correccion {idx + 1}"
                lines.append(f"  -- [{tag}] --")
                lines.append(f"  {fb.correct_lines_json}")
                if fb.notes:
                    lines.append(f"  Notas: {fb.notes}")
        lines.append("\n=== FIN DE INSTRUCCIONES ===\n")
        return "\n".join(lines)
