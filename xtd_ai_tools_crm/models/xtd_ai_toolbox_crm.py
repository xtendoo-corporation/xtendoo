import re
from datetime import date, datetime, time, timedelta

import pytz

from odoo import fields, models
from odoo.exceptions import AccessError
from odoo.tools import html2plaintext, plaintext2html
from odoo.tools.misc import formatLang

from odoo.addons.xtd_ai.tools import (
    XtdAiDraftOnlyError,
    XtdAiToolError,
    xtd_ai_tool,
)

SALES_GROUPS = ["sales_team.group_sale_salesman"]
SALES_MANAGER_GROUP = "sales_team.group_sale_manager"

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


class XtdAiToolboxCrm(models.AbstractModel):
    _name = "xtd.ai.toolbox.crm"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: CRM"

    _xtd_ai_skills = {"crm": "data/skills/crm.md"}

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

    def _xtd_ai_is_sales_manager(self):
        return self.env.user.has_group(SALES_MANAGER_GROUP)

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
    # CRM: read
    # ------------------------------------------------------------------
    def _xtd_ai_lead_status(self, lead):
        if lead.stage_id.is_won:
            return "won"
        if not lead.active:
            return "lost"
        return "open"

    def _xtd_ai_lead_row(self, lead):
        currency = lead.company_currency
        return {
            "id": lead.id,
            "name": self._xtd_ai_text(lead.name),
            "status": self._xtd_ai_lead_status(lead),
            "partner": (
                {
                    "id": lead.partner_id.id,
                    "name": self._xtd_ai_text(lead.partner_id.name),
                }
                if lead.partner_id
                else None
            ),
            "stage": lead.stage_id.name or None,
            "salesperson": self._xtd_ai_user_name(lead.user_id),
            "team": lead.team_id.name or None,
            "expected_revenue": self._xtd_ai_money(lead.expected_revenue, currency),
            "probability": lead.probability,
            "prorated_revenue": self._xtd_ai_money(lead.prorated_revenue, currency),
            "date_deadline": self._xtd_ai_iso(lead.date_deadline),
            **self._xtd_ai_label({}, lead),
        }

    def _xtd_ai_lead_status_domain(self, status):
        """Return ``(domain, model)``; lost opportunities are archived ones."""
        lead = self.env["crm.lead"]
        if status == "won":
            return [("type", "=", "opportunity"), ("stage_id.is_won", "=", True)], lead
        if status == "lost":
            return [
                ("type", "=", "opportunity"),
                ("active", "=", False),
                ("probability", "=", 0),
            ], lead.with_context(active_test=False)
        if status == "all":
            return [("type", "=", "opportunity")], lead.with_context(active_test=False)
        return [
            ("type", "=", "opportunity"),
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
        ], lead

    @xtd_ai_tool(
        name="search_opportunities",
        title="Buscar oportunidades",
        description=(
            "Lista oportunidades del CRM con filtros: estado (open = abiertas por "
            "defecto, won, lost "
            "o all), etapa, comercial, equipo, cliente, ingreso esperado "
            "mínimo/máximo y rango de "
            "fecha de cierre prevista. Devuelve nombre, cliente, etapa, comercial, "
            "equipo, ingreso "
            "esperado, probabilidad, ingreso ponderado y fecha prevista. Para totales "
            "por etapa, "
            "comercial o equipo usa pipeline_report. Solo ve lo que el usuario puede "
            "ver. Cubre todas las compañías activas del usuario; con `company` filtra "
            "por una; cada elemento indica su compañía si hay varias. "
            "No modifica datos."
        ),
        input_schema=_schema(
            {
                "status": {
                    "type": "string",
                    "enum": ["open", "won", "lost", "all"],
                    "description": "open (por defecto), won, lost o all.",
                },
                "stage": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Etapa. " + _REF,
                },
                "salesperson": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Comercial. " + _REF,
                },
                "team": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Equipo de ventas. " + _REF,
                },
                "partner": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Cliente. " + _REF,
                },
                "min_revenue": {
                    "type": "number",
                    "description": "Ingreso esperado mínimo.",
                },
                "max_revenue": {
                    "type": "number",
                    "description": "Ingreso esperado máximo.",
                },
                "deadline_from": _DATE
                | {"description": "Cierre previsto desde (incluida), AAAA-MM-DD."},
                "deadline_to": _DATE
                | {"description": "Cierre previsto hasta (incluida), AAAA-MM-DD."},
                "company": _COMPANY,
                "limit": _LIMIT,
            }
        ),
        kind="read",
        skill="crm",
        groups=SALES_GROUPS,
    )
    def tool_search_opportunities(self, args):
        self._xtd_ai_check_dates(args.get("deadline_from"), args.get("deadline_to"))
        domain, leads = self._xtd_ai_lead_status_domain(args.get("status", "open"))
        domain += self._xtd_ai_company_domain(args)
        if args.get("stage"):
            domain.append(
                ("stage_id", "=", self._xtd_ai_resolve("crm.stage", args["stage"]).id)
            )
        if args.get("salesperson"):
            user = self._xtd_ai_resolve(
                "res.users", args["salesperson"], domain=[("share", "=", False)]
            )
            domain.append(("user_id", "=", user.id))
        if args.get("team"):
            domain.append(
                ("team_id", "=", self._xtd_ai_resolve("crm.team", args["team"]).id)
            )
        if args.get("partner"):
            partner = self._xtd_ai_resolve("res.partner", args["partner"])
            domain.append(("partner_id", "child_of", partner.commercial_partner_id.id))
        if "min_revenue" in args:
            domain.append(("expected_revenue", ">=", args["min_revenue"]))
        if "max_revenue" in args:
            domain.append(("expected_revenue", "<=", args["max_revenue"]))
        if args.get("deadline_from"):
            domain.append(("date_deadline", ">=", args["deadline_from"]))
        if args.get("deadline_to"):
            domain.append(("date_deadline", "<=", args["deadline_to"]))
        limit = self._xtd_ai_limit(args.get("limit"))
        found = leads.search(domain, limit=limit, order="date_deadline asc, id desc")
        total = leads.search_count(domain) if len(found) >= limit else len(found)
        rows = [self._xtd_ai_lead_row(lead) for lead in found]
        return {"data": self._xtd_ai_list(rows, total, limit), "records": found}

    @xtd_ai_tool(
        name="get_opportunity",
        title="Detalle de una oportunidad",
        description=(
            "Devuelve el detalle de una oportunidad: cliente, contacto, etapa, "
            "comercial, equipo, "
            "ingreso esperado, probabilidad, fechas y descripción. Acepta el id o el "
            "nombre; `company` "
            "desambigua nombres repetidos entre compañías activas. No modifica datos."
        ),
        input_schema=_schema(
            {
                "opportunity": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "Id numérico o nombre de la oportunidad.",
                },
                "company": _COMPANY,
            },
            ["opportunity"],
        ),
        kind="read",
        skill="crm",
        groups=SALES_GROUPS,
    )
    def tool_get_opportunity(self, args):
        lead = self.with_context(active_test=False)._xtd_ai_resolve(
            "crm.lead",
            args["opportunity"],
            domain=[("type", "=", "opportunity")] + self._xtd_ai_company_domain(args),
        )
        data = self._xtd_ai_lead_row(lead)
        data.update(
            {
                "contact_name": self._xtd_ai_text(lead.contact_name),
                "email_from": self._xtd_ai_text(lead.email_from),
                "phone": self._xtd_ai_text(lead.phone),
                "priority": lead.priority,
                "created": self._xtd_ai_iso(lead.create_date),
                "date_closed": self._xtd_ai_iso(lead.date_closed),
                "lost_reason": lead.lost_reason_id.name or None,
                "description": self._xtd_ai_plain(lead.description),
            }
        )
        return {"data": data, "records": lead}

    _PIPELINE_GROUPBY = {
        "stage": "stage_id",
        "salesperson": "user_id",
        "team": "team_id",
    }

    @xtd_ai_tool(
        name="pipeline_report",
        title="Informe del pipeline",
        description=(
            "Agrega las oportunidades por etapa, comercial o equipo: número, ingreso "
            "esperado y "
            "ingreso ponderado (ingreso esperado x probabilidad). Por defecto solo "
            "oportunidades "
            "abiertas; status permite won, lost o all. Admite filtrar por fecha de "
            "cierre prevista. "
            "Úsala para «cómo está el pipeline» o «cuánto prevemos cerrar»; para ver "
            "oportunidades "
            "concretas usa search_opportunities. Con varias compañías activas y sin "
            "`company`, "
            "separa filas y totales por compañía (cada una en su moneda); con "
            "`company` filtra por una. "
            "No modifica datos."
        ),
        input_schema=_schema(
            {
                "group_by": {
                    "type": "string",
                    "enum": sorted(_PIPELINE_GROUPBY),
                    "description": "stage (por defecto), salesperson o team.",
                },
                "status": {
                    "type": "string",
                    "enum": ["open", "won", "lost", "all"],
                    "description": "open (por defecto), won, lost o all.",
                },
                "deadline_from": _DATE
                | {"description": "Cierre previsto desde (incluida), AAAA-MM-DD."},
                "deadline_to": _DATE
                | {"description": "Cierre previsto hasta (incluida), AAAA-MM-DD."},
                "company": _COMPANY,
            }
        ),
        kind="read",
        skill="crm",
        groups=SALES_GROUPS,
    )
    def tool_pipeline_report(self, args):
        self._xtd_ai_check_dates(args.get("deadline_from"), args.get("deadline_to"))
        domain, leads = self._xtd_ai_lead_status_domain(args.get("status", "open"))
        domain += self._xtd_ai_company_domain(args)
        split = self._xtd_ai_split_companies(args)
        if args.get("deadline_from"):
            domain.append(("date_deadline", ">=", args["deadline_from"]))
        if args.get("deadline_to"):
            domain.append(("date_deadline", "<=", args["deadline_to"]))
        group_by = args.get("group_by", "stage")
        groupby = self._PIPELINE_GROUPBY[group_by]
        aggregates = ["__count", "expected_revenue:sum", "prorated_revenue:sum"]
        order = None if group_by == "stage" else "expected_revenue:sum desc"
        groups = leads._read_group(
            domain,
            [groupby] + (["company_id"] if split else []),
            aggregates,
            order=order,
        )
        currency = (self._xtd_ai_company(args) or self.env.company).currency_id
        rows = []
        for key in groups:
            group, *company, count, expected, prorated = key
            row_currency = (
                (company[0] or self.env.company).currency_id if company else currency
            )
            row = {
                "count": count,
                "expected_revenue": self._xtd_ai_money(expected, row_currency),
                "prorated_revenue": self._xtd_ai_money(prorated, row_currency),
            }
            if company:
                row["company"] = company[0].name or None
            if group_by == "stage":
                row["stage"] = {"id": group.id, "name": group.name} if group else None
            elif group_by == "team":
                row["team"] = {"id": group.id, "name": group.name} if group else None
            else:
                row["salesperson"] = (
                    {"id": group.id, "name": group.name} if group else None
                )
            rows.append(row)
        data = self._xtd_ai_list(rows)
        data.update({"group_by": group_by, "status": args.get("status", "open")})
        if split:
            data["totals_by_company"] = [
                {
                    "company": company.name or None,
                    "total_count": t_count,
                    "total_expected_revenue": self._xtd_ai_money(
                        t_expected, (company or self.env.company).currency_id
                    ),
                    "total_prorated_revenue": self._xtd_ai_money(
                        t_prorated, (company or self.env.company).currency_id
                    ),
                }
                for company, t_count, t_expected, t_prorated in leads._read_group(
                    domain, ["company_id"], aggregates, order="company_id"
                )
            ]
        else:
            totals = leads._read_group(domain, [], aggregates)
            t_count, t_expected, t_prorated = totals[0] if totals else (0, 0.0, 0.0)
            data.update(
                {
                    "total_count": t_count,
                    "total_expected_revenue": self._xtd_ai_money(t_expected, currency),
                    "total_prorated_revenue": self._xtd_ai_money(t_prorated, currency),
                }
            )
        return {"data": data, "records": []}

    # ------------------------------------------------------------------
    # CRM: draft
    # ------------------------------------------------------------------
    def _xtd_ai_opportunity_vals(self, args):
        vals = {"name": args["name"].strip(), "type": "opportunity"}
        partner = None
        if args.get("partner"):
            partner = self._xtd_ai_resolve("res.partner", args["partner"])
            vals["partner_id"] = partner.id
        for key in ("contact_name", "email_from"):
            if args.get(key):
                vals[key] = args[key].strip()
        if "expected_revenue" in args:
            vals["expected_revenue"] = args["expected_revenue"]
        if "probability" in args:
            if not 0 < args["probability"] < 100:
                raise XtdAiToolError(
                    "validation",
                    self.env._(
                        "La probabilidad debe estar entre 1 y 99: 0 y 100 equivalen a "
                        "perder o ganar."
                    ),
                )
            vals["probability"] = args["probability"]
        if args.get("date_deadline"):
            vals["date_deadline"] = args["date_deadline"]
        if args.get("description"):
            vals["description"] = plaintext2html(args["description"])
        user = self.env.user
        if args.get("salesperson"):
            user = self._xtd_ai_resolve(
                "res.users", args["salesperson"], domain=[("share", "=", False)]
            )
            if user != self.env.user and not self._xtd_ai_is_sales_manager():
                raise AccessError(
                    self.env._(
                        "Solo un responsable de ventas puede asignar oportunidades a "
                        "otro comercial."
                    )
                )
        vals["user_id"] = user.id
        if args.get("team"):
            vals["team_id"] = self._xtd_ai_resolve("crm.team", args["team"]).id
        return partner, user, vals

    @xtd_ai_tool(
        name="create_opportunity",
        title="Crear oportunidad",
        description=(
            "Crea una oportunidad NUEVA en el CRM, en la primera etapa (nunca ganada "
            "ni perdida). "
            "Indica un nombre y, si se conoce, el cliente existente o bien nombre y "
            "email de "
            "contacto, ingreso esperado, probabilidad (1 a 99, opcional), fecha de "
            "cierre prevista "
            "y notas en texto plano. El comercial es el propio usuario; solo un "
            "responsable de "
            "ventas puede asignarla a otro. No sirve para ganar, perder ni mover "
            "etapas. Con varias "
            "compañías activas se crea en `company` (o en la primera activa si se "
            "omite). Devuelve "
            "el id y los datos principales."
        ),
        input_schema=_schema(
            {
                "name": {
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 200,
                    "description": "Nombre de la oportunidad.",
                },
                "partner": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Cliente existente. " + _REF,
                },
                "contact_name": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Nombre de contacto si no hay cliente.",
                },
                "email_from": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Email de contacto si no hay cliente.",
                },
                "expected_revenue": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Ingreso esperado.",
                },
                "probability": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 99,
                    "description": (
                        "Probabilidad en % (1 a 99). Omítela para que la calcule Odoo."
                    ),
                },
                "salesperson": {
                    "type": "string",
                    "maxLength": 200,
                    "description": (
                        "Comercial. Solo un responsable de ventas puede indicar a otro."
                    ),
                },
                "team": {
                    "type": "string",
                    "maxLength": 100,
                    "description": "Equipo de ventas. " + _REF,
                },
                "date_deadline": _DATE
                | {"description": "Cierre previsto, AAAA-MM-DD."},
                "description": {
                    "type": "string",
                    "maxLength": 2000,
                    "description": "Notas en texto plano.",
                },
                "company": _COMPANY,
            },
            ["name"],
        ),
        kind="draft",
        skill="crm",
        groups=SALES_GROUPS,
        preview="_xtd_ai_preview_create_opportunity",
    )
    def tool_create_opportunity(self, args):
        scoped = self._xtd_ai_scoped(args)
        _partner, _user, vals = scoped._xtd_ai_opportunity_vals(args)
        lead = scoped.env["crm.lead"].create(vals)
        if (
            lead.type != "opportunity"
            or not lead.active
            or lead.stage_id.is_won
            or lead.probability in (0, 100)
        ):
            raise XtdAiDraftOnlyError(
                self.env._("La oportunidad no ha quedado abierta.")
            )
        data = self._xtd_ai_lead_row(lead)
        if self._xtd_ai_multi():
            data["company"] = lead.company_id.name
        return {"data": data, "records": lead}

    def _xtd_ai_preview_create_opportunity(self, args):
        show_company = self._xtd_ai_multi()
        self = self._xtd_ai_scoped(args)  # noqa: PLW0642
        partner, user, vals = self._xtd_ai_opportunity_vals(args)
        currency = self.env.company.currency_id
        summary = self.env._(
            "Oportunidad «%(name)s»%(partner)s, comercial %(user)s, ingreso esperado "
            "%(amount)s",
            name=vals["name"],
            partner=(" " + self.env._("para %s", partner.name)) if partner else "",
            user=user.name,
            amount=self._xtd_ai_money_fmt(vals.get("expected_revenue", 0.0), currency),
        )
        lines = [
            {"field": key, "value": self._xtd_ai_text(value)}
            for key, value in vals.items()
            if key
            in ("name", "contact_name", "email_from", "probability", "date_deadline")
        ]
        if show_company:
            summary = (
                self.env._("[%(company)s] ", company=self.env.company.name) + summary
            )
            lines.append({"field": "company", "value": self.env.company.name})
        return {"summary": summary, "lines": lines}
