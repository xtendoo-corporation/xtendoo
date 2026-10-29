import re
from datetime import datetime, time, timedelta

import pytz

from odoo import Command, fields, models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext

from odoo.addons.xtd_ai.tools import xtd_ai_tool
from odoo.addons.xtd_ai.tools.errors import XtdAiDraftOnlyError, XtdAiToolError

PURCHASE_GROUPS = ["purchase.group_purchase_user"]

_PO_STATES = ["draft", "sent", "to approve", "purchase", "cancel"]
_RFQ_STATES = ("draft", "sent", "to approve")


def _obj(properties, required=()):
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


_COMPANY = {
    "type": "string",
    "maxLength": 100,
    "description": (
        "Compañía (id o nombre) entre las activas del usuario. Omítela para ver todas."
    ),
}
_LIMIT = {
    "type": "integer",
    "minimum": 1,
    "maximum": 200,
    "description": "Máximo de filas (50 por defecto, 200 como tope).",
}
_DATE_FROM = {
    "type": "string",
    "format": "date",
    "description": "Desde (inclusive), AAAA-MM-DD.",
}
_DATE_TO = {
    "type": "string",
    "format": "date",
    "description": "Hasta (inclusive), AAAA-MM-DD.",
}


class XtdAiToolboxPurchase(models.AbstractModel):
    _name = "xtd.ai.toolbox.purchase"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: purchase"

    _xtd_ai_skills = {"compras": "data/skills/compras.md"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ps_require_group(self, group, label):
        """Defence in depth: ACLs alone are not enough (stock.quant is readable by every
        internal user), so the tool group is checked again at execution time."""
        if not self.env.user.has_group(group):
            raise AccessError(self.env._("No tienes permiso para %s.", label))

    def _ps_require_purchase(self):
        self._ps_require_group(
            "purchase.group_purchase_user",
            self.env._("usar las herramientas de compras"),
        )

    def _ps_datetime(self, value, end=False):
        """Local date (user timezone) to a naive UTC datetime for domains."""
        day = fields.Date.from_string(value)
        if end:
            local = datetime.combine(day + timedelta(days=1), time.min)
        else:
            local = datetime.combine(day, time.min)
        return (
            pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
            .localize(local)
            .astimezone(pytz.utc)
            .replace(tzinfo=None)
        )

    def _ps_date_domain(self, field, args):
        domain = []
        if args.get("date_from"):
            domain.append((field, ">=", self._ps_datetime(args["date_from"])))
        if args.get("date_to"):
            domain.append((field, "<", self._ps_datetime(args["date_to"], end=True)))
        return domain

    def _ps_iso(self, value):
        return value.isoformat() if value else None

    def _ps_html_text(self, html):
        return self._xtd_ai_text(html2plaintext(html or "").strip() or None)

    def _ps_partner_ref(self, partner):
        return (
            {"id": partner.id, "name": self._xtd_ai_text(partner.display_name)}
            if partner
            else None
        )

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

    # ==================================================================
    # PURCHASE: read
    # ==================================================================
    @xtd_ai_tool(
        name="search_purchase_orders",
        title="Buscar pedidos de compra",
        description=(
            "Lista pedidos de compra y solicitudes de presupuesto (RFQ) filtrando por "
            "proveedor, "
            "estado, tipo, rango de fechas del pedido, comprador e importe total. "
            "Parámetro "
            "`kind`: `rfq` = solicitudes aún sin confirmar (borrador, enviada, por "
            "aprobar), "
            "`order` = pedidos confirmados, `any` = todos (por defecto). Devuelve id, "
            "número, "
            "estado, proveedor, fecha, comprador, importes y estado de facturación, "
            "ordenados "
            "del más reciente al más antiguo. Para ver las líneas de uno usa "
            "get_purchase_order; "
            "para totales agregados usa purchase_report. Cubre todas las compañías "
            "activas del usuario; con `company` filtra por una; cada elemento indica "
            "su compañía si hay varias. No modifica datos."
        ),
        input_schema=_obj(
            {
                "vendor": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Parte del nombre del proveedor.",
                },
                "state": {
                    "type": "string",
                    "enum": _PO_STATES,
                    "description": (
                        "draft=RFQ, sent=RFQ enviada, to approve=por aprobar, "
                        "purchase=pedido confirmado, cancel=cancelado."
                    ),
                },
                "kind": {"type": "string", "enum": ["rfq", "order", "any"]},
                "date_from": _DATE_FROM,
                "date_to": _DATE_TO,
                "buyer": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Nombre del comprador.",
                },
                "amount_min": {
                    "type": "number",
                    "description": "Importe total mínimo (con impuestos).",
                },
                "amount_max": {
                    "type": "number",
                    "description": "Importe total máximo (con impuestos).",
                },
                "company": _COMPANY,
                "limit": _LIMIT,
            }
        ),
        kind="read",
        skill="compras",
        groups=PURCHASE_GROUPS,
    )
    def tool_search_purchase_orders(self, args):
        self._ps_require_purchase()
        domain = self._xtd_ai_company_domain(args)
        if args.get("vendor"):
            domain.append(("partner_id", "ilike", args["vendor"].strip()))
        if args.get("state"):
            domain.append(("state", "=", args["state"]))
        kind = args.get("kind", "any")
        if kind == "rfq":
            domain.append(("state", "in", list(_RFQ_STATES)))
        elif kind == "order":
            domain.append(("state", "=", "purchase"))
        domain += self._ps_date_domain("date_order", args)
        if args.get("buyer"):
            domain.append(("user_id", "ilike", args["buyer"].strip()))
        if args.get("amount_min") is not None:
            domain.append(("amount_total", ">=", args["amount_min"]))
        if args.get("amount_max") is not None:
            domain.append(("amount_total", "<=", args["amount_max"]))
        orders_model = self.env["purchase.order"]
        limit = self._xtd_ai_limit(args.get("limit"))
        orders = orders_model.search(
            domain, limit=limit, order="date_order desc, id desc"
        )
        total = (
            orders_model.search_count(domain) if len(orders) >= limit else len(orders)
        )
        rows = [self._ps_order_row(o) for o in orders]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": orders}

    def _ps_order_row(self, order):
        return {
            "id": order.id,
            "name": order.name,
            "state": order.state,
            "is_rfq": order.state in _RFQ_STATES,
            "vendor": self._ps_partner_ref(order.partner_id),
            "date_order": self._ps_iso(order.date_order),
            "buyer": order.user_id.name or None,
            "amount_untaxed": self._xtd_ai_money(
                order.amount_untaxed, order.currency_id
            ),
            "amount_total": self._xtd_ai_money(order.amount_total, order.currency_id),
            "invoice_status": order.invoice_status,
            **self._xtd_ai_label({}, order),
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="get_purchase_order",
        title="Detalle de un pedido de compra",
        description=(
            "Devuelve la cabecera y las líneas de un pedido de compra o solicitud de "
            "presupuesto: "
            "proveedor, estado, fechas, notas y, por línea, producto, cantidad "
            "pedida, cantidad "
            "recibida, cantidad facturada, precio y subtotal. Indica `order_id` (id de "
            "search_purchase_orders) o `name` (número, p. ej. P00012); `company` "
            "desambigua números repetidos entre compañías activas. No modifica datos."
        ),
        input_schema=_obj(
            {
                "order_id": {"type": "integer", "minimum": 1},
                "name": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Número del pedido.",
                },
                "company": _COMPANY,
            }
        ),
        kind="read",
        skill="compras",
        groups=PURCHASE_GROUPS,
    )
    def tool_get_purchase_order(self, args):
        self._ps_require_purchase()
        ref = args.get("order_id") or args.get("name")
        if not ref:
            raise XtdAiToolError("validation", self.env._("Indica order_id o name."))
        order = self._xtd_ai_resolve(
            "purchase.order", ref, domain=self._xtd_ai_company_domain(args)
        )
        data = self._ps_order_row(order)
        data.update(
            {
                "vendor_reference": self._xtd_ai_text(order.partner_ref),
                "origin": self._xtd_ai_text(order.origin),
                "date_approve": self._ps_iso(order.date_approve),
                "date_planned": self._ps_iso(order.date_planned),
                "notes": self._ps_html_text(order.note),
            }
        )
        lines = []
        for line in order.order_line:
            if line.display_type:
                lines.append({"section_or_note": self._xtd_ai_text(line.name)})
                continue
            currency = line.currency_id
            lines.append(
                {
                    "id": line.id,
                    "product": (
                        {
                            "id": line.product_id.id,
                            "name": self._xtd_ai_text(line.product_id.display_name),
                        }
                        if line.product_id
                        else None
                    ),
                    "description": self._xtd_ai_text(line.name),
                    "qty_ordered": line.product_qty,
                    "qty_received": line.qty_received,
                    "qty_invoiced": line.qty_invoiced,
                    "uom": line.product_uom_id.name,
                    "price_unit": self._xtd_ai_money(line.price_unit, currency),
                    "subtotal": self._xtd_ai_money(line.price_subtotal, currency),
                    "date_planned": self._ps_iso(line.date_planned),
                }
            )
        data["lines"] = self._xtd_ai_list(lines, limit=200)
        return {"data": data, "records": order}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="purchase_report",
        title="Informe de compras agregado",
        description=(
            "Totales de compras agrupados por proveedor (`vendor`), producto "
            "(`product`), mes "
            "(`month`) o comprador (`buyer`): importe sin impuestos, cantidad pedida, "
            "recibida y "
            "facturada y número de líneas. Por defecto solo cuenta pedidos "
            "confirmados; con "
            "`include_rfq` suma también las solicitudes no canceladas. Filtra por "
            "fechas del "
            "pedido. Úsala para preguntas como «cuánto hemos comprado a X este año». "
            "Para "
            "listar documentos concretos usa search_purchase_orders. Los importes "
            "salen por moneda "
            "y, con varias compañías activas y sin `company`, también por compañía "
            "(nunca se "
            "suman compañías distintas); con `company` filtra por una. No modifica "
            "datos."
        ),
        input_schema=_obj(
            {
                "group_by": {
                    "type": "string",
                    "enum": ["vendor", "product", "month", "buyer"],
                },
                "date_from": _DATE_FROM,
                "date_to": _DATE_TO,
                "include_rfq": {"type": "boolean"},
                "company": _COMPANY,
                "limit": _LIMIT,
            },
            required=["group_by"],
        ),
        kind="read",
        skill="compras",
        groups=PURCHASE_GROUPS,
    )
    def tool_purchase_report(self, args):
        self._ps_require_purchase()
        group_by = args["group_by"]
        groupby = {
            "vendor": "partner_id",
            "product": "product_id",
            "month": "date_order:month",
            "buyer": "user_id",
        }[group_by]
        states = (
            ["draft", "sent", "to approve", "purchase"]
            if args.get("include_rfq")
            else ["purchase"]
        )
        domain = (
            [("state", "in", states)]
            + self._ps_date_domain("date_order", args)
            + self._xtd_ai_company_domain(args)
        )
        split = self._xtd_ai_split_companies(args)
        report = self.env["purchase.report"]
        order = (
            "date_order:month asc" if group_by == "month" else "untaxed_total:sum desc"
        )
        groups = report._read_group(
            domain,
            [groupby, "currency_id"] + (["company_id"] if split else []),
            [
                "untaxed_total:sum",
                "qty_ordered:sum",
                "qty_received:sum",
                "qty_billed:sum",
                "nbr_lines:sum",
            ],
            order=order,
        )
        rows = []
        for (
            key,
            currency,
            *company,
            untaxed,
            ordered,
            received,
            billed,
            lines,
        ) in groups:
            if group_by == "month":
                label = key.strftime("%Y-%m") if key else None
                item = {"month": label}
            else:
                item = {
                    group_by: (
                        {"id": key.id, "name": self._xtd_ai_text(key.display_name)}
                        if key
                        else None
                    )
                }
            item.update(
                {
                    "untaxed_total": self._xtd_ai_money(untaxed, currency),
                    "qty_ordered": ordered,
                    "qty_received": received,
                    "qty_billed": billed,
                    "lines": lines,
                }
            )
            if company:
                item["company"] = company[0].name
            rows.append(item)
        limit = self._xtd_ai_limit(args.get("limit"))
        return {"data": self._xtd_ai_list(rows, limit=limit), "records": []}

    # ==================================================================
    # PURCHASE: draft
    # ==================================================================
    @xtd_ai_tool(
        name="create_purchase_rfq",
        title="Crear solicitud de presupuesto (RFQ)",
        description=(
            "Crea una solicitud de presupuesto de compra (RFQ) en BORRADOR para un "
            "proveedor, con "
            "una o varias líneas (producto y cantidad; precio unitario opcional: si "
            "se omite, "
            "XTD usa la tarifa del proveedor). Opcionalmente fecha prevista de "
            "llegada y "
            "referencia del proveedor. Antes localiza proveedor y productos con "
            "search_partners "
            "y search_products y pregunta al usuario lo que falte (proveedor, "
            "cantidades). Con "
            "varias compañías activas se crea en `company` (o en la primera activa si "
            "se omite). No "
            "confirma ni envía nada: convertir la RFQ en pedido lo hace una persona "
            "en XTD."
        ),
        input_schema=_obj(
            {
                "vendor": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Nombre o id del proveedor.",
                },
                "lines": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": _obj(
                        {
                            "product": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 100,
                                "description": "Nombre, referencia o id del producto.",
                            },
                            "quantity": {"type": "number", "minimum": 0.0001},
                            "price_unit": {"type": "number", "minimum": 0},
                        },
                        required=["product", "quantity"],
                    ),
                },
                "date_planned": {
                    "type": "string",
                    "format": "date",
                    "description": "Fecha prevista de llegada, AAAA-MM-DD.",
                },
                "vendor_reference": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Referencia del proveedor.",
                },
                "company": _COMPANY,
            },
            required=["vendor", "lines"],
        ),
        kind="draft",
        skill="compras",
        groups=PURCHASE_GROUPS,
        preview="_preview_create_purchase_rfq",
    )
    def tool_create_purchase_rfq(self, args):
        self._ps_require_purchase()
        scoped = self._xtd_ai_scoped(args)
        vals = scoped._ps_rfq_vals(args)
        order = scoped.env["purchase.order"].create(vals)
        if order.state != "draft":
            raise XtdAiDraftOnlyError(
                self.env._(
                    "La solicitud no quedó en borrador: se cancela la operación."
                )
            )
        data = {
            "id": order.id,
            "name": order.name,
            "state": order.state,
            "vendor": self._ps_partner_ref(order.partner_id),
            "lines": len(order.order_line),
            "amount_untaxed": self._xtd_ai_money(
                order.amount_untaxed, order.currency_id
            ),
        }
        if self._xtd_ai_multi():
            data["company"] = order.company_id.name
        return {"data": data, "records": order}

    def _ps_rfq_vals(self, args):
        vendor = self._xtd_ai_resolve("res.partner", args["vendor"])
        planned = None
        if args.get("date_planned"):
            planned = datetime.combine(
                fields.Date.from_string(args["date_planned"]), time(12, 0)
            )
        lines = []
        for item in args["lines"]:
            product = self._xtd_ai_resolve(
                "product.product", item["product"], domain=[("purchase_ok", "=", True)]
            )
            line = {"product_id": product.id, "product_qty": item["quantity"]}
            if item.get("price_unit") is not None:
                line["price_unit"] = item["price_unit"]
            if planned:
                line["date_planned"] = planned
            lines.append(Command.create(line))
        vals = {"partner_id": vendor.id, "order_line": lines}
        if args.get("vendor_reference"):
            vals["partner_ref"] = args["vendor_reference"].strip()
        return vals

    def _preview_create_purchase_rfq(self, args):
        show_company = self._xtd_ai_multi()
        self = self._xtd_ai_scoped(args)  # noqa: PLW0642
        vals = self._ps_rfq_vals(args)
        # new(): computes amounts without writing or consuming the order sequence
        order = self.env["purchase.order"].new(vals)
        summary = self.env._(
            "Solicitud de presupuesto para %(vendor)s: %(count)s líneas, %(amount)s "
            "sin impuestos",
            vendor=order.partner_id.display_name,
            count=len(order.order_line),
            amount=order.currency_id.format(order.amount_untaxed)
            if order.currency_id
            else order.amount_untaxed,
        )
        lines = [
            {
                "product": self._xtd_ai_text(line.product_id.display_name),
                "quantity": line.product_qty,
                "price_unit": self._xtd_ai_money(line.price_unit, order.currency_id),
            }
            for line in order.order_line
        ]
        if show_company:
            summary = (
                self.env._("[%(company)s] ", company=self.env.company.name) + summary
            )
        return {"summary": summary, "lines": lines}
