# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import json
import logging
import os
import re
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openai
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None

try:
    import jsonschema
except ImportError:
    jsonschema = None


class AccountMove(models.Model):
    _inherit = "account.move"

    ai_invoice_file = fields.Binary(
        string="AI Invoice File",
        help="Upload invoice file to analyze with AI",
        copy=False,
    )
    ai_invoice_filename = fields.Char(string="AI Filename", copy=False)

    def action_import_invoice_with_ai(self):
        """Importar factura usando IA desde el botón en la factura"""
        self.ensure_one()

        if not self.ai_invoice_file:
            raise UserError(_("Please upload an invoice file first."))

        if self.state != "draft":
            raise UserError(_("You can only import AI data on draft invoices."))

        if self.move_type != "in_invoice":
            raise UserError(_("AI import is only available for vendor bills."))

        # Usar el wizard para procesar
        wizard = self.env["xtendoo.invoice.ai.wizard"].create({
            "upload": self.ai_invoice_file,
            "filename": self.ai_invoice_filename,
            "company_id": self.company_id.id,
            "journal_id": self.journal_id.id,
            "currency_id": self.currency_id.id if self.currency_id else False,
            "create_partner_if_missing": True,
            "attach_original": True,
        })

        # Crear job
        job = self.env["xtendoo.invoice.ai.job"].create({
            "filename": self.ai_invoice_filename,
            "state": "processing",
            "company_id": self.company_id.id,
            "user_id": self.env.user.id,
        })

        try:
            # Obtener credenciales
            credentials = wizard._get_openai_credentials()

            # Preparar imágenes
            images_b64 = wizard._prepare_images_for_openai()

            # Llamar a OpenAI
            openai_result = wizard._call_openai_vision(images_b64, credentials)

            # Validar schema
            wizard._validate_json_schema(openai_result["json_data"])

            # Actualizar la factura actual con los datos extraídos
            self._update_invoice_from_ai_data(openai_result["json_data"])

            # Adjuntar archivo original
            if self.ai_invoice_file:
                self.env["ir.attachment"].create({
                    "name": self.ai_invoice_filename or "invoice.pdf",
                    "datas": self.ai_invoice_file,
                    "res_model": "account.move",
                    "res_id": self.id,
                    "type": "binary",
                })

            # Actualizar job
            meta = openai_result["json_data"].get("meta", {})
            job.write({
                "state": "done",
                "invoice_id": self.id,
                "tokens_used": openai_result["tokens_used"],
                "processing_time": openai_result["processing_time"],
                "pages_processed": meta.get("pages_processed", len(images_b64)),
                "detected_language": meta.get("language"),
                "detected_country": meta.get("detected_country"),
                "supplier_name": openai_result["json_data"]["supplier"]["name"],
                "invoice_number": openai_result["json_data"]["invoice"]["supplier_invoice_number"],
                "invoice_amount": openai_result["json_data"]["totals"]["total"],
            })

            # Limpiar campos temporales
            self.write({
                "ai_invoice_file": False,
                "ai_invoice_filename": False,
            })

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Invoice data has been successfully imported from AI."),
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            # Actualizar job con error
            job.write({
                "state": "error",
                "error_message": str(e),
            })
            raise

    def action_quick_import_invoice_ai(self):
        """Abrir wizard de importación rápida desde la vista de lista"""
        return {
            "name": _("Import Invoice with AI"),
            "type": "ir.actions.act_window",
            "res_model": "xtendoo.invoice.ai.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_company_id": self.env.company.id,
                "default_create_partner_if_missing": True,
                "default_attach_original": True,
            },
        }

    def _update_invoice_from_ai_data(self, ai_data):
        """Actualizar factura existente con datos de IA"""
        supplier_data = ai_data["supplier"]
        invoice_data = ai_data["invoice"]
        lines_data = ai_data["lines"]
        totals_data = ai_data["totals"]

        # Obtener wizard para usar sus métodos auxiliares
        wizard = self.env["xtendoo.invoice.ai.wizard"].new({
            "company_id": self.company_id.id,
            "create_partner_if_missing": True,
        })

        # 1. Actualizar partner
        partner = wizard._find_or_create_partner(supplier_data)

        # 2. Actualizar datos de cabecera
        invoice_date = fields.Date.from_string(invoice_data["invoice_date"])
        due_date = None
        if invoice_data.get("due_date"):
            try:
                due_date = fields.Date.from_string(invoice_data["due_date"])
            except:
                pass

        vals = {
            "partner_id": partner.id,
            "invoice_date": invoice_date,
            "ref": invoice_data["supplier_invoice_number"],
        }

        if due_date:
            vals["invoice_date_due"] = due_date

        if invoice_data.get("notes"):
            vals["narration"] = invoice_data["notes"]

        self.write(vals)

        # 3. Eliminar líneas existentes (excepto las de impuestos)
        self.invoice_line_ids.filtered(lambda l: not l.display_type).unlink()

        # 4. Crear nuevas líneas
        default_account = wizard._get_default_purchase_account()
        lines_to_create = []

        for line_data in lines_data:
            product = None
            account = default_account

            # Buscar producto por código
            if line_data.get("product_code"):
                product = self.env["product.product"].search(
                    [("default_code", "=", line_data["product_code"])],
                    limit=1,
                )

            # Si hay producto, usar su cuenta
            if product:
                account = (
                    product.property_account_expense_id
                    or product.categ_id.property_account_expense_categ_id
                    or default_account
                )

            # Mapear impuestos
            taxes = self.env["account.tax"]
            for tax_name in line_data.get("taxes", []):
                tax = wizard._map_tax_by_name(tax_name)
                if tax:
                    taxes |= tax
                    _logger.info(f"Tax '{tax_name}' mapped to: {tax.name} (ID: {tax.id}, Amount: {tax.amount}%)")
                else:
                    _logger.warning(f"Tax '{tax_name}' not found, skipping")

            # Si no se encontró ningún impuesto, usar el impuesto de compra por defecto
            if not taxes and partner.property_account_position_id:
                taxes = partner.property_account_position_id.map_tax(
                    taxes, product=product, partner=partner
                )

            _logger.info(f"Creating line: {line_data['description']}, qty: {line_data['quantity']}, "
                        f"price: {line_data['unit_price']}, taxes: {taxes.mapped('name')}")

            line_vals = {
                "move_id": self.id,
                "name": line_data["description"],
                "quantity": line_data["quantity"],
                "price_unit": line_data["unit_price"],
                "account_id": account.id,
                "tax_ids": [(6, 0, taxes.ids)],
            }

            if product:
                line_vals["product_id"] = product.id

            lines_to_create.append((0, 0, line_vals))

        # Crear todas las líneas de una vez
        self.write({"invoice_line_ids": lines_to_create})

        # 5. Validar totales
        _logger.info(f"Invoice totals after recompute - Untaxed: {self.amount_untaxed}, "
                    f"Tax: {self.amount_tax}, Total: {self.amount_total}")

        tolerance = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_invoice_ai.tolerance", default=0.02)
        )

        diff_untaxed = abs(self.amount_untaxed - totals_data["untaxed"])
        diff_total = abs(self.amount_total - totals_data["total"])

        if diff_untaxed > tolerance or diff_total > tolerance:
            _logger.warning(
                f"Total mismatch detected! AI: Untaxed={totals_data['untaxed']}, Total={totals_data['total']} | "
                f"Calculated: Untaxed={self.amount_untaxed}, Total={self.amount_total}"
            )
            # Añadir una nota en la factura
            current_narration = self.narration or ""
            warning_note = _(
                "\n\n⚠️ WARNING: Total mismatch detected!\n"
                "AI extracted: Untaxed=%.2f, Total=%.2f\n"
                "Calculated: Untaxed=%.2f, Total=%.2f\n"
                "Please review the invoice manually."
            ) % (
                totals_data["untaxed"],
                totals_data["total"],
                self.amount_untaxed,
                self.amount_total,
            )
            self.narration = current_narration + warning_note

