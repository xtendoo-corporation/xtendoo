import re
from datetime import datetime, time, timedelta

import pytz

from odoo import Command, fields, models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext

from odoo.addons.xtd_ai_gateway.tools import xtd_ai_tool
from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiDraftOnlyError, XtdAiToolError

PURCHASE_GROUPS = ["purchase.group_purchase_user"]
STOCK_GROUPS = ["stock.group_stock_user"]

_PO_STATES = ["draft", "sent", "to approve", "purchase", "cancel"]
_RFQ_STATES = ("draft", "sent", "to approve")
_PICKING_TYPES = {"receipt": "incoming", "delivery": "outgoing", "internal": "internal"}
_PICKING_TYPE_LABEL = {v: k for k, v in _PICKING_TYPES.items()}
_PICKING_STATES = ["draft", "waiting", "confirmed", "assigned", "done", "cancel"]
_MAX_PRODUCTS = 20


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


class XtdAiToolboxPurchaseStock(models.AbstractModel):
    _name = "xtd.ai.toolbox.purchase_stock"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: purchase and stock"

    _xtd_ai_skills = {
        "compras": "data/skills/compras.md",
        "inventario": "data/skills/inventario.md",
    }

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

    def _ps_require_stock(self):
        self._ps_require_group(
            "stock.group_stock_user", self.env._("usar las herramientas de inventario")
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
            "Odoo usa la tarifa del proveedor). Opcionalmente fecha prevista de "
            "llegada y "
            "referencia del proveedor. Antes localiza proveedor y productos con "
            "search_partners "
            "y search_products y pregunta al usuario lo que falte (proveedor, "
            "cantidades). Con "
            "varias compañías activas se crea en `company` (o en la primera activa si "
            "se omite). No "
            "confirma ni envía nada: convertir la RFQ en pedido lo hace una persona "
            "en Odoo."
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

    # ==================================================================
    # STOCK: read
    # ==================================================================
    @xtd_ai_tool(
        name="get_stock_levels",
        title="Niveles de stock",
        description=(
            "Stock de uno o varios productos: `on_hand` (físico en almacén), "
            "`reserved` (ya "
            "comprometido con albaranes de salida), `available` (on_hand - reserved: "
            "lo que se "
            "puede prometer ahora) y `forecasted` (previsto: físico más entradas "
            "pendientes menos "
            "salidas pendientes). Indica `products` (nombres, referencias o ids; "
            "máximo 20). Con "
            "`warehouse` (nombre o id) devuelve solo ese almacén; sin él, devuelve "
            "cada almacén "
            "y el total; con varias compañías activas y sin `company`, el total sale "
            "por compañía (nunca se "
            "suman compañías distintas) y cada almacén indica su compañía. Si un "
            "nombre es ambiguo "
            "devuelve los candidatos. No modifica datos."
        ),
        input_schema=_obj(
            {
                "products": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": _MAX_PRODUCTS,
                    "items": {"type": "string", "minLength": 1, "maxLength": 100},
                    "description": "Nombres, referencias internas o ids de producto.",
                },
                "warehouse": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Nombre, código o id del almacén.",
                },
                "company": _COMPANY,
            },
            required=["products"],
        ),
        kind="read",
        skill="inventario",
        groups=STOCK_GROUPS,
    )
    def tool_get_stock_levels(self, args):
        self._ps_require_stock()
        products = self.env["product.product"]
        for item in args["products"]:
            products |= self._xtd_ai_resolve("product.product", item)
        company = self._xtd_ai_company(args)
        split = self._xtd_ai_split_companies(args)
        company_domain = self._xtd_ai_company_domain(args)
        warehouse_model = self.env["stock.warehouse"]
        if args.get("warehouse"):
            by_code = warehouse_model.search(
                [("code", "=ilike", args["warehouse"].strip())] + company_domain
            )
            if len(by_code) > 1:
                raise XtdAiToolError(
                    "ambiguous",
                    self.env._(
                        "Hay varios almacenes con ese código en distintas compañías: "
                        "indica `company`."
                    ),
                    data={
                        "candidates": [
                            {"id": w.id, "name": w.name, "company": w.company_id.name}
                            for w in by_code
                        ]
                    },
                )
            warehouses = (
                by_code
                if len(by_code) == 1
                else self._xtd_ai_resolve(
                    "stock.warehouse", args["warehouse"], domain=company_domain
                )
            )
        else:
            warehouses = warehouse_model.search(company_domain)
        quant = self.env["stock.quant"]
        per_wh = {}
        for warehouse in warehouses:
            per_wh[warehouse.id] = self._ps_quant_totals(
                quant, products, [("location_id.warehouse_id", "=", warehouse.id)]
            )
        total_quants = None
        per_company = {}
        if not args.get("warehouse"):
            if split:
                for scoped_company in split:
                    per_company[scoped_company] = self._ps_quant_totals(
                        quant, products, [("company_id", "=", scoped_company.id)]
                    )
            else:
                total_quants = self._ps_quant_totals(quant, products, company_domain)
        items = []
        for product in products:
            row = {
                "id": product.id,
                "name": self._xtd_ai_text(product.display_name),
                "code": product.default_code or None,
                "uom": product.uom_id.name,
                "is_storable": bool(product.is_storable),
                "warehouses": [],
            }
            for warehouse in warehouses:
                row["warehouses"].append(
                    self._ps_level_row(
                        product, per_wh[warehouse.id], warehouse=warehouse
                    )
                )
            if total_quants is not None:
                row["total"] = self._ps_level_row(
                    product.with_context(allowed_company_ids=company.ids)
                    if company
                    else product,
                    total_quants,
                )
            elif per_company:
                row["totals_by_company"] = [
                    dict(
                        {"company": scoped_company.name},
                        **self._ps_level_row(
                            product.with_context(
                                allowed_company_ids=[scoped_company.id]
                            ),
                            totals,
                        ),
                    )
                    for scoped_company, totals in per_company.items()
                ]
            items.append(row)
        return {
            "data": self._xtd_ai_list(items, limit=_MAX_PRODUCTS),
            "records": products,
        }

    def _ps_quant_totals(self, quant_model, products, extra_domain):
        domain = [
            ("product_id", "in", products.ids),
            ("location_id.usage", "=", "internal"),
        ] + extra_domain
        groups = quant_model._read_group(
            domain, ["product_id"], ["quantity:sum", "reserved_quantity:sum"]
        )
        return {product.id: (qty, reserved) for product, qty, reserved in groups}

    def _ps_level_row(self, product, totals, warehouse=None):
        on_hand, reserved = totals.get(product.id, (0.0, 0.0))
        context = {}
        if warehouse:
            context["warehouse_id"] = warehouse.id
        forecast_product = product.with_context(**context)
        row = {
            "on_hand": on_hand,
            "reserved": reserved,
            "available": on_hand - reserved,
            "forecasted": forecast_product.virtual_available,
            "incoming": forecast_product.incoming_qty,
            "outgoing": forecast_product.outgoing_qty,
        }
        if warehouse:
            ref = {"id": warehouse.id, "name": warehouse.name, "code": warehouse.code}
            self._xtd_ai_label(ref, warehouse)
            row = dict({"warehouse": ref}, **row)
        return row

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="search_pickings",
        title="Buscar albaranes",
        description=(
            "Lista albaranes (movimientos de inventario) filtrando por tipo "
            "(`receipt` = "
            "recepción de proveedor, `delivery` = entrega a cliente, `internal` = "
            "traslado "
            "interno), estado (borrador, esperando otra operación, esperando, listo, "
            "hecho, "
            "cancelado), contacto, rango de fecha prevista y origen (p. ej. número "
            "del pedido "
            "de compra o venta). Devuelve id, número, tipo, estado, contacto, fecha "
            "prevista y "
            "origen. Para ver los productos de uno usa get_picking. Cubre todas las "
            "compañías activas del usuario; con `company` filtra por una; cada "
            "elemento indica su compañía si hay varias. No valida ni modifica nada."
        ),
        input_schema=_obj(
            {
                "type": {"type": "string", "enum": list(_PICKING_TYPES)},
                "state": {
                    "type": "string",
                    "enum": _PICKING_STATES,
                    "description": (
                        "assigned=Listo, confirmed=Esperando, waiting=Esperando otra "
                        "operación, done=Hecho."
                    ),
                },
                "partner": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Nombre o id del contacto.",
                },
                "date_from": _DATE_FROM,
                "date_to": _DATE_TO,
                "origin": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Documento de origen.",
                },
                "company": _COMPANY,
                "limit": _LIMIT,
            }
        ),
        kind="read",
        skill="inventario",
        groups=STOCK_GROUPS,
    )
    def tool_search_pickings(self, args):
        self._ps_require_stock()
        domain = self._xtd_ai_company_domain(args)
        if args.get("type"):
            domain.append(("picking_type_code", "=", _PICKING_TYPES[args["type"]]))
        if args.get("state"):
            domain.append(("state", "=", args["state"]))
        if args.get("partner"):
            partner = self._xtd_ai_resolve("res.partner", args["partner"])
            domain.append(("partner_id", "child_of", partner.id))
        domain += self._ps_date_domain("scheduled_date", args)
        if args.get("origin"):
            domain.append(("origin", "ilike", args["origin"].strip()))
        picking_model = self.env["stock.picking"]
        limit = self._xtd_ai_limit(args.get("limit"))
        pickings = picking_model.search(
            domain, limit=limit, order="scheduled_date desc, id desc"
        )
        total = (
            picking_model.search_count(domain)
            if len(pickings) >= limit
            else len(pickings)
        )
        rows = [self._ps_picking_row(p) for p in pickings]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": pickings}

    def _ps_picking_row(self, picking):
        return {
            "id": picking.id,
            "name": picking.name,
            "type": _PICKING_TYPE_LABEL.get(
                picking.picking_type_code, picking.picking_type_code
            ),
            "state": picking.state,
            "partner": self._ps_partner_ref(picking.partner_id),
            "scheduled_date": self._ps_iso(picking.scheduled_date),
            "date_done": self._ps_iso(picking.date_done),
            "origin": self._xtd_ai_text(picking.origin),
            **self._xtd_ai_label({}, picking),
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="get_picking",
        title="Detalle de un albarán",
        description=(
            "Devuelve la cabecera de un albarán (tipo, estado, contacto, fechas, "
            "origen, "
            "ubicaciones) y sus movimientos: producto, demanda (cantidad pedida), "
            "cantidad "
            "reservada o hecha, unidad y estado. Indica `picking_id` (id de "
            "search_pickings) o "
            "`name` (número, p. ej. WH/IN/00001); `company` desambigua números "
            "repetidos entre compañías activas. No valida ni modifica nada."
        ),
        input_schema=_obj(
            {
                "picking_id": {"type": "integer", "minimum": 1},
                "name": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Número del albarán.",
                },
                "company": _COMPANY,
            }
        ),
        kind="read",
        skill="inventario",
        groups=STOCK_GROUPS,
    )
    def tool_get_picking(self, args):
        self._ps_require_stock()
        ref = args.get("picking_id") or args.get("name")
        if not ref:
            raise XtdAiToolError("validation", self.env._("Indica picking_id o name."))
        picking = self._xtd_ai_resolve(
            "stock.picking", ref, domain=self._xtd_ai_company_domain(args)
        )
        data = self._ps_picking_row(picking)
        data.update(
            {
                "operation_type": self._xtd_ai_text(picking.picking_type_id.name),
                "location_from": self._xtd_ai_text(picking.location_id.complete_name),
                "location_to": self._xtd_ai_text(
                    picking.location_dest_id.complete_name
                ),
                "date_deadline": self._ps_iso(picking.date_deadline),
            }
        )
        moves = [
            {
                "id": move.id,
                "product": {
                    "id": move.product_id.id,
                    "name": self._xtd_ai_text(move.product_id.display_name),
                },
                "demand": move.product_uom_qty,
                "quantity": move.quantity,
                "uom": move.product_uom.name,
                "state": move.state,
            }
            for move in picking.move_ids
        ]
        data["moves"] = self._xtd_ai_list(moves, limit=200)
        return {"data": data, "records": picking}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="stock_move_history",
        title="Historial de movimientos de stock",
        description=(
            "Movimientos de stock YA REALIZADOS (hechos) de un producto en un "
            "periodo: fecha, "
            "referencia, cantidad, ubicación origen y destino y sentido (`in` "
            "entrada, `out` "
            "salida, `internal` interno). `direction` filtra entradas o salidas. Del "
            "más "
            "reciente al más antiguo, con tope de filas. Úsala para «qué ha entrado o "
            "salido de "
            "X». Para el stock actual usa get_stock_levels; para albaranes pendientes, "
            "search_pickings. Cubre todas las compañías activas del usuario; con "
            "`company` filtra por una; cada elemento indica su compañía si hay "
            "varias. No modifica datos."
        ),
        input_schema=_obj(
            {
                "product": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Nombre, referencia o id del producto.",
                },
                "date_from": _DATE_FROM,
                "date_to": _DATE_TO,
                "direction": {"type": "string", "enum": ["in", "out", "any"]},
                "company": _COMPANY,
                "limit": _LIMIT,
            },
            required=["product"],
        ),
        kind="read",
        skill="inventario",
        groups=STOCK_GROUPS,
    )
    def tool_stock_move_history(self, args):
        self._ps_require_stock()
        product = self._xtd_ai_resolve("product.product", args["product"])
        domain = [("product_id", "=", product.id), ("state", "=", "done")]
        domain += self._xtd_ai_company_domain(args)
        domain += self._ps_date_domain("date", args)
        direction = args.get("direction", "any")
        if direction == "in":
            domain += [
                ("location_id.usage", "!=", "internal"),
                ("location_dest_id.usage", "=", "internal"),
            ]
        elif direction == "out":
            domain += [
                ("location_id.usage", "=", "internal"),
                ("location_dest_id.usage", "!=", "internal"),
            ]
        line_model = self.env["stock.move.line"]
        limit = self._xtd_ai_limit(args.get("limit"))
        lines = line_model.search(domain, limit=limit, order="date desc, id desc")
        total = line_model.search_count(domain) if len(lines) >= limit else len(lines)
        rows = []
        for line in lines:
            src_internal = line.location_id.usage == "internal"
            dst_internal = line.location_dest_id.usage == "internal"
            sense = (
                "internal"
                if src_internal and dst_internal
                else ("in" if dst_internal else "out" if src_internal else "other")
            )
            rows.append(
                {
                    "id": line.id,
                    "date": self._ps_iso(line.date),
                    "reference": self._xtd_ai_text(line.reference),
                    "direction": sense,
                    "quantity": line.quantity,
                    "uom": line.product_uom_id.name,
                    "location_from": self._xtd_ai_text(line.location_id.complete_name),
                    "location_to": self._xtd_ai_text(
                        line.location_dest_id.complete_name
                    ),
                    "picking": (
                        {"id": line.picking_id.id, "name": line.picking_id.name}
                        if line.picking_id
                        else None
                    ),
                    **self._xtd_ai_label({}, line),
                }
            )
        data = self._xtd_ai_list(rows, total, limit)
        data["product"] = {
            "id": product.id,
            "name": self._xtd_ai_text(product.display_name),
        }
        return {"data": data, "records": product}
