# © 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import json
import logging
import os
import re
import time
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import openai
    from openai import OpenAI
except ImportError:
    _logger.warning("openai library not found. Please install it with: pip install openai")
    OpenAI = None

try:
    from pdf2image import convert_from_bytes
except ImportError:
    _logger.warning("pdf2image library not found. Please install it with: pip install pdf2image")
    convert_from_bytes = None

try:
    import jsonschema
except ImportError:
    _logger.warning("jsonschema library not found. Please install it with: pip install jsonschema")
    jsonschema = None


# JSON Schema para extracción estructurada
INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "supplier": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "vat": {"type": ["string", "null"]},
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
                "street": {"type": ["string", "null"]},
                "city": {"type": ["string", "null"]},
                "zip": {"type": ["string", "null"]},
                "country_code": {"type": ["string", "null"]},
            },
            "required": ["name"],
        },
        "invoice": {
            "type": "object",
            "properties": {
                "supplier_invoice_number": {"type": "string"},
                "invoice_date": {"type": "string"},
                "due_date": {"type": ["string", "null"]},
                "currency": {"type": "string"},
                "payment_terms": {"type": ["string", "null"]},
                "notes": {"type": ["string", "null"]},
            },
            "required": ["supplier_invoice_number", "invoice_date", "currency"],
        },
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "uom": {"type": ["string", "null"]},
                    "unit_price": {"type": "number"},
                    "taxes": {"type": "array", "items": {"type": "string"}},
                    "product_code": {"type": ["string", "null"]},
                    "analytic_tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["description", "quantity", "unit_price", "taxes"],
            },
        },
        "totals": {
            "type": "object",
            "properties": {
                "untaxed": {"type": "number"},
                "tax": {"type": "number"},
                "total": {"type": "number"},
            },
            "required": ["untaxed", "tax", "total"],
        },
        "meta": {
            "type": "object",
            "properties": {
                "language": {"type": ["string", "null"]},
                "detected_country": {"type": ["string", "null"]},
                "pages_processed": {"type": "integer"},
            },
        },
    },
    "required": ["supplier", "invoice", "lines", "totals", "meta"],
}

EXTRACTION_PROMPT = """Eres un extractor estricto de datos de facturas. Devuelve exclusivamente JSON válido que siga exactamente el siguiente esquema.

NO incluyas ningún texto fuera del JSON. Si algún dato no aparece, usa null o listas vacías.

Instrucciones:
- Estandariza moneda a ISO 4217 (EUR, USD, GBP, etc.)
- Fechas en formato YYYY-MM-DD
- Numéricos con punto decimal (no comas)
- Detecta proveedor (nombre, NIF/CIF, email, teléfono, dirección)
- Número de factura del proveedor
- Fecha de factura y vencimiento
- Divisa
- Líneas: descripción, cantidad, precio unitario, impuestos aplicados
- Totales: base imponible, impuestos, total
- Si hay varios tipos de IVA (21%, 10%, 4%), devuélvelos por línea
- No inventes valores que no aparezcan en la imagen

Devuelve el JSON siguiendo este esquema exacto:
"""


class XtendooInvoiceAIWizard(models.TransientModel):
    """Wizard para importar facturas de proveedor usando OpenAI"""

    _name = "xtendoo.invoice.ai.wizard"
    _description = "Invoice AI Import Wizard"

    upload = fields.Binary(
        string="Invoice File",
        required=True,
        help="Upload PDF or image (JPG, PNG) of vendor invoice",
    )
    filename = fields.Char(string="Filename")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Purchase Journal",
        domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="Leave empty to use default purchase journal",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Force Currency",
        help="Optional: force currency instead of detecting from invoice",
    )
    create_partner_if_missing = fields.Boolean(
        string="Create Partner if Missing",
        default=True,
        help="Create supplier automatically if not found",
    )
    attach_original = fields.Boolean(
        string="Attach Original File",
        default=True,
        help="Attach uploaded file to created invoice",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("processing", "Processing")],
        default="draft",
    )

    def _get_openai_credentials(self):
        """Obtener credenciales de OpenAI desde config"""
        icp = self.env["ir.config_parameter"].sudo()
        api_key = icp.get_param("xtendoo_invoice_ai.openai_api_key") or os.environ.get(
            "OPENAI_API_KEY"
        )
        base_url = icp.get_param("xtendoo_invoice_ai.openai_base")
        model = icp.get_param("xtendoo_invoice_ai.openai_model", default="gpt-4o")
        max_pages = int(icp.get_param("xtendoo_invoice_ai.max_pages", default=10))
        temperature = float(icp.get_param("xtendoo_invoice_ai.temperature", default=0.0))

        if not api_key:
            raise UserError(
                _(
                    "OpenAI API Key not configured. "
                    "Please go to Settings → General → Integrations → OpenAI and configure it."
                )
            )

        return {
            "api_key": api_key,
            "base_url": base_url or None,
            "model": model,
            "max_pages": max_pages,
            "temperature": temperature,
        }

    def _convert_pdf_to_images(self, pdf_bytes, max_pages=10):
        """Convertir PDF a imágenes base64"""
        if not convert_from_bytes:
            raise UserError(_("pdf2image library not installed. Please install it."))

        try:
            images = convert_from_bytes(pdf_bytes, fmt="jpeg", dpi=150)
            images_b64 = []
            for idx, img in enumerate(images[:max_pages]):
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                images_b64.append(img_b64)
            return images_b64
        except Exception as e:
            _logger.error(f"Error converting PDF to images: {e}")
            raise UserError(_("Failed to convert PDF to images: %s") % str(e))

    def _prepare_images_for_openai(self):
        """Preparar imágenes para enviar a OpenAI"""
        if not self.upload:
            raise UserError(_("No file uploaded"))

        file_data = base64.b64decode(self.upload)
        filename_lower = (self.filename or "").lower()

        # Detectar tipo de archivo
        if filename_lower.endswith(".pdf"):
            creds = self._get_openai_credentials()
            images_b64 = self._convert_pdf_to_images(file_data, creds["max_pages"])
        elif filename_lower.endswith((".jpg", ".jpeg", ".png")):
            images_b64 = [base64.b64encode(file_data).decode("utf-8")]
        else:
            raise UserError(_("Unsupported file format. Please upload PDF, JPG or PNG."))

        return images_b64

    def _call_openai_vision(self, images_b64, credentials):
        """Llamar a OpenAI Vision API para extracción"""
        if not OpenAI:
            raise UserError(_("openai library not installed. Please install it."))

        client_params = {"api_key": credentials["api_key"]}
        if credentials["base_url"]:
            client_params["base_url"] = credentials["base_url"]

        client = OpenAI(**client_params)

        # Preparar contenido del mensaje
        content = [
            {"type": "text", "text": EXTRACTION_PROMPT + "\n\n" + json.dumps(INVOICE_SCHEMA, indent=2)}
        ]

        for img_b64 in images_b64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}",
                        "detail": "high",
                    },
                }
            )

        messages = [
            {
                "role": "system",
                "content": "You are a precise invoice data extraction assistant. Always return valid JSON.",
            },
            {"role": "user", "content": content},
        ]

        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=credentials["model"],
                messages=messages,
                temperature=credentials["temperature"],
                response_format={"type": "json_object"},
            )
            processing_time = time.time() - start_time

            result_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0

            _logger.info(f"OpenAI API call completed in {processing_time:.2f}s, tokens: {tokens_used}")

            return {
                "json_data": json.loads(result_text),
                "tokens_used": tokens_used,
                "processing_time": processing_time,
            }

        except openai.APIError as e:
            _logger.error(f"OpenAI API error: {e}")
            raise UserError(_("OpenAI API error: %s") % str(e))
        except json.JSONDecodeError as e:
            _logger.error(f"Invalid JSON from OpenAI: {e}")
            raise UserError(_("OpenAI returned invalid JSON: %s") % str(e))
        except Exception as e:
            _logger.error(f"Unexpected error calling OpenAI: {e}")
            raise UserError(_("Unexpected error: %s") % str(e))

    def _validate_json_schema(self, data):
        """Validar JSON contra el schema"""
        if not jsonschema:
            _logger.warning("jsonschema not installed, skipping validation")
            return True

        try:
            jsonschema.validate(instance=data, schema=INVOICE_SCHEMA)
            return True
        except jsonschema.ValidationError as e:
            _logger.error(f"JSON schema validation failed: {e}")
            raise UserError(_("Invalid data structure from AI: %s") % str(e.message))

    def _normalize_vat(self, vat):
        """Normalizar VAT/NIF"""
        if not vat:
            return ""
        return vat.upper().replace(" ", "").replace("-", "").replace(".", "")

    def _find_or_create_partner(self, supplier_data):
        """Buscar o crear proveedor - PRIORIDAD: buscar por NIF/VAT"""
        Partner = self.env["res.partner"]

        vat_normalized = self._normalize_vat(supplier_data.get("vat"))
        supplier_name = supplier_data.get("name", "").strip()

        _logger.info(f"Searching for supplier: Name='{supplier_name}', VAT='{vat_normalized}'")

        # PASO 1: Buscar por VAT (campo clave, prioridad máxima)
        if vat_normalized:
            # Búsqueda exacta con normalización
            partner = Partner.search(
                [
                    ("vat", "=ilike", vat_normalized),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if partner:
                _logger.info(f"Supplier FOUND by VAT: {partner.name} (ID: {partner.id})")
                # Actualizar datos si es necesario
                self._update_partner_data_if_needed(partner, supplier_data)
                return partner

            # Búsqueda alternativa: quitar prefijo de país (ej: ES12345678A -> 12345678A)
            vat_without_country = re.sub(r'^[A-Z]{2}', '', vat_normalized)
            if vat_without_country != vat_normalized:
                partner = Partner.search(
                    [
                        "|",
                        ("vat", "=ilike", vat_without_country),
                        ("vat", "=ilike", vat_normalized),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
                if partner:
                    _logger.info(f"Supplier FOUND by VAT (without country prefix): {partner.name} (ID: {partner.id})")
                    self._update_partner_data_if_needed(partner, supplier_data)
                    return partner

            # Búsqueda con variaciones: buscar si el VAT está contenido
            all_partners = Partner.search([
                ("vat", "!=", False),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ])
            for partner in all_partners:
                partner_vat_normalized = self._normalize_vat(partner.vat)
                if partner_vat_normalized and (
                    partner_vat_normalized == vat_normalized
                    or partner_vat_normalized == vat_without_country
                    or vat_normalized in partner_vat_normalized
                    or vat_without_country in partner_vat_normalized
                ):
                    _logger.info(f"Supplier FOUND by VAT (fuzzy match): {partner.name} (ID: {partner.id})")
                    self._update_partner_data_if_needed(partner, supplier_data)
                    return partner

            _logger.warning(f"No supplier found with VAT: {vat_normalized}")

        # PASO 2: Buscar por nombre (solo si no hay VAT o no se encontró)
        if supplier_name:
            partner = Partner.search(
                [
                    ("name", "=ilike", supplier_name),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if partner:
                _logger.info(f"Supplier FOUND by name: {partner.name} (ID: {partner.id})")
                # Si encontramos por nombre pero tiene VAT diferente, avisar
                if partner.vat and vat_normalized and self._normalize_vat(partner.vat) != vat_normalized:
                    _logger.warning(
                        f"Supplier found by name but VAT mismatch! "
                        f"Found VAT: {partner.vat}, Invoice VAT: {vat_normalized}"
                    )
                else:
                    self._update_partner_data_if_needed(partner, supplier_data)
                return partner

        # PASO 3: No encontrado - verificar si se debe crear
        if not self.create_partner_if_missing:
            error_msg = _(
                "Supplier not found in database:\n"
                "- Name: %s\n"
                "- VAT/NIF: %s\n\n"
                "Automatic creation is disabled. Please:\n"
                "1. Enable 'Create Partner if Missing', or\n"
                "2. Create the supplier manually first"
            ) % (supplier_name, vat_normalized or _("Not provided"))
            raise UserError(error_msg)

        # PASO 4: Crear nuevo proveedor
        _logger.info(f"Creating NEW supplier: {supplier_name} with VAT: {vat_normalized}")

        # Preparar datos del partner
        country_code = supplier_data.get("country_code")
        country = None
        if country_code:
            country = self.env["res.country"].search([("code", "=ilike", country_code)], limit=1)

        partner_vals = {
            "name": supplier_name,
            "supplier_rank": 1,
            "company_id": self.company_id.id,
        }

        if vat_normalized:
            partner_vals["vat"] = vat_normalized
        if supplier_data.get("email"):
            partner_vals["email"] = supplier_data["email"]
        if supplier_data.get("phone"):
            partner_vals["phone"] = supplier_data["phone"]
        if supplier_data.get("street"):
            partner_vals["street"] = supplier_data["street"]
        if supplier_data.get("city"):
            partner_vals["city"] = supplier_data["city"]
        if supplier_data.get("zip"):
            partner_vals["zip"] = supplier_data["zip"]
        if country:
            partner_vals["country_id"] = country.id

        partner = Partner.create(partner_vals)
        _logger.info(f"✓ New supplier created: {partner.name} (ID: {partner.id}, VAT: {partner.vat})")

        return partner

    def _update_partner_data_if_needed(self, partner, supplier_data):
        """Actualizar datos del proveedor si están vacíos y vienen en la factura"""
        update_vals = {}

        # Solo actualizar campos vacíos
        if not partner.email and supplier_data.get("email"):
            update_vals["email"] = supplier_data["email"]
        if not partner.phone and supplier_data.get("phone"):
            update_vals["phone"] = supplier_data["phone"]
        if not partner.street and supplier_data.get("street"):
            update_vals["street"] = supplier_data["street"]
        if not partner.city and supplier_data.get("city"):
            update_vals["city"] = supplier_data["city"]
        if not partner.zip and supplier_data.get("zip"):
            update_vals["zip"] = supplier_data["zip"]
        if not partner.country_id and supplier_data.get("country_code"):
            country = self.env["res.country"].search(
                [("code", "=ilike", supplier_data["country_code"])], limit=1
            )
            if country:
                update_vals["country_id"] = country.id

        # Asegurar que tiene supplier_rank
        if partner.supplier_rank == 0:
            update_vals["supplier_rank"] = 1

        if update_vals:
            partner.write(update_vals)
            _logger.info(f"Updated partner {partner.name} with data from invoice: {list(update_vals.keys())}")

    def _get_or_default_journal(self):
        """Obtener diario de compras"""
        if self.journal_id:
            return self.journal_id

        journal = self.env["account.journal"].search(
            [
                ("type", "=", "purchase"),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        if not journal:
            raise UserError(_("No purchase journal found for company %s") % self.company_id.name)

        return journal

    def _get_currency(self, currency_code):
        """Obtener divisa desde código ISO"""
        if self.currency_id:
            return self.currency_id

        currency = self.env["res.currency"].search([("name", "=ilike", currency_code)], limit=1)

        if not currency:
            _logger.warning(f"Currency {currency_code} not found, using company currency")
            currency = self.company_id.currency_id

        return currency

    def _map_tax_by_name(self, tax_name):
        """Mapear impuesto por nombre"""
        if not tax_name:
            return self.env["account.tax"]

        tax_name_lower = tax_name.lower().strip()

        # Extraer porcentaje numérico del nombre (ej: "21%", "21.0%", "IVA 21%")
        percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*%?', tax_name)

        if percentage_match:
            percentage = float(percentage_match.group(1))
            _logger.info(f"Extracted percentage {percentage} from tax name '{tax_name}'")

            # Buscar impuesto con ese porcentaje exacto
            tax = self.env["account.tax"].search(
                [
                    ("amount", "=", percentage),
                    ("type_tax_use", "=", "purchase"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if tax:
                _logger.info(f"Found tax by percentage: {tax.name} (ID: {tax.id}, Amount: {tax.amount}%)")
                return tax

            # Si no se encuentra exacto, buscar el más cercano
            all_purchase_taxes = self.env["account.tax"].search(
                [
                    ("type_tax_use", "=", "purchase"),
                    ("company_id", "=", self.company_id.id),
                ]
            )

            # Encontrar el impuesto con el porcentaje más cercano
            closest_tax = None
            min_diff = float('inf')
            for tax in all_purchase_taxes:
                diff = abs(tax.amount - percentage)
                if diff < min_diff:
                    min_diff = diff
                    closest_tax = tax

            if closest_tax and min_diff <= 1.0:  # Tolerancia de 1%
                _logger.info(f"Found closest tax: {closest_tax.name} (ID: {closest_tax.id}, Amount: {closest_tax.amount}%)")
                return closest_tax

        # Búsquedas comunes para España (fallback)
        tax_mappings = {
            "iva 21": [("name", "ilike", "21"), ("type_tax_use", "=", "purchase")],
            "iva 10": [("name", "ilike", "10"), ("type_tax_use", "=", "purchase")],
            "iva 4": [("name", "ilike", "4"), ("type_tax_use", "=", "purchase")],
            "iva 0": [("name", "ilike", "0"), ("type_tax_use", "=", "purchase")],
        }

        # Buscar por mapeos conocidos
        for key, domain in tax_mappings.items():
            if key in tax_name_lower:
                tax = self.env["account.tax"].search(
                    domain + [("company_id", "=", self.company_id.id)],
                    limit=1,
                )
                if tax:
                    return tax

        # Búsqueda genérica
        tax = self.env["account.tax"].search(
            [
                ("name", "ilike", tax_name),
                ("type_tax_use", "=", "purchase"),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        if not tax:
            _logger.warning(f"Tax '{tax_name}' not found after all search attempts")

        return tax

    def _get_default_purchase_account(self):
        """Obtener cuenta de compras por defecto"""
        # En Odoo 18, account.account no tiene company_id, buscar sin filtro de empresa
        account = self.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )
        if not account:
            raise UserError(_("No expense account found. Please configure your chart of accounts."))
        return account

    def _create_invoice_from_data(self, ai_data):
        """Crear factura de proveedor desde datos de IA"""
        supplier_data = ai_data["supplier"]
        invoice_data = ai_data["invoice"]
        lines_data = ai_data["lines"]
        totals_data = ai_data["totals"]

        # 1. Partner
        partner = self._find_or_create_partner(supplier_data)

        # 2. Diario
        journal = self._get_or_default_journal()

        # 3. Divisa
        currency = self._get_currency(invoice_data["currency"])

        # 4. Fechas
        invoice_date = fields.Date.from_string(invoice_data["invoice_date"])
        due_date = None
        if invoice_data.get("due_date"):
            try:
                due_date = fields.Date.from_string(invoice_data["due_date"])
            except:
                pass

        # 5. Crear factura
        invoice_vals = {
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "journal_id": journal.id,
            "currency_id": currency.id,
            "company_id": self.company_id.id,
            "invoice_date": invoice_date,
            "ref": invoice_data["supplier_invoice_number"],
        }

        if due_date:
            invoice_vals["invoice_date_due"] = due_date

        if invoice_data.get("notes"):
            invoice_vals["narration"] = invoice_data["notes"]

        invoice = self.env["account.move"].create(invoice_vals)

        # 6. Líneas
        default_account = self._get_default_purchase_account()

        # Preparar todas las líneas antes de crearlas
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
                tax = self._map_tax_by_name(tax_name)
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
                "move_id": invoice.id,
                "name": line_data["description"],
                "quantity": line_data["quantity"],
                "price_unit": line_data["unit_price"],
                "account_id": account.id,
                "tax_ids": [(6, 0, taxes.ids)],
            }

            if product:
                line_vals["product_id"] = product.id

            lines_to_create.append((0, 0, line_vals))

        # Crear todas las líneas de una vez usando write
        # Esto permite que Odoo genere automáticamente las líneas de impuestos
        invoice.write({"invoice_line_ids": lines_to_create})

        # 7. Validar totales
        # En Odoo 18, forzar el recálculo es tan simple como acceder a los campos computados
        # El ORM se encarga de recalcular automáticamente
        _logger.info(f"Invoice totals after recompute - Untaxed: {invoice.amount_untaxed}, "
                    f"Tax: {invoice.amount_tax}, Total: {invoice.amount_total}")

        tolerance = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("xtendoo_invoice_ai.tolerance", default=0.02)
        )

        diff_untaxed = abs(invoice.amount_untaxed - totals_data["untaxed"])
        diff_total = abs(invoice.amount_total - totals_data["total"])

        if diff_untaxed > tolerance or diff_total > tolerance:
            _logger.warning(
                f"Total mismatch detected! AI: Untaxed={totals_data['untaxed']}, Total={totals_data['total']} | "
                f"Calculated: Untaxed={invoice.amount_untaxed}, Total={invoice.amount_total}"
            )
            # En lugar de lanzar error, añadir una nota en la factura
            current_narration = invoice.narration or ""
            warning_note = _(
                "\n\n⚠️ WARNING: Total mismatch detected!\n"
                "AI extracted: Untaxed=%.2f, Total=%.2f\n"
                "Calculated: Untaxed=%.2f, Total=%.2f\n"
                "Please review the invoice manually."
            ) % (
                totals_data["untaxed"],
                totals_data["total"],
                invoice.amount_untaxed,
                invoice.amount_total,
            )
            invoice.narration = current_narration + warning_note

        return invoice

    def action_analyze_and_create(self):
        """Acción principal: analizar y crear factura"""
        self.ensure_one()

        # Crear job
        job = self.env["xtendoo.invoice.ai.job"].create(
            {
                "filename": self.filename,
                "state": "processing",
                "company_id": self.company_id.id,
                "user_id": self.env.user.id,
            }
        )

        try:
            # 1. Obtener credenciales
            credentials = self._get_openai_credentials()

            # 2. Preparar imágenes
            images_b64 = self._prepare_images_for_openai()

            # 3. Llamar a OpenAI
            openai_result = self._call_openai_vision(images_b64, credentials)

            # 4. Validar schema
            self._validate_json_schema(openai_result["json_data"])

            # 5. Crear factura
            invoice = self._create_invoice_from_data(openai_result["json_data"])

            # 6. Adjuntar archivo original si está configurado
            if self.attach_original and self.upload:
                self.env["ir.attachment"].create(
                    {
                        "name": self.filename or "invoice.pdf",
                        "datas": self.upload,
                        "res_model": "account.move",
                        "res_id": invoice.id,
                        "type": "binary",
                    }
                )

            # 7. Actualizar job
            meta = openai_result["json_data"].get("meta", {})
            job.write(
                {
                    "state": "done",
                    "invoice_id": invoice.id,
                    "tokens_used": openai_result["tokens_used"],
                    "processing_time": openai_result["processing_time"],
                    "pages_processed": meta.get("pages_processed", len(images_b64)),
                    "detected_language": meta.get("language"),
                    "detected_country": meta.get("detected_country"),
                    "supplier_name": openai_result["json_data"]["supplier"]["name"],
                    "invoice_number": openai_result["json_data"]["invoice"]["supplier_invoice_number"],
                    "invoice_amount": openai_result["json_data"]["totals"]["total"],
                }
            )

            # 8. Retornar acción para ver factura
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": invoice.id,
                "target": "current",
                "context": {
                    "default_move_type": "in_invoice",
                },
            }

        except Exception as e:
            # Actualizar job con error
            job.write(
                {
                    "state": "error",
                    "error_message": str(e),
                }
            )
            raise

    @api.model
    def create_and_process_attachments(self, attachment_ids):
        """
        Método llamado desde el botón OCR para procesar adjuntos
        Crea un wizard por cada adjunto y procesa las facturas
        """
        if not attachment_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No files"),
                    "message": _("No files were uploaded."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        Attachment = self.env["ir.attachment"]
        invoices_created = []
        errors = []

        for att_id in attachment_ids:
            attachment = Attachment.browse(att_id)

            try:
                # Crear wizard con el adjunto
                wizard = self.create({
                    "upload": attachment.datas,
                    "filename": attachment.name,
                    "company_id": self.env.company.id,
                    "create_partner_if_missing": True,
                    "attach_original": True,
                })

                # Procesar y crear factura
                result = wizard.action_analyze_and_create()

                if result.get("res_id"):
                    invoices_created.append(result["res_id"])

            except Exception as e:
                _logger.error(f"Error processing attachment {attachment.name}: {e}")
                errors.append(f"{attachment.name}: {str(e)}")
            finally:
                # Eliminar el adjunto temporal
                attachment.unlink()

        # Preparar respuesta
        if invoices_created and not errors:
            # Todo exitoso - abrir vista de facturas creadas
            return {
                "type": "ir.actions.act_window",
                "name": _("Invoices Created"),
                "res_model": "account.move",
                "view_mode": "tree,form",
                "domain": [("id", "in", invoices_created)],
                "context": {
                    "default_move_type": "in_invoice",
                },
            }
        elif invoices_created and errors:
            # Parcialmente exitoso
            return {
                "type": "ir.actions.act_window",
                "name": _("Invoices Created (with errors)"),
                "res_model": "account.move",
                "view_mode": "tree,form",
                "domain": [("id", "in", invoices_created)],
                "context": {
                    "default_move_type": "in_invoice",
                    "notifications": {
                        "Errors": "\n".join(errors),
                    },
                },
            }
        else:
            # Solo errores
            raise UserError(
                _("Failed to process invoices:\n\n%s") % "\n".join(errors)
            )
