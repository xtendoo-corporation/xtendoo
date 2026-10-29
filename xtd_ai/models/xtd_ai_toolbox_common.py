from odoo import fields, models

from ..tools import xtd_ai_tool
from ..tools.errors import XtdAiToolError

_KIND_ENUM = ["customer", "supplier", "any"]


class XtdAiToolboxCommon(models.AbstractModel):
    _name = "xtd.ai.toolbox.common"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: common"

    _xtd_ai_skills = {"contactos": "data/skills/contactos.md"}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="get_user_context",
        title="Contexto del usuario",
        description=(
            "Devuelve el usuario, su idioma y zona horaria, la compañía activa, las "
            "compañías "
            "permitidas, la fecha de hoy y si las acciones requieren confirmación. "
            "Úsala si "
            "necesitas la fecha actual o la compañía; no hace falta para el resto de "
            "consultas."
        ),
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        kind="read",
    )
    def tool_get_user_context(self, args):
        user = self.env.user
        company = self.env.company
        companies = self.env["res.company"].browse(
            self.env.context.get("allowed_company_ids") or []
        )
        return {
            "data": {
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "lang": user.lang,
                    "tz": user.tz,
                },
                "company": {
                    "id": company.id,
                    "name": company.name,
                    "currency": company.currency_id.name,
                },
                "allowed_companies": [{"id": c.id, "name": c.name} for c in companies],
                "today": str(fields.Date.context_today(self)),
                "confirm_writes": user._xtd_ai_needs_confirmation("draft"),
            },
            "records": [],
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="load_skill",
        title="Cargar instrucciones de un área",
        description=(
            "Carga las instrucciones detalladas de un área de negocio (qué preguntar "
            "antes de "
            "crear, cómo interpretar términos). Llámala una vez antes de trabajar en "
            "esa área si "
            "no conoces el criterio. Devuelve texto de instrucciones."
        ),
        input_schema=lambda toolbox: {
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "enum": sorted(toolbox._xtd_ai_skill_files()),
                    "description": "Nombre de la skill.",
                }
            },
            "required": ["skill"],
            "additionalProperties": False,
        },
        kind="read",
    )
    def tool_load_skill(self, args):
        text = self._xtd_ai_read_skill(args["skill"])
        return {"data": {"skill": args["skill"], "instructions": text}, "records": []}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="search_partners",
        title="Buscar contactos",
        description=(
            "Busca contactos (clientes, proveedores, empresas, personas) por nombre, "
            "NIF, "
            "referencia, email o ciudad. Devuelve id, nombre, NIF y datos básicos. "
            "Úsala antes "
            "de crear nada para reutilizar un contacto existente. No modifica datos."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2, "maxLength": 100},
                "kind": {"type": "string", "enum": _KIND_ENUM},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        kind="read",
        skill="contactos",
    )
    def tool_search_partners(self, args):
        query = args["query"].strip()
        domain = [
            "|",
            "|",
            "|",
            "|",
            ("name", "ilike", query),
            ("vat", "ilike", query),
            ("ref", "ilike", query),
            ("email", "ilike", query),
            ("city", "ilike", query),
        ]
        partner_model = self.env["res.partner"]
        kind = args.get("kind", "any")
        if kind == "customer" and "customer_rank" in partner_model._fields:
            domain = [("customer_rank", ">", 0)] + domain
        elif kind == "supplier" and "supplier_rank" in partner_model._fields:
            domain = [("supplier_rank", ">", 0)] + domain
        limit = self._xtd_ai_limit(args.get("limit"))
        partners = partner_model.search(domain, limit=limit, order="name, id")
        total = (
            partner_model.search_count(domain)
            if len(partners) >= limit
            else len(partners)
        )
        rows = [self._xtd_ai_partner_row(p) for p in partners]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": partners}

    def _xtd_ai_partner_row(self, partner):
        return {
            "id": partner.id,
            "name": self._xtd_ai_text(partner.name),
            "is_company": partner.is_company,
            "vat": partner.vat or None,
            "ref": partner.ref or None,
            "email": self._xtd_ai_text(partner.email),
            "phone": self._xtd_ai_text(partner.phone),
            "city": self._xtd_ai_text(partner.city),
            "country": partner.country_id.code or None,
        }

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="get_partner_summary",
        title="Ficha de un contacto",
        description=(
            "Ficha corta de un contacto y totales visibles para el usuario: pedidos "
            "de venta y "
            "compra, y pendiente de cobro y pago. Usa el id de search_partners. Solo "
            "lectura."
        ),
        input_schema={
            "type": "object",
            "properties": {"partner_id": {"type": "integer", "minimum": 1}},
            "required": ["partner_id"],
            "additionalProperties": False,
        },
        kind="read",
        skill="contactos",
    )
    def tool_get_partner_summary(self, args):
        partner = self._xtd_ai_resolve("res.partner", args["partner_id"])
        commercial = partner.commercial_partner_id
        data = self._xtd_ai_partner_row(partner)
        data["parent"] = (
            {
                "id": partner.parent_id.id,
                "name": self._xtd_ai_text(partner.parent_id.name),
            }
            if partner.parent_id
            else None
        )
        totals = {}
        env = self.env
        domain = [("partner_id", "child_of", commercial.id)]
        for key, model, extra in (
            ("sale_orders", "sale.order", [("state", "in", ("sale", "done"))]),
            (
                "purchase_orders",
                "purchase.order",
                [("state", "in", ("purchase", "done"))],
            ),
        ):
            if model in env and env[model].has_access("read"):
                totals[key] = env[model].search_count(domain + extra)
        if "account.move" in env and env["account.move"].has_access("read"):
            move = env["account.move"]
            company_currency = env.company.currency_id
            for key, types in (
                ("receivable_open", ("out_invoice", "out_refund")),
                ("payable_open", ("in_invoice", "in_refund")),
            ):
                groups = move._read_group(
                    domain
                    + [
                        ("move_type", "in", types),
                        ("state", "=", "posted"),
                        ("payment_state", "in", ("not_paid", "partial")),
                    ],
                    [],
                    ["amount_residual_signed:sum", "__count"],
                )
                amount, count = groups[0] if groups else (0.0, 0)
                totals[key] = {
                    "count": count,
                    "amount": self._xtd_ai_money(amount, company_currency),
                }
        data["totals"] = totals
        return {"data": data, "records": partner}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="search_products",
        title="Buscar productos",
        description=(
            "Busca productos por nombre, referencia interna o código de barras. "
            "Devuelve id, "
            "referencia, nombre, precio de venta y unidad. No modifica datos."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2, "maxLength": 100},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        kind="read",
        requires=["product.product"],
    )
    def tool_search_products(self, args):
        query = args["query"].strip()
        product_model = self.env["product.product"]
        domain = [
            "|",
            "|",
            ("name", "ilike", query),
            ("default_code", "ilike", query),
            ("barcode", "=", query),
        ]
        limit = self._xtd_ai_limit(args.get("limit"))
        products = product_model.search(
            domain, limit=limit, order="default_code, name, id"
        )
        total = (
            product_model.search_count(domain)
            if len(products) >= limit
            else len(products)
        )
        currency = self.env.company.currency_id
        uom_field = "uom_id" if "uom_id" in product_model._fields else None
        rows = [
            {
                "id": p.id,
                "code": p.default_code or None,
                "name": self._xtd_ai_text(p.display_name),
                "list_price": self._xtd_ai_money(p.list_price, currency),
                "uom": p[uom_field].name if uom_field else None,
            }
            for p in products
        ]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": products}

    # ------------------------------------------------------------------
    @xtd_ai_tool(
        name="create_contact",
        title="Crear contacto",
        description=(
            "Crea una empresa o persona nueva. Antes usa search_partners: la vista "
            "previa avisa "
            "de posibles duplicados por NIF, email o nombre. Siempre requiere "
            "confirmación del "
            "usuario. No sirve para modificar contactos existentes."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 2, "maxLength": 200},
                "is_company": {"type": "boolean"},
                "vat": {"type": "string", "maxLength": 40},
                "email": {"type": "string", "maxLength": 200},
                "phone": {"type": "string", "maxLength": 50},
                "street": {"type": "string", "maxLength": 200},
                "zip": {"type": "string", "maxLength": 20},
                "city": {"type": "string", "maxLength": 100},
                "country_code": {"type": "string", "minLength": 2, "maxLength": 2},
                "parent_id": {
                    "type": "integer",
                    "minimum": 1,
                    "description": (
                        "Solo para una persona de contacto de una empresa que ya "
                        "existe: id de esa empresa (search_partners). Omítelo para "
                        "empresas y para personas independientes."
                    ),
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        kind="create",
        skill="contactos",
        groups=["base.group_partner_manager"],
        preview="_xtd_ai_preview_create_contact",
    )
    def tool_create_contact(self, args):
        vals = self._xtd_ai_contact_vals(args)
        partner = self.env["res.partner"].create(vals)
        return {
            "data": {"id": partner.id, "name": self._xtd_ai_text(partner.name)},
            "records": partner,
        }

    def _xtd_ai_contact_vals(self, args):
        vals = {"name": args["name"].strip()}
        for key in ("vat", "email", "phone", "street", "zip", "city"):
            if args.get(key):
                vals[key] = args[key].strip()
        if "is_company" in args:
            vals["is_company"] = args["is_company"]
        if args.get("country_code"):
            country = self.env["res.country"].search(
                [("code", "=", args["country_code"].upper())], limit=1
            )
            if not country:
                raise XtdAiToolError(
                    "validation",
                    self.env._("Código de país desconocido: %s", args["country_code"]),
                )
            vals["country_id"] = country.id
        if args.get("parent_id"):
            if args.get("is_company"):
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "Una empresa no tiene empresa padre: quita parent_id y vuelve "
                        "a llamar a la herramienta."
                    ),
                )
            parent = self._xtd_ai_resolve("res.partner", args["parent_id"])
            if not parent.is_company:
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "parent_id debe ser una empresa (id %s no lo es). Si el "
                        "contacto no pertenece a una empresa, quita parent_id.",
                        parent.id,
                    ),
                )
            vals["parent_id"] = parent.id
        return vals

    def _xtd_ai_contact_card_lines(self, vals):
        """Confirmation card rows of a new contact, with Spanish labels."""
        labels = {
            "name": self.env._("Nombre"),
            "vat": self.env._("NIF"),
            "email": self.env._("Email"),
            "phone": self.env._("Teléfono"),
            "street": self.env._("Dirección"),
            "zip": self.env._("C.P."),
            "city": self.env._("Ciudad"),
        }
        lines = [
            {"field": label, "value": self._xtd_ai_text(vals[key])}
            for key, label in labels.items()
            if vals.get(key)
        ]
        if vals.get("country_id"):
            country = self.env["res.country"].browse(vals["country_id"])
            lines.append(
                {"field": self.env._("País"), "value": self._xtd_ai_text(country.name)}
            )
        if vals.get("parent_id"):
            # The parent must show on the card: it changes who the contact belongs to
            parent = self.env["res.partner"].browse(vals["parent_id"])
            lines.append(
                {
                    "field": self.env._("Empresa padre"),
                    "value": self._xtd_ai_text(parent.display_name),
                }
            )
        lines.append(
            {
                "field": self.env._("Tipo"),
                "value": self.env._("Empresa")
                if vals.get("is_company")
                else self.env._("Persona"),
            }
        )
        return lines

    def _xtd_ai_find_duplicates(self, vals):
        partner_model = self.env["res.partner"]
        clauses = [[("name", "=ilike", vals["name"])]]
        if vals.get("vat"):
            clauses.append([("vat", "=ilike", vals["vat"])])
        if vals.get("email"):
            clauses.append([("email", "=ilike", vals["email"])])
        domain = []
        for clause in clauses:
            domain = (["|"] + domain + clause) if domain else clause
        return partner_model.search(domain, limit=5)

    def _xtd_ai_preview_create_contact(self, args):
        vals = self._xtd_ai_contact_vals(args)
        duplicates = self._xtd_ai_find_duplicates(vals)
        kind = (
            self.env._("empresa") if vals.get("is_company") else self.env._("contacto")
        )
        summary = self.env._("Crear %(kind)s «%(name)s»", kind=kind, name=vals["name"])
        if duplicates:
            summary += " - " + self.env._("posibles duplicados: %s", len(duplicates))
        lines = self._xtd_ai_contact_card_lines(vals)
        return {
            "summary": summary,
            "lines": lines,
            "duplicates": [self._xtd_ai_partner_row(p) for p in duplicates],
        }
