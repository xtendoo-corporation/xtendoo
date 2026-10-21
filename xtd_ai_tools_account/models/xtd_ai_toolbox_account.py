import re
from datetime import timedelta

from odoo import Command, fields, models

from odoo.addons.xtd_ai_gateway.tools import xtd_ai_tool
from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiDraftOnlyError, XtdAiToolError

_READ_GROUPS = ["account.group_account_invoice", "account.group_account_readonly"]
_WRITE_GROUPS = ["account.group_account_invoice"]

_MOVE_TYPES = {
    "customer_invoice": "out_invoice",
    "customer_refund": "out_refund",
    "vendor_bill": "in_invoice",
    "vendor_refund": "in_refund",
}
_ALL_TYPES = list(_MOVE_TYPES.values())
_UNPAID_STATES = ("not_paid", "partial", "blocked")
_BUCKETS = ["not_due", "d1_30", "d31_60", "d61_90", "d90_plus"]


def _obj(properties, required=()):
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


_DATE = {"type": "string", "format": "date"}
_COMPANY = {
    "type": "string",
    "maxLength": 100,
    "description": (
        "Compañía (id o nombre) entre las activas del usuario. Omítela para ver todas."
    ),
}

_LINE_SCHEMA = _obj(
    {
        "product_id": {
            "type": "integer",
            "minimum": 1,
            "description": (
                "Id del producto (search_products). Opcional si hay description."
            ),
        },
        "description": {
            "type": "string",
            "maxLength": 300,
            "description": "Descripción de la línea; obligatoria si no hay producto.",
        },
        "quantity": {"type": "number", "minimum": 0.0001, "maximum": 1000000},
        "price_unit": {
            "type": "number",
            "minimum": 0,
            "maximum": 100000000,
            "description": (
                "Precio unitario sin impuestos. Si se omite se usa el del producto."
            ),
        },
    },
    required=["quantity"],
)


def _invoice_schema(partner_label):
    return _obj(
        {
            "partner_id": {
                "type": "integer",
                "minimum": 1,
                "description": f"Id del {partner_label} (search_partners).",
            },
            "lines": {
                "type": "array",
                "minItems": 1,
                "maxItems": 50,
                "items": _LINE_SCHEMA,
            },
            "invoice_date": _DATE
            | {
                "description": (
                    "Fecha de la factura (YYYY-MM-DD). Obligatoria si la factura de "
                    "proveedor se prepara a partir de un documento adjunto: léela "
                    "del documento."
                )
            },
            "ref": {
                "type": "string",
                "maxLength": 100,
                "description": (
                    "En facturas de proveedor: número de la factura del proveedor, "
                    "obligatorio si se parte de un documento adjunto (léelo del "
                    "documento). En facturas de cliente: referencia del cliente, "
                    "opcional."
                ),
            },
            "company": _COMPANY,
            "attachment_id": {
                "type": "integer",
                "minimum": 1,
                "description": (
                    "Id del adjunto del chat (el documento original) que quedará "
                    "adjunto al borrador. Opcional."
                ),
            },
        },
        required=["partner_id", "lines"],
    )


class XtdAiToolboxAccount(models.AbstractModel):
    _name = "xtd.ai.toolbox.account"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: accounting"

    _xtd_ai_skills = {"contabilidad": "data/skills/contabilidad.md"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _xtd_ai_today(self):
        return fields.Date.context_today(self)

    def _xtd_ai_partner_ref(self, partner):
        if not partner:
            return None
        return {"id": partner.id, "name": self._xtd_ai_text(partner.name)}

    def _xtd_ai_invoice_row(self, move, today):
        company_currency = move.currency_id
        overdue = bool(
            move.state == "posted"
            and move.payment_state in _UNPAID_STATES
            and move.invoice_date_due
            and move.invoice_date_due < today
        )
        return {
            "id": move.id,
            "number": move.name if move.name and move.name != "/" else None,
            "move_type": move.move_type,
            "state": move.state,
            "payment_state": move.payment_state,
            "partner": self._xtd_ai_partner_ref(move.partner_id),
            "invoice_date": str(move.invoice_date) if move.invoice_date else None,
            "due_date": str(move.invoice_date_due) if move.invoice_date_due else None,
            "ref": self._xtd_ai_text(move.ref),
            "amount_untaxed": self._xtd_ai_money(move.amount_untaxed, company_currency),
            "amount_total": self._xtd_ai_money(move.amount_total, company_currency),
            "amount_residual": self._xtd_ai_money(
                move.amount_residual, company_currency
            ),
            "overdue": overdue,
            "days_overdue": (today - move.invoice_date_due).days if overdue else 0,
            **self._xtd_ai_label({}, move),
        }

    # ------------------------------------------------------------------
    # Multi-company (results span env.companies; never wider)
    # ------------------------------------------------------------------
    def _xtd_ai_multi(self):
        return len(self.env.companies) > 1

    def _xtd_ai_company(self, args):
        """Company named in ``args["company"]`` (id or name), resolved ONLY among the
        user's active companies (``env.companies``). Empty recordset if not given."""
        companies = self.env.companies
        value = args.get("company")
        if value is None or value is False or str(value).strip() == "":
            return companies.browse()
        text = str(value).strip()
        if re.fullmatch(r"\d{1,12}", text):
            found = companies.filtered(lambda c: c.id == int(text))
        else:
            low = text.lower()
            found = companies.filtered(lambda c: (c.name or "").lower() == low)
            if not found:
                found = companies.filtered(lambda c: low in (c.name or "").lower())
        if len(found) > 1:
            raise XtdAiToolError(
                "ambiguous",
                self.env._(
                    "Hay varias compañías activas que coinciden con «%s». Indica el "
                    "id.",
                    text,
                ),
                data={"candidates": [{"id": c.id, "name": c.name} for c in found]},
            )
        if not found:
            raise XtdAiToolError(
                "not_found",
                self.env._(
                    "No hay ninguna compañía activa «%(name)s». Compañías activas: "
                    "%(names)s.",
                    name=text,
                    names=", ".join(companies.mapped("name")),
                ),
            )
        return found

    def _xtd_ai_company_domain(self, args, field="company_id"):
        company = self._xtd_ai_company(args)
        return [(field, "in", company.ids)] if company else []

    def _xtd_ai_split_companies(self, args):
        """Companies to split aggregates by: empty unless several are active and no
        ``company`` filter was given."""
        if self._xtd_ai_company(args) or not self._xtd_ai_multi():
            return self.env["res.company"]
        return self.env.companies

    def _xtd_ai_label(self, row, record):
        """Add ``company`` to a row when the user has several active companies."""
        if self._xtd_ai_multi() and "company_id" in record._fields:
            row["company"] = record.company_id.name or None
        return row

    def _xtd_ai_scoped(self, args=None, record=None):
        """Toolbox whose env only sees the target company (for drafts): the requested
        one, the company of ``record`` or the first active one. Only narrows."""
        requested = self._xtd_ai_company(args or {})  # validates even with one company
        if not self._xtd_ai_multi():
            return self
        company = (
            requested
            or (record.company_id if record is not None and record.company_id else None)
            or self.env.company
        )
        return self.with_context(allowed_company_ids=[company.id])

    # ------------------------------------------------------------------
    # Read tools
    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="search_invoices",
        title="Buscar facturas",
        description=(
            "Busca facturas y rectificativas de cliente o de proveedor. Filtra por "
            "tipo "
            "(move_type), estado (borrador, publicada, cancelada), estado de pago, "
            "contacto, "
            "rango de fecha de factura o de vencimiento, solo vencidas e importe "
            "total. Devuelve "
            "por factura: id, número, tipo, estado, pago, contacto, fechas, importes "
            "sin y con "
            "impuestos, pendiente y días de vencimiento. Úsala para listar o "
            "localizar facturas; "
            "para el detalle de una usa get_invoice y para totales por contacto "
            "receivables_payables_summary. Cubre todas las compañías activas del "
            "usuario; con `company` filtra por una; cada factura indica su compañía "
            "si hay varias. Solo lectura."
        ),
        input_schema=_obj(
            {
                "move_type": {
                    "type": "string",
                    "enum": list(_MOVE_TYPES),
                    "description": "customer_invoice, customer_refund, vendor_bill o "
                    "vendor_refund. "
                    "Si se omite, todos.",
                },
                "state": {"type": "string", "enum": ["draft", "posted", "cancel"]},
                "payment_state": {
                    "type": "string",
                    "enum": [
                        "not_paid",
                        "in_payment",
                        "paid",
                        "partial",
                        "reversed",
                        "blocked",
                    ],
                },
                "partner_id": {"type": "integer", "minimum": 1},
                "partner_query": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 100,
                    "description": (
                        "Texto del nombre del contacto, si no se conoce su id."
                    ),
                },
                "invoice_date_from": _DATE,
                "invoice_date_to": _DATE,
                "due_date_from": _DATE,
                "due_date_to": _DATE,
                "overdue_only": {
                    "type": "boolean",
                    "description": (
                        "Solo publicadas, no pagadas y con vencimiento anterior a hoy."
                    ),
                },
                "min_amount": {
                    "type": "number",
                    "description": "Importe total mínimo (con impuestos).",
                },
                "max_amount": {
                    "type": "number",
                    "description": "Importe total máximo (con impuestos).",
                },
                "company": _COMPANY,
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            }
        ),
        kind="read",
        skill="contabilidad",
        groups=_READ_GROUPS,
    )
    def tool_search_invoices(self, args):
        move_model = self.env["account.move"]
        today = self._xtd_ai_today()
        types = (
            [_MOVE_TYPES[args["move_type"]]] if args.get("move_type") else _ALL_TYPES
        )
        domain = [("move_type", "in", types)] + self._xtd_ai_company_domain(args)
        if args.get("state"):
            domain.append(("state", "=", args["state"]))
        if args.get("payment_state"):
            domain.append(("payment_state", "=", args["payment_state"]))
        if args.get("partner_id"):
            partner = self._xtd_ai_resolve("res.partner", args["partner_id"])
            domain.append(("partner_id", "child_of", partner.commercial_partner_id.id))
        if args.get("partner_query"):
            domain.append(("partner_id", "ilike", args["partner_query"].strip()))
        for key, field, operator in (
            ("invoice_date_from", "invoice_date", ">="),
            ("invoice_date_to", "invoice_date", "<="),
            ("due_date_from", "invoice_date_due", ">="),
            ("due_date_to", "invoice_date_due", "<="),
        ):
            if args.get(key):
                domain.append((field, operator, args[key]))
        if args.get("overdue_only"):
            domain += [
                ("state", "=", "posted"),
                ("payment_state", "in", list(_UNPAID_STATES)),
                ("invoice_date_due", "<", today),
            ]
        if "min_amount" in args:
            domain.append(("amount_total", ">=", args["min_amount"]))
        if "max_amount" in args:
            domain.append(("amount_total", "<=", args["max_amount"]))
        limit = self._xtd_ai_limit(args.get("limit"))
        moves = move_model.search(
            domain, limit=limit, order="invoice_date desc, id desc"
        )
        total = move_model.search_count(domain) if len(moves) >= limit else len(moves)
        rows = [self._xtd_ai_invoice_row(m, today) for m in moves]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": moves}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="get_invoice",
        title="Detalle de una factura",
        description=(
            "Devuelve una factura o rectificativa completa: cabecera (contacto, "
            "estado, pago, "
            "fechas, referencia), líneas (producto, descripción, cantidad, precio, "
            "descuento, "
            "impuestos, subtotal y total) y totales (sin impuestos, impuestos, total, "
            "pendiente). "
            "Identifícala con invoice_id (de search_invoices) o con su número, p. ej. "
            "INV/2026/00001; "
            "`company` desambigua números repetidos entre compañías activas. No "
            "modifica datos."
        ),
        input_schema=_obj(
            {
                "invoice_id": {"type": "integer", "minimum": 1},
                "number": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 100,
                    "description": "Número de la factura, si no se conoce el id.",
                },
                "company": _COMPANY,
            }
        ),
        kind="read",
        skill="contabilidad",
        groups=_READ_GROUPS,
    )
    def tool_get_invoice(self, args):
        if not args.get("invoice_id") and not args.get("number"):
            raise XtdAiToolError(
                "validation", self.env._("Indica invoice_id o el número de la factura.")
            )
        move = self._xtd_ai_resolve(
            "account.move",
            args.get("invoice_id") or args["number"],
            domain=[("move_type", "in", _ALL_TYPES)]
            + self._xtd_ai_company_domain(args),
        )
        today = self._xtd_ai_today()
        currency = move.currency_id
        data = self._xtd_ai_invoice_row(move, today)
        data.update(
            {
                "payment_reference": self._xtd_ai_text(move.payment_reference),
                "currency": currency.name,
                "amount_tax": self._xtd_ai_money(move.amount_tax, currency),
            }
        )
        product_lines = move.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
        )
        rows = [
            {
                "product": (
                    {
                        "id": line.product_id.id,
                        "name": self._xtd_ai_text(line.product_id.display_name),
                    }
                    if line.product_id
                    else None
                ),
                "description": self._xtd_ai_text(line.name),
                "quantity": line.quantity,
                "price_unit": self._xtd_ai_money(line.price_unit, currency),
                "discount": line.discount,
                "taxes": [t.name for t in line.tax_ids],
                "subtotal": self._xtd_ai_money(line.price_subtotal, currency),
                "total": self._xtd_ai_money(line.price_total, currency),
            }
            for line in product_lines
        ]
        data["lines"] = self._xtd_ai_list(rows, limit=100)
        return {"data": data, "records": move}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="receivables_payables_summary",
        title="Pendiente de cobro o pago por antigüedad",
        description=(
            "Resume lo pendiente de cobrar a clientes (kind=receivable) o de pagar a "
            "proveedores "
            "(kind=payable) por contacto, repartido por antigüedad del vencimiento: "
            "no vencido, "
            "1-30, 31-60, 61-90 y más de 90 días. Usa solo facturas publicadas y su "
            "pendiente; "
            "las rectificativas restan. Úsala para preguntas como «quién nos debe» o "
            "«qué debemos pagar»; para listar facturas "
            "concretas usa search_invoices. Cubre todas las compañías activas del "
            "usuario: los "
            "totales salen separados por compañía, cada una en su moneda (no se "
            "suman); con "
            "`company` filtra por una. Solo lectura."
        ),
        input_schema=_obj(
            {
                "kind": {"type": "string", "enum": ["receivable", "payable"]},
                "partner_id": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Opcional: limitar a un contacto.",
                },
                "company": _COMPANY,
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "description": (
                        "Máximo de contactos devueltos (los de mayor importe)."
                    ),
                },
            },
            required=["kind"],
        ),
        kind="read",
        skill="contabilidad",
        groups=_READ_GROUPS,
    )
    def tool_receivables_payables_summary(self, args):
        move_model = self.env["account.move"]
        today = self._xtd_ai_today()
        receivable = args["kind"] == "receivable"
        types = (
            ["out_invoice", "out_refund"] if receivable else ["in_invoice", "in_refund"]
        )
        sign = (
            1 if receivable else -1
        )  # amount_residual_signed is negative for vendor bills
        base = [
            ("move_type", "in", types),
            ("state", "=", "posted"),
            ("amount_residual", "!=", 0),
        ] + self._xtd_ai_company_domain(args)
        multi = self._xtd_ai_multi()
        if args.get("partner_id"):
            partner = self._xtd_ai_resolve("res.partner", args["partner_id"])
            base.append(
                ("commercial_partner_id", "=", partner.commercial_partner_id.id)
            )
        bounds = {
            "d1_30": (today - timedelta(days=30), today - timedelta(days=1)),
            "d31_60": (today - timedelta(days=60), today - timedelta(days=31)),
            "d61_90": (today - timedelta(days=90), today - timedelta(days=61)),
        }
        bucket_domains = {
            "not_due": [
                "|",
                ("invoice_date_due", "=", False),
                ("invoice_date_due", ">=", today),
            ],
            "d90_plus": [("invoice_date_due", "<", today - timedelta(days=90))],
        }
        for name, (low, high) in bounds.items():
            bucket_domains[name] = [
                ("invoice_date_due", ">=", low),
                ("invoice_date_due", "<=", high),
            ]
        table = {}  # (company, partner) -> {bucket: amount}
        for bucket in _BUCKETS:
            groups = move_model._read_group(
                base + bucket_domains[bucket],
                ["company_id", "commercial_partner_id"],
                ["amount_residual_signed:sum"],
            )
            for company, partner, amount in groups:
                table.setdefault((company, partner), dict.fromkeys(_BUCKETS, 0.0))[
                    bucket
                ] += sign * amount
        rows, totals = [], {}
        for (company, partner), buckets in sorted(
            table.items(), key=lambda item: (-sum(item[1].values()), item[0][1].id)
        ):
            currency = company.currency_id
            row_total = sum(buckets.values())
            row = {
                "partner": self._xtd_ai_partner_ref(partner),
                "total": self._xtd_ai_money(row_total, currency),
                "buckets": {
                    b: self._xtd_ai_money(v, currency) for b, v in buckets.items()
                },
            }
            if multi:
                row["company"] = company.name
            rows.append(row)
            company_totals = totals.setdefault(company, dict.fromkeys(_BUCKETS, 0.0))
            for bucket, value in buckets.items():
                company_totals[bucket] += value
        limit = self._xtd_ai_limit(args.get("limit"))
        data = {
            "kind": args["kind"],
            "as_of": str(today),
            "totals": [
                {
                    "company": company.name,
                    "total": self._xtd_ai_money(
                        sum(values.values()), company.currency_id
                    ),
                    "buckets": {
                        b: self._xtd_ai_money(v, company.currency_id)
                        for b, v in values.items()
                    },
                }
                for company, values in totals.items()
            ],
            "partners": self._xtd_ai_list(rows, limit=limit),
        }
        return {"data": data, "records": []}

    # ------------------------------------------------------------------
    # Draft tools
    # ------------------------------------------------------------------
    def _xtd_ai_invoice_vals(self, args, move_type):
        """Validated ``account.move`` values from tool arguments (whitelisted fields
        only)."""
        if move_type == "in_invoice" and args.get("attachment_id") is not None:
            # A supplier invoice always shows its number and date (and a bill
            # without them is hard to reconcile or to detect as duplicate): when
            # the bill comes from a document, require both instead of trusting the
            # model to remember them.
            missing = [
                label
                for key, label in (
                    ("ref", self.env._("ref (número de la factura del proveedor)")),
                    ("invoice_date", self.env._("invoice_date (fecha de la factura)")),
                )
                if not str(args.get(key) or "").strip()
            ]
            if missing:
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "Factura de proveedor a partir de un documento: falta %s. "
                        "Léelos del documento y vuelve a llamar a la herramienta; si "
                        "de verdad no aparecen, pregunta al usuario.",
                        " y ".join(missing),
                    ),
                )
        partner = self._xtd_ai_resolve("res.partner", args["partner_id"])
        lines = []
        for index, line in enumerate(args["lines"], 1):
            line_vals = {"quantity": line["quantity"]}
            product = None
            if line.get("product_id"):
                product = self._xtd_ai_resolve("product.product", line["product_id"])
                line_vals["product_id"] = product.id
            if line.get("description"):
                line_vals["name"] = line["description"].strip()
            if not product and not line_vals.get("name"):
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "La línea %s necesita un producto o una descripción.", index
                    ),
                )
            if "price_unit" in line:
                line_vals["price_unit"] = line["price_unit"]
            elif not product:
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "La línea %s no tiene producto: indica price_unit.", index
                    ),
                )
            lines.append(Command.create(line_vals))
        vals = {
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_line_ids": lines,
        }
        if args.get("invoice_date"):
            vals["invoice_date"] = args["invoice_date"]
        if args.get("ref"):
            vals["ref"] = args["ref"].strip()
        return vals

    def _xtd_ai_invoice_attachment(self, args):
        """The chat attachment to keep with the draft (empty recordset if none)."""
        if args.get("attachment_id") is None:
            return self.env["ir.attachment"]
        return self._xtd_ai_conversation_attachment(args["attachment_id"])

    def _xtd_ai_move_model(self, move_type):
        return self.env["account.move"].with_context(default_move_type=move_type)

    def _xtd_ai_create_invoice(self, args, move_type):
        multi = self._xtd_ai_multi()
        self = self._xtd_ai_scoped(args)  # noqa: PLW0642
        vals = self._xtd_ai_invoice_vals(args, move_type)
        attachment = self._xtd_ai_invoice_attachment(args)
        move = self._xtd_ai_move_model(move_type).create(vals)
        if (
            move.state != "draft"
            or move.auto_post != "no"
            or move.move_type != move_type
            or move.payment_state not in ("not_paid", False)
        ):
            raise XtdAiDraftOnlyError(
                self.env._("La factura no ha quedado en borrador.")
            )
        if attachment:
            # Copy (never move) the chat document to the draft, with the user's
            # rights, and make it the main attachment. The chat copy stays.
            copy = self.env["ir.attachment"].create(
                {
                    "name": attachment.name,
                    "raw": attachment.raw,
                    "mimetype": attachment.mimetype,
                    "res_model": "account.move",
                    "res_id": move.id,
                }
            )
            if "message_main_attachment_id" in move._fields:
                move.message_main_attachment_id = copy
        today = self._xtd_ai_today()
        data = self._xtd_ai_invoice_row(move, today)
        if attachment:
            data["attachment"] = self._xtd_ai_text(attachment.name)
        data["journal"] = move.journal_id.name
        if multi:
            data["company"] = move.company_id.name
        data["currency"] = move.currency_id.name
        data["amount_tax"] = self._xtd_ai_money(move.amount_tax, move.currency_id)
        return {"data": data, "records": move}

    def _xtd_ai_preview_invoice(self, args, move_type, label):
        multi = self._xtd_ai_multi()
        self = self._xtd_ai_scoped(args)  # noqa: PLW0642
        vals = self._xtd_ai_invoice_vals(args, move_type)
        attachment = self._xtd_ai_invoice_attachment(args)
        # The gateway runs previews in a savepoint that is always rolled back, so the
        # draft can be really created to let Odoo compute taxes and totals.
        move = self._xtd_ai_move_model(move_type).create(vals)
        currency = move.currency_id or self.env.company.currency_id
        partner = self.env["res.partner"].browse(vals["partner_id"])
        summary = self.env._(
            "%(label)s para %(partner)s: %(count)s líneas, %(amount)s sin impuestos, "
            "%(tax)s de impuestos, total %(total)s calculado por Odoo (borrador)",
            label=label,
            partner=partner.display_name,
            count=len(args["lines"]),
            amount=f"{move.amount_untaxed:,.2f} {currency.name}",
            tax=f"{move.amount_tax:,.2f} {currency.name}",
            total=f"{move.amount_total:,.2f} {currency.name}",
        )
        if multi:
            summary = (
                self.env._("[%(company)s] ", company=move.company_id.name) + summary
            )
        if attachment:
            summary += self.env._(
                " Adjunto: %s.", self._xtd_ai_text(attachment.name)["untrusted_text"]
            )
        lines = [
            {
                "product": self._xtd_ai_text(line.product_id.display_name)
                if line.product_id
                else None,
                "description": self._xtd_ai_text(line.name),
                "quantity": line.quantity,
                "price_unit": self._xtd_ai_money(line.price_unit, currency),
                "taxes": [t.name for t in line.tax_ids],
                "subtotal": self._xtd_ai_money(line.price_subtotal, currency),
            }
            for line in move.invoice_line_ids
        ]
        extra = {}
        if attachment:
            extra["attachment"] = self._xtd_ai_text(attachment.name)
        return {
            **extra,
            "summary": summary,
            "lines": lines,
            "amount_untaxed": self._xtd_ai_money(move.amount_untaxed, currency),
            "amount_tax": self._xtd_ai_money(move.amount_tax, currency),
            "amount_total": self._xtd_ai_money(move.amount_total, currency),
        }

    @xtd_ai_tool(
        name="create_customer_invoice",
        title="Crear factura de cliente (borrador)",
        description=(
            "Crea una factura de cliente SIEMPRE en borrador: no la contabiliza, no "
            "la envía y no "
            "registra pagos; el usuario la revisa y publica en Odoo. Necesita el "
            "contacto "
            "(partner_id de search_partners) y líneas con cantidad y producto "
            "(product_id de "
            "search_products) o descripción más price_unit; el precio, si falta, es "
            "el del "
            "producto. Los impuestos y el diario los calcula Odoo. Opcionales: "
            "invoice_date, ref "
            "y attachment_id (documento adjunto del chat que quedará en el borrador). "
            "Con varias compañías activas se crea en `company` (o en la primera "
            "activa si se omite). "
            "No sirve para facturas de proveedor (create_vendor_bill) ni para "
            "modificar facturas "
            "existentes. Pregunta al usuario los datos que falten antes de llamarla."
        ),
        input_schema=_invoice_schema("cliente"),
        kind="draft",
        skill="contabilidad",
        groups=_WRITE_GROUPS,
        preview="_xtd_ai_preview_create_customer_invoice",
    )
    def tool_create_customer_invoice(self, args):
        return self._xtd_ai_create_invoice(args, "out_invoice")

    def _xtd_ai_preview_create_customer_invoice(self, args):
        return self._xtd_ai_preview_invoice(
            args, "out_invoice", self.env._("Factura de cliente")
        )

    @xtd_ai_tool(
        name="create_vendor_bill",
        title="Crear factura de proveedor (borrador)",
        description=(
            "Registra una factura de proveedor SIEMPRE en borrador: no la contabiliza "
            "ni registra "
            "pagos; el usuario la revisa y publica en Odoo. Necesita el proveedor "
            "(partner_id de "
            "search_partners) y líneas con cantidad y producto o descripción más "
            "price_unit. "
            "Opcionales: ref (número de la factura del proveedor), invoice_date "
            "(fecha de la "
            "factura del proveedor) y attachment_id (id del documento adjunto del "
            "chat, p. ej. "
            "el PDF de la factura, que quedará adjunto al borrador). Los impuestos y "
            "el diario los calcula Odoo. Con varias compañías "
            "activas se crea en `company` (o en la primera activa si se omite). No "
            "sirve para "
            "facturas de cliente (create_customer_invoice) ni para modificar facturas "
            "existentes."
        ),
        input_schema=_invoice_schema("proveedor"),
        kind="draft",
        skill="contabilidad",
        groups=_WRITE_GROUPS,
        preview="_xtd_ai_preview_create_vendor_bill",
    )
    def tool_create_vendor_bill(self, args):
        return self._xtd_ai_create_invoice(args, "in_invoice")

    def _xtd_ai_preview_create_vendor_bill(self, args):
        return self._xtd_ai_preview_invoice(
            args, "in_invoice", self.env._("Factura de proveedor")
        )
