import re
from datetime import datetime, time, timedelta

import pytz

from odoo import fields, models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext

from odoo.addons.xtd_ai.tools import xtd_ai_tool
from odoo.addons.xtd_ai.tools.errors import XtdAiToolError

STOCK_GROUPS = ["stock.group_stock_user"]

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


class XtdAiToolboxStock(models.AbstractModel):
    _name = "xtd.ai.toolbox.stock"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: stock"

    _xtd_ai_skills = {"inventario": "data/skills/inventario.md"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ps_require_group(self, group, label):
        """Defence in depth: ACLs alone are not enough (stock.quant is readable by every
        internal user), so the tool group is checked again at execution time."""
        if not self.env.user.has_group(group):
            raise AccessError(self.env._("No tienes permiso para %s.", label))

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
