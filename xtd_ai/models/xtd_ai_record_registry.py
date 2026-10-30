"""Declarative registry of what the generic tools may create and edit (§6.5).

It is a whitelist: a model or a field that is not declared here cannot be
touched by ``create_record`` / ``update_record``, and a field declared with
risk ``forbidden`` can never be written, whatever the policy says. Bridge
modules (``xtd_ai_tools_*``) add their models by inheriting this model and
extending ``_xtd_ai_record_specs``::

    class XtdAiRecordRegistry(models.AbstractModel):
        _inherit = "xtd.ai.record.registry"

        def _xtd_ai_record_specs(self):
            specs = super()._xtd_ai_record_specs()
            specs["sale.order"] = {...}
            return specs

Model spec keys:

- ``label``: Spanish name for cards and messages. ``skill``: skill that
  explains it.
- ``create`` / ``update``: whether each generic tool may do it.
- ``create_class``: policy class of a creation (``create_master`` or
  ``create_draft``).
- ``domain``: records the tools may edit (list, or the name of a registry
  method ``f(model) -> list``), on top of the user's record rules.
- ``duplicates``: ``[(field, operator)]`` checked before creating or when
  editing those fields; any match turns the action into a card.
- ``check``: registry method ``f(record_or_empty, vals)`` raising
  ``XtdAiToolError`` for business validations; it is called first with the
  field names only (values ``None``) and then with the converted values.
- ``effects``: registry method ``f(record_or_empty, vals) -> [str]`` for
  the card ("Afecta a los presupuestos nuevos...").
- ``undo_create``: the created record can be undone (``xtd.ai.undo``).
- ``fields``: ``{name: spec}``; field spec keys: ``label``, ``risk``
  (``low`` | ``money`` | ``forbidden``), ``risk_update`` (risk when editing,
  defaults to ``risk``), ``money_above`` (policy method returning a threshold:
  a numeric value above it is ``money``), ``create`` / ``update`` (False to
  restrict it to one of the tools), ``domain`` (for relational values),
  ``required`` (on create), ``max_length``.
"""

import re
from datetime import date, datetime

from odoo import Command, api, models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext

from ..tools.errors import XtdAiToolError

RISKS = ("low", "money", "forbidden")

# Red lines (§5): these models can never be registered, by any module.
RED_LINE_MODELS = (
    "res.partner.bank",
    "res.users",
    "res.groups",
    "res.company",
    "account.payment",
    "account.payment.register",
    "account.batch.payment",
    "account.bank.statement",
    "account.bank.statement.line",
    "account.account",
    "account.tax",
    "account.journal",
    "account.fiscal.position",
    "account.lock_exception",
    "hr.employee",
    "hr.contract",
    "hr.payslip",
    "hr.version",
    "sign.request",
    "base.automation",
    "mail.mail",
    "mail.message",
)
RED_LINE_PREFIXES = ("ir.", "res.users", "hr.payslip", "base.", "auth")
# Fields never writable whatever a spec says (bank accounts, users, companies,
# states, accounting properties...).
RED_LINE_FIELDS = (
    "bank_ids",
    "user_ids",
    "company_id",
    "company_ids",
    "state",
    "move_type",
    "journal_id",
    "posted_before",
    "group_ids",
    "groups_id",
    "password",
    "employee_ids",
    "message_ids",
    "activity_ids",
)
RED_LINE_FIELD_PREFIXES = (
    "property_account_",
    "property_payment_",
    "property_supplier_payment",
    "acc_",
    "bank_",
)
CHAR_LIMIT = 200
TEXT_LIMIT = 2000
MAX_CHANGES = 15
_TRUE = ("1", "true", "yes", "si", "sí", "verdadero", "on")
_FALSE = ("0", "false", "no", "falso", "off")


def is_red_line_model(model):
    return model in RED_LINE_MODELS or model.startswith(RED_LINE_PREFIXES)


def is_red_line_field(fname):
    return fname in RED_LINE_FIELDS or fname.startswith(RED_LINE_FIELD_PREFIXES)


class XtdAiRecordRegistry(models.AbstractModel):
    _name = "xtd.ai.record.registry"
    _description = "AI agent: registry of creatable and editable records"

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_record_specs(self):
        """``{model: spec}``; bridge modules extend it with ``super()``."""
        return {
            "res.partner": {
                "label": self.env._("contacto"),
                "skill": "contactos",
                # creation stays in create_contact (company/parent validation)
                "create": False,
                "update": True,
                "domain": "_xtd_ai_domain_res_partner",
                "duplicates": [("vat", "=ilike"), ("email", "=ilike")],
                "fields": {
                    "name": {"label": self.env._("Nombre"), "risk": "low"},
                    "phone": {"label": self.env._("Teléfono"), "risk": "low"},
                    "mobile": {"label": self.env._("Móvil"), "risk": "low"},
                    # redirects invoices and portal access: card (§4 Contactos)
                    "email": {"label": self.env._("Email"), "risk": "money"},
                    "website": {"label": self.env._("Web"), "risk": "low"},
                    "street": {"label": self.env._("Dirección"), "risk": "low"},
                    "street2": {"label": self.env._("Dirección 2"), "risk": "low"},
                    "zip": {"label": self.env._("C.P."), "risk": "low"},
                    "city": {"label": self.env._("Ciudad"), "risk": "low"},
                    "state_id": {"label": self.env._("Provincia"), "risk": "low"},
                    "country_id": {"label": self.env._("País"), "risk": "low"},
                    "user_id": {
                        "label": self.env._("Comercial"),
                        "risk": "low",
                        "domain": [("share", "=", False)],
                    },
                    "category_id": {"label": self.env._("Etiquetas"), "risk": "low"},
                    "comment": {"label": self.env._("Notas"), "risk": "low"},
                    "function": {"label": self.env._("Cargo"), "risk": "low"},
                    # tax identity: affects invoices and taxes (card)
                    "vat": {"label": self.env._("NIF"), "risk": "money"},
                    "bank_ids": {"risk": "forbidden"},
                    "active": {"risk": "forbidden"},
                    "parent_id": {"risk": "forbidden"},
                    "is_company": {"risk": "forbidden"},
                    "property_payment_term_id": {"risk": "forbidden"},
                    "property_account_position_id": {"risk": "forbidden"},
                    "credit_limit": {"risk": "forbidden"},
                },
            },
            "product.template": {
                "label": self.env._("producto"),
                "skill": "productos",
                "create": True,
                "update": True,
                "create_class": "create_master",
                "undo_create": True,
                "duplicates": [
                    ("name", "=ilike"),
                    ("default_code", "=ilike"),
                    ("barcode", "="),
                ],
                "effects": "_xtd_ai_effects_product_template",
                "fields": {
                    "name": {
                        "label": self.env._("Nombre"),
                        "risk": "low",
                        "required": True,
                    },
                    "default_code": {"label": self.env._("Referencia"), "risk": "low"},
                    "barcode": {"label": self.env._("Código de barras"), "risk": "low"},
                    "list_price": {
                        "label": self.env._("Precio de venta"),
                        "risk": "low",
                        "risk_update": "money",
                    },
                    "standard_price": {
                        "label": self.env._("Coste"),
                        "risk": "low",
                        "risk_update": "money",
                    },
                    "categ_id": {"label": self.env._("Categoría"), "risk": "low"},
                    "uom_id": {
                        "label": self.env._("Unidad"),
                        "risk": "low",
                        "risk_update": "money",
                    },
                    "type": {
                        "label": self.env._("Tipo"),
                        "risk": "low",
                        "risk_update": "money",
                    },
                    "is_storable": {
                        "label": self.env._("Controlar stock"),
                        "risk": "low",
                        "risk_update": "money",
                    },
                    "taxes_id": {
                        "label": self.env._("Impuestos de venta"),
                        "risk": "money",
                        "domain": "_xtd_ai_domain_sale_taxes",
                    },
                    "supplier_taxes_id": {
                        "label": self.env._("Impuestos de compra"),
                        "risk": "money",
                        "domain": "_xtd_ai_domain_purchase_taxes",
                    },
                    "sale_ok": {"label": self.env._("Se puede vender"), "risk": "low"},
                    "purchase_ok": {
                        "label": self.env._("Se puede comprar"),
                        "risk": "low",
                    },
                    "description_sale": {
                        "label": self.env._("Descripción de venta"),
                        "risk": "low",
                    },
                    # archive / restore: only on edit, and with a card (§4)
                    "active": {
                        "label": self.env._("Activo"),
                        "risk": "money",
                        "create": False,
                    },
                    "property_account_income_id": {"risk": "forbidden"},
                    "property_account_expense_id": {"risk": "forbidden"},
                    "seller_ids": {"risk": "forbidden"},
                    "attribute_line_ids": {"risk": "forbidden"},
                },
            },
        }

    # -- domains and effects of the base specs ---------------------------
    @api.model
    def _xtd_ai_domain_res_partner(self, model):
        # Partners of users (employees) and of companies are not contacts the
        # agent edits: their data belong to user and company administration.
        # sudo: only the ids of the companies' partners, to exclude them
        company_partners = self.env["res.company"].sudo().search([]).partner_id.ids
        return [("user_ids", "=", False), ("id", "not in", company_partners)]

    @api.model
    def _xtd_ai_domain_sale_taxes(self, model):
        return [
            ("type_tax_use", "=", "sale"),
            ("company_id", "in", self.env.companies.ids),
        ]

    @api.model
    def _xtd_ai_domain_purchase_taxes(self, model):
        return [
            ("type_tax_use", "=", "purchase"),
            ("company_id", "in", self.env.companies.ids),
        ]

    @api.model
    def _xtd_ai_effects_product_template(self, record, vals):
        effects = []
        if not record:
            effects.append(
                self.env._(
                    "Quedará disponible en presupuestos, compras y facturas; las "
                    "cuentas salen de su categoría."
                )
            )
        if record and "list_price" in vals:
            effects.append(
                self.env._(
                    "El precio nuevo se aplica a los presupuestos nuevos; los ya "
                    "hechos no cambian."
                )
            )
        if record and "standard_price" in vals:
            effects.append(
                self.env._("El coste nuevo cambia la valoración del stock y el margen.")
            )
        if record and vals.get("active") is False:
            effects.append(
                self.env._("Dejará de salir en búsquedas y documentos nuevos.")
            )
        return effects

    # ------------------------------------------------------------------
    # Reading the registry
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_specs(self):
        """Installed, valid specs. A red-line model raises (a programming error)."""
        result = {}
        for model, spec in self._xtd_ai_record_specs().items():
            if is_red_line_model(model):
                raise ValueError(f"AI record registry: {model} is a red line (§5)")
            if model not in self.env:
                continue
            model_fields = self.env[model]._fields
            fields_spec = {}
            for fname, fspec in spec.get("fields", {}).items():
                if fspec.get("risk") not in RISKS:
                    raise ValueError(f"AI record registry: bad risk {model}.{fname}")
                if fname not in model_fields:
                    continue
                if is_red_line_field(fname):
                    fspec = fspec | {"risk": "forbidden", "risk_update": "forbidden"}
                fields_spec[fname] = fspec
            result[model] = spec | {"fields": fields_spec}
        return result

    @api.model
    def _xtd_ai_spec(self, model, operation):
        spec = self._xtd_ai_specs().get(model)
        if not spec or not spec.get(operation):
            raise XtdAiToolError(
                "forbidden",
                self.env._(
                    "El agente no puede %(op)s registros de «%(model)s».",
                    op=self.env._("crear")
                    if operation == "create"
                    else self.env._("modificar"),
                    model=model,
                ),
            )
        return spec

    @api.model
    def _xtd_ai_has_access(self, model, operation):
        try:
            return self.env[model].has_access(operation)
        except AccessError:
            return False

    @api.model
    def _xtd_ai_models(self, operation):
        """Registered models the current user may create (or edit) with the ORM."""
        orm_op = "create" if operation == "create" else "write"
        return sorted(
            model
            for model, spec in self._xtd_ai_specs().items()
            if spec.get(operation) and self._xtd_ai_has_access(model, orm_op)
        )

    @api.model
    def _xtd_ai_record_domain(self, model, spec):
        domain = spec.get("domain") or []
        if isinstance(domain, str):
            domain = getattr(self, domain)(model)
        return list(domain)

    @api.model
    def _xtd_ai_editable_fields(self, model):
        """Field names of ``model`` the registry lets an update write."""
        spec = self._xtd_ai_specs().get(model) or {}
        return {
            fname
            for fname, fspec in spec.get("fields", {}).items()
            if fspec.get("update", True)
            and fspec.get("risk_update", fspec["risk"]) != "forbidden"
        }

    # ------------------------------------------------------------------
    # Changes: validation, conversion and risk
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_prepare(self, model, changes, record=None):
        """Validate ``changes`` (``[{"field", "value"}]``) against the registry.

        :returns: ``(vals, info)`` with ORM ``vals`` and per field
            ``{"label", "risk", "value"}`` (``value`` comparable/serialisable).
        :raises XtdAiToolError: field not declared, forbidden or invalid value.
        """
        operation = "update" if record else "create"
        spec = self._xtd_ai_spec(model, operation)
        if not changes:
            raise XtdAiToolError("validation", self.env._("No hay cambios que hacer."))
        if len(changes) > MAX_CHANGES:
            raise XtdAiToolError(
                "validation",
                self.env._("Demasiados cambios a la vez (máximo %s).", MAX_CHANGES),
            )
        if spec.get("check"):
            # first with the field names only: a field refused for this record
            # is reported before resolving its value
            names = {str(c.get("field") or "").strip(): None for c in changes}
            getattr(self, spec["check"])(record or self.env[model], names)
        vals, info = {}, {}
        for change in changes:
            fname = str(change.get("field") or "").strip()
            fspec = spec["fields"].get(fname)
            risk = fspec and fspec.get(
                "risk_update" if record else "risk", fspec["risk"]
            )
            if not fspec or risk == "forbidden" or is_red_line_field(fname):
                raise XtdAiToolError(
                    "forbidden",
                    self.env._(
                        "El campo «%(field)s» de %(model)s no se puede %(op)s desde "
                        "el agente. Campos permitidos: %(allowed)s.",
                        field=fname,
                        model=spec["label"],
                        op=self.env._("modificar")
                        if record
                        else self.env._("rellenar"),
                        allowed=", ".join(sorted(self._xtd_ai_allowed(spec, record))),
                    ),
                )
            if not fspec.get(operation, True):
                raise XtdAiToolError(
                    "forbidden",
                    self.env._(
                        "El campo «%s» no se puede usar en esta operación.", fname
                    ),
                )
            if fname in vals:
                raise XtdAiToolError(
                    "validation", self.env._("Campo repetido: %s.", fname)
                )
            orm_value, value = self._xtd_ai_convert(
                model, fname, fspec, change.get("value"), record
            )
            threshold = fspec.get("money_above")
            if threshold and isinstance(value, (int, float)):
                limit = getattr(self.env["xtd.ai.policy"], threshold)()
                if value > limit:
                    risk = "money"
            vals[fname] = orm_value
            info[fname] = {
                "label": fspec.get("label") or fname,
                "risk": risk,
                "value": value,
            }
        if not record:
            missing = [
                f
                for f, fs in spec["fields"].items()
                if fs.get("required") and f not in vals
            ]
            if missing:
                raise XtdAiToolError(
                    "validation",
                    self.env._("Falta un dato obligatorio: %s.", ", ".join(missing)),
                )
        if spec.get("check"):
            getattr(self, spec["check"])(record or self.env[model], vals)
        return vals, info

    @api.model
    def _xtd_ai_allowed(self, spec, record):
        key = "risk_update" if record else "risk"
        operation = "update" if record else "create"
        return [
            fname
            for fname, fspec in spec["fields"].items()
            if fspec.get(key, fspec["risk"]) != "forbidden"
            and fspec.get(operation, True)
        ]

    @api.model
    def _xtd_ai_convert(self, model, fname, fspec, raw, record):  # noqa: C901  one dispatcher by field type
        """``(orm_value, comparable_value)`` of a raw (string) value."""
        field = self.env[model]._fields[fname]
        label = fspec.get("label") or fname
        text = raw.strip() if isinstance(raw, str) else raw

        def bad(message):
            return XtdAiToolError(
                "validation",
                self.env._("%(field)s: %(message)s", field=label, message=message),
            )

        if text in (None, ""):
            if field.required or fspec.get("required"):
                raise bad(self.env._("es obligatorio."))
            empty = [] if field.type in ("many2many", "one2many") else False
            return ([Command.clear()] if empty == [] else False), empty
        ftype = field.type
        if ftype in ("char", "text", "html"):
            limit = fspec.get("max_length") or (
                CHAR_LIMIT if ftype == "char" else TEXT_LIMIT
            )
            value = str(text)
            if len(value) > limit:
                raise bad(self.env._("máximo %s caracteres.", limit))
            return value, value
        if ftype in ("float", "monetary", "integer"):
            try:
                number = (
                    float(text)
                    if isinstance(text, (int, float))
                    else float(str(text).replace(" ", "").replace(",", "."))
                )
            except ValueError:
                raise bad(self.env._("debe ser un número.")) from None
            if number < 0 and fname not in ("debit", "credit", "amount_currency"):
                raise bad(self.env._("no puede ser negativo."))
            if fname == "discount" and number > 100:
                raise bad(self.env._("no puede superar el 100 %."))
            if ftype == "integer":
                number = int(number)
            return number, number
        if ftype == "boolean":
            word = str(text).lower()
            if isinstance(text, bool):
                return text, text
            if word in _TRUE:
                return True, True
            if word in _FALSE:
                return False, False
            raise bad(self.env._("debe ser sí o no."))
        if ftype == "selection":
            options = dict(field._description_selection(self.env))
            word = str(text).lower()
            for key, option_label in options.items():
                if word in (str(key).lower(), str(option_label).lower()):
                    return key, key
            raise bad(self.env._("valores posibles: %s.", ", ".join(map(str, options))))
        if ftype in ("date", "datetime"):
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(text)):
                    raise ValueError
                day = date.fromisoformat(str(text))
            except ValueError:
                raise bad(self.env._("fecha en formato AAAA-MM-DD.")) from None
            if ftype == "datetime":
                moment = datetime.combine(day, datetime.min.time()).replace(hour=12)
                return moment, str(moment)
            return day, str(day)
        if ftype == "many2one":
            target = self._xtd_ai_resolve_value(field, fspec, text, model, record)
            return target.id, target.id
        if ftype == "many2many":
            current = set(record[fname].ids) if record else set()
            items = [i.strip() for i in re.split(r"[;,]", str(text)) if i.strip()]
            if not items:
                raise bad(self.env._("indica al menos un valor."))
            incremental = all(i[0] in "+-" for i in items)
            ids = set(current) if incremental else set()
            for item in items:
                sign = item[0] if item[0] in "+-" else "+"
                target = self._xtd_ai_resolve_value(
                    field, fspec, item.lstrip("+-").strip(), model, record
                )
                if sign == "-":
                    ids.discard(target.id)
                else:
                    ids.add(target.id)
            return [Command.set(sorted(ids))], sorted(ids)
        raise bad(self.env._("este tipo de campo no se puede editar."))

    @api.model
    def _xtd_ai_resolve_value(self, field, fspec, text, model, record=None):
        if is_red_line_model(field.comodel_name) and field.comodel_name not in (
            "res.users",
            "account.tax",
            "account.account",
        ):
            raise XtdAiToolError(
                "forbidden", self.env._("Ese tipo de dato no se puede asignar.")
            )
        domain = list(fspec.get("domain") or [])
        if isinstance(fspec.get("domain"), str):
            domain = getattr(self, fspec["domain"])(model)
        comodel = self.env[field.comodel_name]
        # values of the record's own company (an account, a tax of that company)
        company = record and "company_id" in record._fields and record.company_id
        if company:
            if "company_ids" in comodel._fields:
                domain = [*domain, ("company_ids", "in", company.ids)]
            elif "company_id" in comodel._fields:
                domain = [*domain, ("company_id", "in", [company.id, False])]
        # a code (account 629000, product reference) is not an id
        if "code" in comodel._fields and isinstance(text, str):
            by_code = comodel.search([*domain, ("code", "=", text.strip())], limit=2)
            if len(by_code) == 1:
                return by_code
        return self.env["xtd.ai.toolbox"]._xtd_ai_resolve(
            field.comodel_name, text, domain
        )

    @api.model
    def _xtd_ai_snapshot(self, record, fnames):
        """Comparable values of ``record`` for ``fnames`` (undo and audit)."""
        values = {}
        for fname in fnames:
            field = record._fields[fname]
            value = record[fname]
            if field.type == "many2one":
                value = value.id or False
            elif field.type in ("many2many", "one2many"):
                value = sorted(value.ids)
            elif field.type in ("date", "datetime"):
                value = str(value) if value else False
            elif field.type == "html":
                value = str(value or "")
            values[fname] = value
        return values

    @api.model
    def _xtd_ai_same(self, model, fname, left, right):
        field = self.env[model]._fields[fname]
        if field.type in ("float", "monetary"):
            return abs(float(left or 0.0) - float(right or 0.0)) < 1e-6
        if field.type == "html":
            return (
                html2plaintext(left or "").strip()
                == html2plaintext(right or "").strip()
            )
        if field.type in ("char", "text"):
            return (left or "") == (right or "")
        return left == right

    @api.model
    def _xtd_ai_display(self, model, fname, value):
        """Human text of a comparable value, for cards."""
        field = self.env[model]._fields[fname]
        if value in (False, None, "", []):
            return "—"
        if field.type == "many2one":
            return self.env[field.comodel_name].browse(value).display_name or "—"
        if field.type == "many2many":
            records = self.env[field.comodel_name].browse(value)
            return ", ".join(records.mapped("display_name")) or "—"
        if field.type == "selection":
            return dict(field._description_selection(self.env)).get(value, value)
        if field.type == "boolean":
            return self.env._("Sí") if value else self.env._("No")
        if field.type == "html":
            return html2plaintext(value).strip()[:200]
        if field.type in ("float", "monetary"):
            return f"{value:,.2f}"
        return str(value)[:200]

    @api.model
    def _xtd_ai_duplicates(self, model, spec, vals, record=None):
        """Records that look like the one being created (or edited into)."""
        clauses = []
        for fname, operator in spec.get("duplicates") or []:
            value = vals.get(fname)
            if value and isinstance(value, str):
                clauses.append([(fname, operator, value.strip())])
        if not clauses:
            return self.env[model]
        domain = []
        for clause in clauses:
            domain = (["|", *domain, *clause]) if domain else clause
        if record:
            domain = ["&", ("id", "!=", record.id), *domain]
        records = self.env[model]
        if "active" in records._fields:
            records = records.with_context(active_test=False)
        return records.search(domain, limit=5)

    @api.model
    def _xtd_ai_effects(self, spec, record, vals):
        if not spec.get("effects"):
            return []
        return getattr(self, spec["effects"])(record, vals)
