import re
from datetime import date, datetime, time, timedelta

import pytz

from odoo import Command, fields, models
from odoo.tools import html2plaintext
from odoo.tools.misc import formatLang

from odoo.addons.xtd_ai.tools import (
    XtdAiDraftOnlyError,
    XtdAiToolError,
    xtd_ai_tool,
)

SALES_GROUPS = ["sales_team.group_sale_salesman"]
MAX_LINES = 100

_REF = "Id numérico o nombre (si es un nombre ambiguo se devolverán los candidatos)."


def _schema(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": list(required or []),
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
    "description": "Máximo de filas (50 por defecto).",
}
_DATE = {"type": "string", "format": "date"}

_LINE_SCHEMA = _schema(
    {
        "product": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
            "description": (
                "Id numérico del producto (de search_products) o su nombre/referencia."
            ),
        },
        "quantity": {
            "type": "number",
            "minimum": 0,
            "description": "Cantidad, mayor que 0.",
        },
        "price_unit": {
            "type": "number",
            "minimum": 0,
            "description": (
                "Precio unitario sin impuestos. Omítelo para usar la tarifa del "
                "cliente."
            ),
        },
        "discount": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Descuento en %.",
        },
    },
    ["product", "quantity"],
)


class XtdAiToolboxSale(models.AbstractModel):
    _name = "xtd.ai.toolbox.sale"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: sales"

    _xtd_ai_skills = {"ventas": "data/skills/ventas.md"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _xtd_ai_iso(self, value):
        return value.isoformat() if value else None

    def _xtd_ai_day_bounds(self, date_from=None, date_to=None):
        """Domain pieces for a Datetime field from local dates (user timezone)."""
        tz = pytz.timezone(self.env.context.get("tz") or "UTC")

        def to_utc(day, end=False):
            day = date.fromisoformat(day)
            if end:
                day += timedelta(days=1)
            local = tz.localize(datetime.combine(day, time.min))
            return fields.Datetime.to_string(
                local.astimezone(pytz.utc).replace(tzinfo=None)
            )

        bounds = []
        if date_from:
            bounds.append((">=", to_utc(date_from)))
        if date_to:
            bounds.append(("<", to_utc(date_to, end=True)))
        return bounds

    def _xtd_ai_check_dates(self, date_from, date_to):
        if date_from and date_to and date_from > date_to:
            raise XtdAiToolError(
                "validation", self.env._("La fecha inicial es posterior a la final.")
            )

    def _xtd_ai_money_fmt(self, amount, currency):
        return formatLang(self.env, amount, currency_obj=currency)

    def _xtd_ai_plain(self, html):
        if not html:
            return None
        return self._xtd_ai_text(html2plaintext(html).strip())

    def _xtd_ai_user_name(self, user):
        return user.name if user else None

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
    # Sales: read
    # ------------------------------------------------------------------
    def _xtd_ai_order_row(self, order):
        return {
            "id": order.id,
            "name": order.name,
            "kind": "order" if order.state == "sale" else "quotation",
            "state": order.state,
            "partner": {
                "id": order.partner_id.id,
                "name": self._xtd_ai_text(order.partner_id.name),
            },
            "date_order": self._xtd_ai_iso(order.date_order),
            "validity_date": self._xtd_ai_iso(order.validity_date),
            "salesperson": self._xtd_ai_user_name(order.user_id),
            "customer_reference": self._xtd_ai_text(order.client_order_ref),
            "amount_untaxed": self._xtd_ai_money(
                order.amount_untaxed, order.currency_id
            ),
            "amount_total": self._xtd_ai_money(order.amount_total, order.currency_id),
            **self._xtd_ai_label({}, order),
        }

    @xtd_ai_tool(
        name="search_sale_orders",
        title="Buscar presupuestos y pedidos de venta",
        description=(
            "Lista presupuestos y pedidos de venta con filtros: cliente, tipo "
            "(quotation = "
            "presupuestos en borrador o enviados; order = pedidos confirmados; all), "
            "estado exacto, "
            "rango de fechas del pedido, comercial e importe sin impuestos "
            "mínimo/máximo. Devuelve "
            "referencia, cliente, estado, fechas, comercial e importes, más recientes "
            "primero. "
            "Úsala para localizar documentos; para totales agregados usa sales_report. "
            "Solo ve los documentos que el usuario puede ver. Cubre todas las "
            "compañías activas del usuario; con `company` filtra por una; cada "
            "elemento indica su compañía si hay varias. No modifica datos."
        ),
        input_schema=_schema(
            {
                "partner": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Cliente. " + _REF,
                },
                "kind": {
                    "type": "string",
                    "enum": ["quotation", "order", "all"],
                    "description": (
                        "quotation = presupuestos, order = pedidos confirmados. Por "
                        "defecto all."
                    ),
                },
                "state": {
                    "type": "string",
                    "enum": ["draft", "sent", "sale", "cancel"],
                    "description": (
                        "Estado exacto: draft, sent (presupuesto enviado), sale "
                        "(pedido), cancel."
                    ),
                },
                "date_from": _DATE
                | {"description": "Fecha del pedido desde (incluida), AAAA-MM-DD."},
                "date_to": _DATE
                | {"description": "Fecha del pedido hasta (incluida), AAAA-MM-DD."},
                "salesperson": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Comercial. " + _REF,
                },
                "min_amount": {
                    "type": "number",
                    "description": "Importe sin impuestos mínimo.",
                },
                "max_amount": {
                    "type": "number",
                    "description": "Importe sin impuestos máximo.",
                },
                "company": _COMPANY,
                "limit": _LIMIT,
            }
        ),
        kind="read",
        skill="ventas",
        groups=SALES_GROUPS,
    )
    def tool_search_sale_orders(self, args):
        self._xtd_ai_check_dates(args.get("date_from"), args.get("date_to"))
        domain = self._xtd_ai_company_domain(args)
        if args.get("partner"):
            partner = self._xtd_ai_resolve("res.partner", args["partner"])
            domain.append(("partner_id", "child_of", partner.commercial_partner_id.id))
        kind = args.get("kind", "all")
        if kind == "quotation":
            domain.append(("state", "in", ("draft", "sent")))
        elif kind == "order":
            domain.append(("state", "=", "sale"))
        if args.get("state"):
            domain.append(("state", "=", args["state"]))
        for operator, value in self._xtd_ai_day_bounds(
            args.get("date_from"), args.get("date_to")
        ):
            domain.append(("date_order", operator, value))
        if args.get("salesperson"):
            user = self._xtd_ai_resolve(
                "res.users", args["salesperson"], domain=[("share", "=", False)]
            )
            domain.append(("user_id", "=", user.id))
        if "min_amount" in args:
            domain.append(("amount_untaxed", ">=", args["min_amount"]))
        if "max_amount" in args:
            domain.append(("amount_untaxed", "<=", args["max_amount"]))
        limit = self._xtd_ai_limit(args.get("limit"))
        orders_model = self.env["sale.order"]
        orders = orders_model.search(
            domain, limit=limit, order="date_order desc, id desc"
        )
        total = (
            orders_model.search_count(domain) if len(orders) >= limit else len(orders)
        )
        rows = [self._xtd_ai_order_row(o) for o in orders]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": orders}

    @xtd_ai_tool(
        name="get_sale_order",
        title="Detalle de un presupuesto o pedido",
        description=(
            "Devuelve la cabecera (cliente, estado, fechas, comercial, tarifa, "
            "condiciones de pago, "
            "importes, notas) y las líneas (producto, descripción, cantidad, precio, "
            "descuento, "
            "impuestos, subtotal) de un presupuesto o pedido de venta. Acepta el id o "
            "la referencia "
            "(S00007). Con varias compañías activas, `company` desambigua referencias "
            "repetidas. "
            "No modifica datos."
        ),
        input_schema=_schema(
            {
                "order": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Id numérico o referencia del presupuesto/pedido.",
                },
                "company": _COMPANY,
            },
            ["order"],
        ),
        kind="read",
        skill="ventas",
        groups=SALES_GROUPS,
    )
    def tool_get_sale_order(self, args):
        order = self._xtd_ai_resolve(
            "sale.order", args["order"], domain=self._xtd_ai_company_domain(args)
        )
        data = self._xtd_ai_order_row(order)
        data.update(
            {
                "team": order.team_id.name or None,
                "pricelist": order.pricelist_id.name or None,
                "payment_term": order.payment_term_id.name or None,
                "fiscal_position": order.fiscal_position_id.name or None,
                "amount_tax": self._xtd_ai_money(order.amount_tax, order.currency_id),
                "invoice_status": order.invoice_status,
                "opportunity": (
                    {
                        "id": order.opportunity_id.id,
                        "name": self._xtd_ai_text(order.opportunity_id.name),
                    }
                    if "opportunity_id" in order._fields and order.opportunity_id
                    else None
                ),
                "notes": self._xtd_ai_plain(order.note),
            }
        )
        lines = order.order_line.sorted("sequence")
        rows = []
        for line in lines[:MAX_LINES]:
            if line.display_type:
                rows.append(
                    {
                        "id": line.id,
                        "display_type": line.display_type,
                        "name": self._xtd_ai_text(line.name),
                    }
                )
                continue
            rows.append(
                {
                    "id": line.id,
                    "product": (
                        {
                            "id": line.product_id.id,
                            "code": line.product_id.default_code or None,
                        }
                        if line.product_id
                        else None
                    ),
                    "name": self._xtd_ai_text(line.name),
                    "quantity": line.product_uom_qty,
                    "uom": line.product_uom_id.name or None,
                    "price_unit": line.price_unit,
                    "discount": line.discount,
                    "taxes": ", ".join(line.tax_ids.mapped("name")) or None,
                    "subtotal": self._xtd_ai_money(
                        line.price_subtotal, order.currency_id
                    ),
                }
            )
        data["lines"] = rows
        data["lines_truncated"] = len(lines) > MAX_LINES
        return {"data": data, "records": order}

    _SALES_GROUPBY = {
        "customer": "partner_id",
        "product": "product_id",
        "salesperson": "user_id",
        "month": "date:month",
    }

    @xtd_ai_tool(
        name="sales_report",
        title="Informe de ventas",
        description=(
            "SOLO totales agregados, NO lista documentos: cada fila es un grupo "
            "(cliente, producto, "
            "comercial o mes), no un pedido, y no devuelve números de pedido ni "
            "presupuesto. Mide "
            "importe sin impuestos, unidades y número de pedidos (`orders` por fila, "
            "`total_orders` "
            "en total; `lines` son líneas de pedido, no pedidos). Por defecto solo "
            "pedidos "
            "confirmados; con include_quotations=true suma también presupuestos (no "
            "cancelados). "
            "Úsala para totales y rankings («qué cliente compra más», «ventas por "
            "mes»). NO la uses "
            "para responder «¿qué pedidos/presupuestos tengo?» ni para mostrar cuáles "
            "son: para "
            "listar documentos (referencias e importes) usa search_sale_orders. "
            "Respeta los permisos "
            "del usuario. Con varias compañías activas y sin `company`, devuelve "
            "filas y totales "
            "separados por compañía (cada una en su moneda); con `company` filtra por "
            "una. "
            "No modifica datos."
        ),
        input_schema=_schema(
            {
                "group_by": {
                    "type": "string",
                    "enum": sorted(_SALES_GROUPBY),
                    "description": "customer, product, salesperson o month.",
                },
                "date_from": _DATE
                | {"description": "Fecha del pedido desde (incluida), AAAA-MM-DD."},
                "date_to": _DATE
                | {"description": "Fecha del pedido hasta (incluida), AAAA-MM-DD."},
                "include_quotations": {
                    "type": "boolean",
                    "description": "Incluir presupuestos en borrador o enviados.",
                },
                "company": _COMPANY,
                "limit": _LIMIT,
            },
            ["group_by", "date_from", "date_to"],
        ),
        kind="read",
        skill="ventas",
        groups=SALES_GROUPS,
        requires=["sale.report"],
    )
    def tool_sales_report(self, args):
        self._xtd_ai_check_dates(args["date_from"], args["date_to"])
        report = self.env["sale.report"]
        states = (
            ["sale", "done"]
            if "done" in dict(report._fields["state"].selection)
            else ["sale"]
        )
        if args.get("include_quotations"):
            states += ["draft", "sent"]
        domain = [("state", "in", states)] + self._xtd_ai_company_domain(args)
        split = self._xtd_ai_split_companies(args)
        for operator, value in self._xtd_ai_day_bounds(
            args["date_from"], args["date_to"]
        ):
            domain.append(("date", operator, value))
        group_by = args["group_by"]
        groupby = self._SALES_GROUPBY[group_by]
        # order_reference ("sale.order,<id>") gives the number of distinct orders;
        # __count
        # counts order lines, which is not what users mean by "how many orders".
        aggregates = [
            "price_subtotal:sum",
            "product_uom_qty:sum",
            "order_reference:count_distinct",
            "__count",
        ]
        order = groupby if group_by == "month" else "price_subtotal:sum desc"
        groups = report._read_group(
            domain,
            [groupby] + (["company_id"] if split else []),
            aggregates,
            order=order,
        )
        currency = (self._xtd_ai_company(args) or self.env.company).currency_id
        rows = []
        for key in groups:
            group, *company, amount, qty, orders, count = key
            row = {
                "amount_untaxed": self._xtd_ai_money(
                    amount, company[0].currency_id if company else currency
                ),
                "quantity": round(qty or 0.0, 4),
                "orders": orders,
                "lines": count,
            }
            if company:
                row["company"] = company[0].name
            if group_by == "month":
                row["month"] = group.strftime("%Y-%m") if group else None
            elif group_by == "customer":
                row["customer"] = (
                    {"id": group.id, "name": self._xtd_ai_text(group.name)}
                    if group
                    else None
                )
            elif group_by == "product":
                row["product"] = (
                    {"id": group.id, "name": self._xtd_ai_text(group.display_name)}
                    if group
                    else None
                )
            else:
                row["salesperson"] = (
                    {"id": group.id, "name": group.name} if group else None
                )
            rows.append(row)
        data = self._xtd_ai_list(rows, limit=args.get("limit"))
        data.update({"group_by": group_by, "states": states})
        if split:
            data["totals_by_company"] = [
                {
                    "company": company.name,
                    "total_amount_untaxed": self._xtd_ai_money(
                        t_amount, company.currency_id
                    ),
                    "total_quantity": round(t_qty or 0.0, 4),
                    "total_orders": t_orders,
                }
                for company, t_amount, t_qty, t_orders, _count in report._read_group(
                    domain, ["company_id"], aggregates, order="company_id"
                )
            ]
        else:
            totals = report._read_group(domain, [], aggregates)
            t_amount, t_qty, t_orders, t_count = (
                totals[0] if totals else (0.0, 0.0, 0, 0)
            )
            data.update(
                {
                    "total_amount_untaxed": self._xtd_ai_money(t_amount, currency),
                    "total_quantity": round(t_qty or 0.0, 4),
                    "total_orders": t_orders,
                }
            )
        return {"data": data, "records": []}

    # ------------------------------------------------------------------
    # Sales: drafts
    # ------------------------------------------------------------------
    def _xtd_ai_line_commands(self, lines):
        """Validate the requested lines and return ``(commands, resolved_rows)``."""
        if not lines:
            raise XtdAiToolError(
                "validation", self.env._("Faltan las líneas del presupuesto.")
            )
        if len(lines) > 50:
            raise XtdAiToolError(
                "validation", self.env._("Máximo 50 líneas por llamada.")
            )
        commands, resolved = [], []
        for index, line in enumerate(lines, 1):
            if line["quantity"] <= 0:
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "La cantidad de la línea %s debe ser mayor que 0.", index
                    ),
                )
            product = self._xtd_ai_resolve(
                "product.product", line["product"], domain=[("sale_ok", "=", True)]
            )
            vals = {"product_id": product.id, "product_uom_qty": line["quantity"]}
            if "price_unit" in line:
                vals["price_unit"] = line["price_unit"]
            if "discount" in line:
                vals["discount"] = line["discount"]
            commands.append(Command.create(vals))
            resolved.append((product, vals))
        return commands, resolved

    def _xtd_ai_quotation_vals(self, args):
        partner = self._xtd_ai_resolve("res.partner", args["partner"])
        commands, resolved = self._xtd_ai_line_commands(args.get("lines"))
        vals = {"partner_id": partner.id, "order_line": commands}
        if args.get("validity_date"):
            vals["validity_date"] = args["validity_date"]
        if args.get("client_order_ref"):
            vals["client_order_ref"] = args["client_order_ref"].strip()
        return partner, vals, resolved

    def _xtd_ai_preview_lines(self, order, resolved):
        rows = [
            {
                "product": self._xtd_ai_text(product.display_name),
                "quantity": vals["product_uom_qty"],
                "price_unit": line.price_unit,
                "discount": line.discount,
                "subtotal": self._xtd_ai_money(line.price_subtotal, order.currency_id),
            }
            for line, (product, vals) in zip(order.order_line, resolved, strict=False)
        ]
        return rows

    def _xtd_ai_quotation_preview(self, args, show_company=False):
        partner, vals, resolved = self._xtd_ai_quotation_vals(args)
        # ``new`` computes pricelist, taxes and totals without touching the database
        # (and without consuming the order sequence).
        order = self.env["sale.order"].new(vals)
        count = len(resolved)
        summary = self.env._(
            "Presupuesto para %(partner)s: %(count)s líneas, %(amount)s sin impuestos",
            partner=partner.name,
            count=count,
            amount=self._xtd_ai_money_fmt(order.amount_untaxed, order.currency_id),
        )
        if show_company:
            summary = (
                self.env._("[%(company)s] ", company=self.env.company.name) + summary
            )
        return {
            "summary": summary,
            "lines": self._xtd_ai_preview_lines(order, resolved),
        }

    @xtd_ai_tool(
        name="create_sale_quotation",
        title="Crear presupuesto",
        description=(
            "Crea un presupuesto de venta NUEVO en borrador para un cliente "
            "existente, con una o "
            "más líneas (producto y cantidad; precio y descuento opcionales). Tarifa, "
            "impuestos, "
            "posición fiscal y condiciones de pago los calcula XTD según el cliente. "
            "Antes busca "
            "cliente y productos (search_partners, search_products) y confirma con el "
            "usuario las "
            "cantidades que falten. No confirma, no envía y no sirve para añadir "
            "líneas a un "
            "presupuesto existente (usa add_sale_order_lines). Si el cliente no "
            "existe, usa "
            "create_contact antes. Con varias compañías activas se crea en `company` "
            "(o en la "
            "primera activa si se omite). Devuelve la referencia y los importes."
        ),
        input_schema=_schema(
            {
                "partner": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Cliente. " + _REF,
                },
                "lines": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": _LINE_SCHEMA,
                },
                "validity_date": _DATE
                | {"description": "Fecha de validez del presupuesto, AAAA-MM-DD."},
                "client_order_ref": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Referencia del cliente (su número de pedido).",
                },
                "company": _COMPANY,
            },
            ["partner", "lines"],
        ),
        kind="draft",
        skill="ventas",
        groups=SALES_GROUPS,
        preview="_xtd_ai_preview_create_sale_quotation",
    )
    def tool_create_sale_quotation(self, args):
        scoped = self._xtd_ai_scoped(args)
        _partner, vals, _resolved = scoped._xtd_ai_quotation_vals(args)
        order = scoped.env["sale.order"].create(vals)
        if order.state != "draft":
            raise XtdAiDraftOnlyError(
                self.env._("El presupuesto no ha quedado en borrador.")
            )
        data = self._xtd_ai_order_row(order)
        if self._xtd_ai_multi():
            data["company"] = order.company_id.name
        data["lines_count"] = len(order.order_line)
        return {"data": data, "records": order}

    def _xtd_ai_preview_create_sale_quotation(self, args):
        return self._xtd_ai_scoped(args)._xtd_ai_quotation_preview(
            args, self._xtd_ai_multi()
        )

    def _xtd_ai_editable_order(self, ref):
        order = self._xtd_ai_resolve("sale.order", ref)
        if order.state != "draft":
            raise XtdAiToolError(
                "validation",
                self.env._(
                    "Solo se pueden añadir líneas a presupuestos en borrador (no "
                    "enviados ni confirmados); "
                    "%(name)s está en estado %(state)s.",
                    name=order.name,
                    state=order.state,
                ),
            )
        return order

    @xtd_ai_tool(
        name="add_sale_order_lines",
        title="Añadir líneas a un presupuesto",
        description=(
            "Añade líneas (producto y cantidad; precio y descuento opcionales) a un "
            "presupuesto "
            "existente que siga en borrador. Se rechaza si ya fue enviado, confirmado "
            "o cancelado. "
            "No modifica ni borra las líneas actuales. Para un presupuesto nuevo usa "
            "create_sale_quotation. Devuelve las líneas añadidas (producto, cantidad, "
            "precio unitario "
            "aplicado, descuento, subtotal) y los nuevos importes del presupuesto "
            "(sin impuestos y total)."
        ),
        input_schema=_schema(
            {
                "order": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Id numérico o referencia del presupuesto (S00007).",
                },
                "lines": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": _LINE_SCHEMA,
                },
            },
            ["order", "lines"],
        ),
        kind="draft",
        skill="ventas",
        groups=SALES_GROUPS,
        preview="_xtd_ai_preview_add_sale_order_lines",
    )
    def tool_add_sale_order_lines(self, args):
        order = self._xtd_ai_editable_order(args["order"])
        commands, _resolved = self._xtd_ai_scoped(record=order)._xtd_ai_line_commands(
            args["lines"]
        )
        before_lines = order.order_line
        order.write({"order_line": commands})
        if order.state != "draft":
            raise XtdAiDraftOnlyError(
                self.env._("El presupuesto no ha quedado en borrador.")
            )
        data = self._xtd_ai_order_row(order)
        new_lines = (order.order_line - before_lines).sorted("sequence")
        data["lines_added"] = len(new_lines)
        data["lines_count"] = len(order.order_line)
        data["added_lines"] = [
            {
                "id": line.id,
                "product": self._xtd_ai_text(line.product_id.display_name or line.name),
                "quantity": line.product_uom_qty,
                "price_unit": line.price_unit,
                "discount": line.discount,
                "subtotal": self._xtd_ai_money(line.price_subtotal, order.currency_id),
            }
            for line in new_lines
            if not line.display_type
        ]
        return {"data": data, "records": order}

    def _xtd_ai_preview_add_sale_order_lines(self, args):
        order = self._xtd_ai_editable_order(args["order"])
        _commands, resolved = self._xtd_ai_scoped(record=order)._xtd_ai_line_commands(
            args["lines"]
        )
        new_lines = self.env["sale.order.line"]
        for _product, vals in resolved:
            new_lines |= self.env["sale.order.line"].new(vals | {"order_id": order.id})
        added = sum(new_lines.mapped("price_subtotal"))
        summary = self.env._(
            "Añadir %(count)s líneas a %(name)s (%(partner)s): %(amount)s sin "
            "impuestos",
            count=len(resolved),
            name=order.name,
            partner=order.partner_id.name,
            amount=self._xtd_ai_money_fmt(added, order.currency_id),
        )
        rows = [
            {
                "product": self._xtd_ai_text(product.display_name),
                "quantity": vals["product_uom_qty"],
                "price_unit": line.price_unit,
                "discount": line.discount,
                "subtotal": self._xtd_ai_money(line.price_subtotal, order.currency_id),
            }
            for line, (product, vals) in zip(new_lines, resolved, strict=False)
        ]
        return {"summary": summary, "lines": rows}

    # ------------------------------------------------------------------
    # Stock availability (read-only, with the salesperson's own rights)
    # ------------------------------------------------------------------
    def _xtd_ai_availability_figures(self, products, can_read_moves):
        """``{product_id: (on_hand, forecasted|None, free)}`` for ``products`` in this
        env.

        With access to stock.move (e.g. sale_stock grants it to salespeople) the
        standard computed fields are used. Without it (stock only), the quants
        (readable by every internal user) give on hand and free; the forecast is
        then unknown (None).
        """
        if can_read_moves:
            return {
                p.id: (p.qty_available, p.virtual_available, p.free_qty)
                for p in products
            }
        figures = {p.id: (0.0, None, 0.0) for p in products}
        groups = (
            self.env["stock.quant"]
            .with_context(active_test=False)
            ._read_group(
                [
                    ("product_id", "in", products.ids),
                    ("location_id.usage", "=", "internal"),
                ],
                ["product_id"],
                ["quantity:sum", "reserved_quantity:sum"],
            )
        )
        for product, quantity, reserved in groups:
            figures[product.id] = (quantity, None, quantity - reserved)
        return figures

    @xtd_ai_tool(
        name="get_product_availability",
        title="Consultar disponibilidad de stock de un producto",
        description=(
            "Dice si hay stock de un producto: cantidad en mano, prevista (tras "
            "entradas y salidas "
            "pendientes) y libre (no reservada), por compañía si el usuario tiene "
            "varias activas. "
            "Úsala para «¿tenemos stock de X?» o antes de prometer una entrega. "
            "`product` es el id "
            "numérico, la referencia interna, el código de barras o parte del nombre; "
            "si coincide "
            "con varios productos devuelve hasta 10 con su disponibilidad. Los "
            "productos no "
            "almacenables (servicios, consumibles sin control de stock) no tienen "
            "existencias. "
            "No reserva ni modifica nada. Con `company` filtra por una compañía."
        ),
        input_schema=_schema(
            {
                "product": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 100,
                    "description": (
                        "Id numérico, referencia interna, código de barras o parte "
                        "del nombre."
                    ),
                },
                "company": _COMPANY,
            },
            ["product"],
        ),
        kind="read",
        skill="ventas",
        groups=SALES_GROUPS,
        requires=["stock.quant"],
    )
    def tool_get_product_availability(self, args):
        text = args["product"].strip()
        Product = self.env["product.product"]
        if re.fullmatch(r"\d{1,12}", text):
            domain = [("id", "=", int(text))]
        else:
            domain = [
                "|",
                "|",
                ("name", "ilike", text),
                ("default_code", "ilike", text),
                ("barcode", "=", text),
            ]
        products = Product.search(
            domain + [("type", "!=", "service")],
            limit=11,
            order="default_code, name, id",
        )
        if not products:
            raise XtdAiToolError(
                "not_found",
                self.env._("No se ha encontrado ningún producto «%s».", text),
            )
        truncated = len(products) > 10
        products = products[:10]
        company = self._xtd_ai_company(args)
        companies = company or (
            self.env.companies if self._xtd_ai_multi() else self.env.company
        )
        can_read_moves = self.env["stock.move"].has_access("read")
        per_company = {}
        for comp in companies:
            scoped = products.with_context(allowed_company_ids=[comp.id])
            scoped_toolbox = self.with_context(allowed_company_ids=[comp.id])
            per_company[comp.id] = scoped_toolbox._xtd_ai_availability_figures(
                scoped, can_read_moves
            )
        rows = []
        for product in products:
            row = {
                "id": product.id,
                "code": product.default_code or None,
                "name": self._xtd_ai_text(product.display_name),
                "uom": product.uom_id.name or None,
                "stockable": bool(product.is_storable),
            }
            if product.is_storable:
                entries = []
                for comp in companies:
                    on_hand, forecast, free = per_company[comp.id][product.id]
                    entry = {"on_hand": on_hand, "forecasted": forecast, "free": free}
                    if len(companies) > 1:
                        entry = dict({"company": comp.name}, **entry)
                    entries.append(entry)
                if len(entries) == 1:
                    row.update(entries[0])
                else:
                    row["by_company"] = entries
            rows.append(row)
        data = {"items": rows, "truncated": truncated}
        if not can_read_moves:
            data["note"] = self.env._(
                "Sin previsión: tu usuario no puede ver los movimientos de stock."
            )
        return {"data": data, "records": products}
