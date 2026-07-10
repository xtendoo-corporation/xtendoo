# © 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging
import re
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = ["purchase.order", "xtendoo.ai.connector.mixin"]

    gemini_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Gemini Attachment",
        help="Attachment to be processed by Gemini AI",
        copy=False,
    )
    gemini_auto_processed = fields.Boolean(
        string="Auto Processed by Gemini",
        help="Indicates if this order was automatically processed by Gemini AI",
        default=False,
        copy=False,
    )

    # Tracking: valores que extrajo Gemini originalmente
    gemini_extracted_partner = fields.Char(string="Proveedor extraído por Gemini", copy=False)
    gemini_extracted_date = fields.Char(string="Fecha extraída por Gemini", copy=False)
    gemini_extracted_ref = fields.Char(string="Referencia extraída por Gemini", copy=False)
    gemini_extracted_lines_count = fields.Integer(
        string="Nº líneas extraídas por Gemini", default=0, copy=False,
    )

    # Flag: se activa cuando Gemini procesa el pedido.
    # El usuario lo desactiva pulsando "Enseñar a Gemini".
    gemini_has_corrections = fields.Boolean(
        string="Pendiente de enseñar a Gemini",
        default=False,
        copy=False,
    )

    def action_teach_gemini(self):
        """
        Guarda el feedback del documento correcto para este proveedor.
        Las líneas reflejan la última corrección del usuario.
        """
        self.ensure_one()

        emisor_name = (
            self.partner_id.name if self.partner_id
            else self.gemini_extracted_partner or ""
        )

        lines_example = []
        for line in self.order_line:
            tax_id_ref = line.taxes_id[0].id if line.taxes_id else None
            tax_name = line.taxes_id[0].name if line.taxes_id else None
            tax_percent = line.taxes_id[0].amount if line.taxes_id else None
            lines_example.append({
                "description": line.name or "",
                "quantity": line.product_qty,
                "unit_price": line.price_unit,
                "tax_id": tax_id_ref,
                "tax_name": tax_name,
                "tax_percent": tax_percent,
                "product_code": line.product_id.default_code if line.product_id else "",
            })

        notes = (
            f"Proveedor: '{emisor_name}'. Pedido de compra corregido. "
            f"Python aplica los impuestos directamente usando tax_id."
        )

        correct_lines_json = json.dumps(lines_example, ensure_ascii=False, indent=2)

        new_vals = {
            "source_model": "purchase.order",
            "purchase_order_id": self.id,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "gemini_partner_name": self.gemini_extracted_partner or "",
            "gemini_date": self.gemini_extracted_date or "",
            "gemini_description": self.gemini_extracted_ref or "",
            "correct_partner_name": emisor_name,
            "correct_date": str(self.date_order) if self.date_order else "",
            "correct_description": self.partner_ref or "",
            "correct_lines_json": correct_lines_json,
            "notes": notes,
        }

        self.env["gemini.feedback"].create(new_vals)

        self.gemini_has_corrections = False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Gemini aprendió"),
                "message": _(
                    "Las correcciones han sido guardadas. "
                    "La próxima vez que se suba un documento de '%s', "
                    "Gemini usará estos datos automáticamente."
                ) % (emisor_name or _("este emisor")),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders.filtered(lambda record: record.state == "draft"):
            order._auto_scan_if_configured()
        return orders

    @api.model
    def create_document_from_attachment(self, name=None, attachment_ids=None):
        """
        Odoo uploader llama: create_document_from_attachment("", [ids])
        Crea un pedido de compra (state='draft') y lo escanea con Gemini AI.
        """
        if not attachment_ids:
            raise UserError(_("No attachment was provided."))

        attachments = self.env['ir.attachment'].browse(attachment_ids)
        created_orders = self.env['purchase.order']

        auto_scan_mode = (
            self.env["ir.config_parameter"].sudo()
            .get_param("xtendoo_purchase_import_ai.gemini_auto_scan", "disabled")
        )
        summary_mode = (auto_scan_mode == 'summary')

        for attachment in attachments:
            order = self.create({
                'state': 'draft',
                'date_order': fields.Datetime.now(),
            })
            attachment.write({'res_model': 'purchase.order', 'res_id': order.id})
            created_orders |= order
            _logger.info(f"Created purchase order {order.id} from attachment {attachment.id}")
            try:
                order._process_with_gemini(summary_mode=summary_mode, auto_mode=True)
            except Exception as e:
                _logger.warning(f"Gemini AI failed for order {order.id}: {e}")

        if created_orders:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase Order'),
                'res_model': 'purchase.order',
                'res_id': created_orders[0].id,
                'views': [[self.env.ref('purchase.purchase_order_form').id, 'form']],
                'target': 'current',
            }
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def write(self, vals):
        gemini_internal_fields = {
            'gemini_has_corrections', 'gemini_auto_processed',
            'gemini_extracted_partner', 'gemini_extracted_date',
            'gemini_extracted_ref', 'gemini_extracted_lines_count',
            'gemini_attachment_id',
        }
        user_changed_fields = set(vals.keys()) - gemini_internal_fields
        if user_changed_fields and 'gemini_has_corrections' not in vals:
            for rec in self:
                if rec.gemini_auto_processed:
                    vals['gemini_has_corrections'] = True
                    break
        res = super().write(vals)
        if 'message_main_attachment_id' in vals or 'state' in vals:
            for order in self:
                if order.state == 'draft':
                    order._auto_scan_if_configured()
        return res

    def _auto_scan_if_configured(self):
        self.ensure_one()
        if self.gemini_auto_processed or self.state != 'draft':
            return
        if self.order_line:
            return

        auto_scan_mode = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_purchase_import_ai.gemini_auto_scan", "disabled")
        )

        if auto_scan_mode == 'disabled':
            return

        attachment = self._get_ai_attachment()
        if not attachment:
            return

        try:
            summary_mode = (auto_scan_mode == 'summary')
            _logger.info(f"Auto-scanning order {self.id} with mode: {auto_scan_mode}")
            self._process_with_gemini(summary_mode=summary_mode, auto_mode=True)
            self.gemini_auto_processed = True
        except Exception as e:
            _logger.warning(f"Auto-scan failed for order {self.id}: {str(e)}")

    def action_import_gemini_full(self):
        return self._process_with_gemini(summary_mode=False)

    def action_import_gemini_summarized(self):
        return self._process_with_gemini(summary_mode=True)

    def _process_with_gemini(self, summary_mode=False, auto_mode=False):
        self.ensure_one()
        if self.state != "draft":
            if not auto_mode:
                raise UserError(_("You can only import AI data on draft orders."))
            return

        attachment = self._get_ai_attachment()
        if not attachment:
            if not auto_mode:
                raise UserError(_("Please attach a PDF or image file first."))
            return

        ai_provider = self._get_ai_provider()
        file_content = base64.b64decode(attachment.datas)
        mime_type = attachment.mimetype

        prompt = self._get_gemini_prompt(summary_mode=summary_mode)

        try:
            raw_text = ai_provider.send_prompt(
                prompt,
                files=[{"data": file_content, "mime_type": mime_type}],
            )

            if not raw_text:
                raise UserError(_("The AI returned an empty response."))

            json_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
            if json_match:
                raw_text = json_match.group(1)
            else:
                json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                if json_match:
                    raw_text = json_match.group(1)

            ai_data = json.loads(raw_text)
            self._apply_gemini_data(ai_data, summary_mode=summary_mode)

            if not auto_mode:
                self.message_post(
                    body=_("✅ Order data successfully imported from Gemini AI (%s mode)!")
                    % (_("Full") if not summary_mode else _("Summarized")),
                    attachments=[(attachment.name, attachment.datas)],
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Success"),
                        "message": _("Order data imported successfully!"),
                        "type": "success",
                        "sticky": False,
                        "next": {"type": "ir.actions.client", "tag": "reload"},
                    },
                }
        except Exception as e:
            _logger.error(f"Gemini AI error: {str(e)}", exc_info=True)
            if not auto_mode:
                raise UserError(_("Error processing with Gemini AI: %s") % str(e))

    def _get_ai_attachment(self):
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "purchase.order"),
                ("res_id", "=", self.id),
                ("mimetype", "in", ["application/pdf", "image/jpeg", "image/png", "image/jpg"]),
            ],
            limit=1,
            order="create_date desc",
        )
        return attachments[0] if attachments else None

    def _get_gemini_prompt(self, summary_mode=False):
        feedback_context = self.env["gemini.feedback"].get_all_feedback_context_for_prompt()
        prompt = ""
        if feedback_context:
            prompt += feedback_context + "\n\n"

        prompt += (
            "Extract all data from this purchase order document and return it in JSON format.\n\n"
            "STEPS:\n"
            "1. Identify the supplier name from the document.\n"
            "2. Check if that supplier appears in the PREVIOUS INSTRUCTIONS above.\n"
            "3. If found: use associated instructions for mapping. "
            "NOTE: taxes are managed by the system automatically.\n"
            "4. If not found: extract data normally.\n\n"
            "Required JSON structure:\n"
            "{\n"
            '    "supplier": {"name": "...", "vat": "...", "address": "..."},\n'
            '    "order": {"partner_ref": "...", "date_order": "YYYY-MM-DD", "currency": "EUR"},\n'
            '    "lines": [{"description": "...", "quantity": 1.0, "unit_price": 100.00, "tax_percent": 21.0, "product_code": "..."}],\n'
            '    "totals": {"untaxed": 100.00, "tax": 21.00, "total": 121.00}\n'
            "}\n"
        )
        if summary_mode:
            prompt += "\nIMPORTANT: In 'lines', group all items by VAT percentage. One line per VAT group."
        else:
            prompt += "\nIMPORTANT: Extract ALL individual line items from the document."
        prompt += "\nReturn ONLY the JSON object, no markdown, no extra text."
        return prompt

    def _apply_gemini_data(self, data, summary_mode=False):
        self.ensure_one()
        supplier_data = data.get("supplier", {})
        order_data = data.get("order", {})

        partner = self._find_partner(supplier_data)
        if not partner and supplier_data.get("name"):
            partner = self.env["res.partner"].create({
                "name": supplier_data.get("name", "Unknown Supplier"),
                "vat": supplier_data.get("vat", False),
                "street": supplier_data.get("address", False),
                "supplier_rank": 1,
            })
        if partner:
            self.partner_id = partner

        if order_data.get("partner_ref"):
            self.partner_ref = order_data["partner_ref"]
        if order_data.get("date_order"):
            self.date_order = order_data["date_order"]

        if order_data.get("currency"):
            currency = self.env["res.currency"].search(
                [("name", "=", order_data["currency"].upper())], limit=1
            )
            if currency:
                self.currency_id = currency

        lines_data = data.get("lines", [])
        self.order_line = [(5, 0, 0)]
        lines_to_create = []
        for line in lines_data:
            tax = self._find_tax(line.get("tax_percent"))
            product = self._find_product(line.get("product_code"), line.get("description"))

            lines_to_create.append((0, 0, {
                "name": line.get("description", "Imported line"),
                "product_qty": line.get("quantity", 1.0),
                "price_unit": line.get("unit_price", 0.0),
                "product_id": product.id if product else False,
                "taxes_id": [(6, 0, [tax.id])] if tax else [],
                "date_planned": self.date_order or fields.Date.context_today(self),
            }))
        self.order_line = lines_to_create

        # Apply feedback taxes if applicable (similar to invoice but adapted)
        self._apply_feedback_taxes_to_order_lines()

        self.write({
            "gemini_extracted_partner": supplier_data.get("name", ""),
            "gemini_extracted_date": order_data.get("date_order", ""),
            "gemini_extracted_ref": order_data.get("partner_ref", ""),
            "gemini_extracted_lines_count": len(self.order_line),
            "gemini_auto_processed": True,
            "gemini_has_corrections": True,
        })

    def _apply_feedback_taxes_to_order_lines(self):
        if not self.partner_id:
            return

        all_feedbacks = self.env["gemini.feedback"].find_all_for_emisor(
            partner_id=self.partner_id.id,
            partner_name=self.partner_id.name,
        )
        if not all_feedbacks:
            return

        line_tax_map = {}
        default_tax_info = None

        for fb in all_feedbacks:
            if not fb.correct_lines_json:
                continue
            try:
                flines = json.loads(fb.correct_lines_json)
            except Exception:
                continue
            for fl in flines:
                if not fl.get("tax_id"):
                    continue
                tax_info = {
                    "tax_id": int(fl["tax_id"]),
                    "tax_name": fl.get("tax_name", ""),
                }
                desc = (fl.get("description") or "").strip().lower()
                if desc:
                    line_tax_map[desc] = tax_info
                default_tax_info = tax_info

        if not line_tax_map and not default_tax_info:
            return

        tax_cache = {}

        def resolve_tax(tax_id, tax_name):
            key = (tax_id, tax_name)
            if key in tax_cache:
                return tax_cache[key]
            tax = None
            if tax_id:
                tax = self.env["account.tax"].browse(tax_id).exists()
            if not tax and tax_name:
                tax = self.env["account.tax"].search([
                    ("name", "=", tax_name),
                    ("type_tax_use", "=", "purchase"),
                ], limit=1)
            tax_cache[key] = tax
            return tax

        for line in self.order_line:
            desc_key = (line.name or "").strip().lower()
            tax_info = line_tax_map.get(desc_key)
            if not tax_info and desc_key:
                for fb_desc, ti in line_tax_map.items():
                    if fb_desc and (fb_desc in desc_key or desc_key in fb_desc):
                        tax_info = ti
                        break
            if not tax_info:
                tax_info = default_tax_info

            if not tax_info:
                continue

            tax = resolve_tax(tax_info["tax_id"], tax_info["tax_name"])
            if tax:
                line.taxes_id = [(6, 0, [tax.id])]

    def _find_partner(self, supplier_data):
        vat = supplier_data.get("vat")
        name = supplier_data.get("name")
        if vat:
            vat_clean = re.sub(r"[^A-Z0-9]", "", vat.upper())
            partner = self.env["res.partner"].sudo().search([("vat", "ilike", vat_clean)], limit=1)
            if partner:
                return partner
        if name:
            partner = self.env["res.partner"].search([("name", "ilike", name)], limit=1)
            if partner:
                return partner
        return None

    def _find_tax(self, percent):
        if percent is None:
            return None
        return self.env["account.tax"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("type_tax_use", "=", "purchase"),
                ("amount", "=", float(percent)),
            ],
            limit=1,
        )

    def _find_product(self, code, description):
        if code:
            product = self.env["product.product"].search([("default_code", "=", code)], limit=1)
            if product:
                return product
        if description:
            product = self.env["product.product"].search([("name", "ilike", description)], limit=1)
            if product:
                return product
        return self.env['product.product'].search([('name', '=', 'Service')], limit=1) # Fallback or something better?
