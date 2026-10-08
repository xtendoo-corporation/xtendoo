# -*- coding: utf-8 -*-

from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class XtdDashboardBlock(models.Model):
    _name = "xtd.dashboard.block"
    _description = "Xtd Dashboard Block"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    technical_key = fields.Char(required=True, index=True)
    block_type = fields.Selection(
        selection=[
            ("kpi_grid", "KPI Grid"),
            ("chart", "Chart"),
            ("list", "List"),
            ("status", "Status"),
            ("custom", "Custom"),
        ],
        required=True,
        default="custom",
    )
    component = fields.Char(
        required=True,
        help="Frontend component key used by the Xtd dashboard OWL renderer.",
    )
    model_name = fields.Char()
    action_xmlid = fields.Char()
    default_size = fields.Selection(
        selection=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
            ("full", "Full Width"),
        ],
        required=True,
        default="medium",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    config = fields.Json(default=dict)

    _technical_key_unique = models.Constraint(
        "UNIQUE(technical_key)",
        "The technical key of a dashboard block must be unique.",
    )


class XtdDashboardLayoutMixin(models.AbstractModel):
    _name = "xtd.dashboard.layout.mixin"
    _description = "Xtd Dashboard Layout Mixin"

    block_id = fields.Many2one(
        "xtd.dashboard.block",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    size = fields.Selection(
        selection=[
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
            ("full", "Full Width"),
        ],
        required=True,
        default="medium",
    )
    visible = fields.Boolean(default=True)
    config = fields.Json(default=dict)


class XtdDashboardLayout(models.Model):
    _name = "xtd.dashboard.layout"
    _inherit = "xtd.dashboard.layout.mixin"
    _description = "Xtd Global Dashboard Layout"
    _order = "sequence, id"


class XtdDashboardUserLayout(models.Model):
    _name = "xtd.dashboard.user.layout"
    _inherit = "xtd.dashboard.layout.mixin"
    _description = "Xtd User Dashboard Layout"
    _order = "sequence, id"

    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        ondelete="cascade",
    )

    _user_block_unique = models.Constraint(
        "UNIQUE(user_id, block_id)",
        "A user dashboard can only contain a block once.",
    )


class XtdDashboardService(models.AbstractModel):
    _name = "xtd.dashboard.service"
    _description = "Xtd Dashboard Service"

    @api.model
    def get_dashboard_layout(self):
        user = self.env.user
        use_custom = bool(user.xtd_use_custom_dashboard)
        can_edit_global = user.has_group("base.group_system")
        layout_model = "xtd.dashboard.user.layout" if use_custom else "xtd.dashboard.layout"
        domain = [("visible", "=", True), ("block_id.active", "=", True)]
        if use_custom:
            domain.append(("user_id", "=", user.id))

        layout_lines = self.env[layout_model].sudo().search(domain)
        if use_custom and not layout_lines:
            layout_lines = self.env["xtd.dashboard.layout"].sudo().search([
                ("visible", "=", True),
                ("block_id.active", "=", True),
            ])
            use_custom = False

        return {
            "mode": "user" if use_custom else "global",
            "can_customize": use_custom,
            "can_edit": use_custom or can_edit_global,
            "can_edit_global": can_edit_global,
            "blocks": [self._format_layout_line(line) for line in layout_lines],
        }

    def _format_layout_line(self, line):
        block = line.block_id
        config = {}
        config.update(block.config or {})
        config.update(line.config or {})
        config = self._with_field_labels(block.model_name, config)
        return {
            "id": line.id,
            "block_id": block.id,
            "key": block.technical_key,
            "name": block.name,
            "type": block.block_type,
            "component": block.component,
            "model": block.model_name,
            "action_xmlid": block.action_xmlid,
            "size": line.size or block.default_size,
            "sequence": line.sequence,
            "can_delete": self._can_delete_block(block),
            "config": config,
        }

    @api.model
    def save_dashboard_layout(self, blocks):
        user = self.env.user
        use_custom = bool(user.xtd_use_custom_dashboard)
        if not use_custom and not user.has_group("base.group_system"):
            return self.get_dashboard_layout()
        if not blocks:
            return self.get_dashboard_layout()
        layout_model = self.env["xtd.dashboard.user.layout" if use_custom else "xtd.dashboard.layout"].sudo()
        domain = [("user_id", "=", user.id)] if use_custom else []
        existing_lines = layout_model.search(domain)
        existing_by_block_id = {line.block_id.id: line for line in existing_lines}

        visible_block_ids = set()
        for index, block_data in enumerate(blocks):
            block_id = int(block_data["block_id"])
            visible_block_ids.add(block_id)
            vals = {
                "sequence": (index + 1) * 10,
                "size": block_data.get("size") or "medium",
                "visible": True,
                "config": block_data.get("config") or {},
            }
            line = existing_by_block_id.get(block_id)
            if line:
                line.write(vals)
            else:
                create_vals = {
                    **vals,
                    "block_id": block_id,
                }
                if use_custom:
                    create_vals["user_id"] = user.id
                layout_model.create(create_vals)

        lines_to_hide = existing_lines.filtered(lambda line: line.block_id.id not in visible_block_ids)
        if lines_to_hide:
            lines_to_hide.write({"visible": False})

        return self.get_dashboard_layout()

    # ------------------------------------------------------------------
    # Resumen (KPIs, últimos elementos y estado de pedidos) en una sola llamada
    # ------------------------------------------------------------------
    _KPI_SPECS = {
        "sales": {
            "model": "sale.order",
            "domain": [("state", "in", ["sale", "done"])],
            "date_field": "date_order",
            "is_datetime": True,
            "amount_field": "amount_total",
            "currency_field": "currency_id",
        },
        "orders": {
            "model": "sale.order",
            "domain": [("state", "in", ["draft", "sent"])],
            "date_field": "date_order",
            "is_datetime": True,
            "amount_field": "amount_total",
            "currency_field": "currency_id",
        },
        "purchase_orders": {
            "model": "purchase.order",
            "domain": [("state", "in", ["purchase", "done"])],
            "date_field": "date_order",
            "is_datetime": True,
            "amount_field": "amount_total",
            "currency_field": "currency_id",
        },
        "invoiced": {
            "model": "account.move",
            "domain": [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
            "date_field": "invoice_date",
            "is_datetime": False,
            "amount_field": "amount_total_signed",
            "currency_field": "company_currency_id",
        },
    }

    @api.model
    def get_dashboard_summary(self, period="month"):
        """Devuelve todo lo que necesitan las tarjetas KPI del dashboard.

        Los importes se agregan en servidor y se convierten a la moneda de la
        empresa activa. Los registros se filtran por las empresas
        seleccionadas (``allowed_company_ids`` del contexto) mediante las
        reglas de registro habituales.
        """
        if period not in ("week", "month", "year"):
            period = "month"
        ranges = self._period_ranges(period)
        company = self.env.company
        kpis = {}
        recent = {}
        for key, spec in self._KPI_SPECS.items():
            if spec["model"] not in self.env or not self.env[spec["model"]].has_access("read"):
                kpis[key] = self._empty_kpi()
                recent[key] = []
                continue
            current = self._kpi_totals(spec, ranges["current"])
            previous = self._kpi_totals(spec, ranges["previous"])
            kpis[key] = {
                "value": current["count"],
                "previous_value": previous["count"],
                "total": current["total"],
                "previous_total": previous["total"],
            }
            recent[key] = self._recent_records(spec, ranges["current"])
        return {
            "kpis": kpis,
            "recent": recent,
            "order_status": self._order_status(),
            "currency": company.currency_id.name,
        }

    @api.model
    def _empty_kpi(self):
        return {"value": 0, "previous_value": 0, "total": 0.0, "previous_total": 0.0}

    @api.model
    def _period_ranges(self, period):
        """Rangos [inicio, fin) del periodo actual y del anterior, en fechas locales."""
        today = fields.Date.context_today(self)
        if period == "week":
            start = today - relativedelta(days=today.weekday())
            end = start + relativedelta(days=7)
            prev_start = start - relativedelta(days=7)
        elif period == "year":
            start = today.replace(month=1, day=1)
            end = start + relativedelta(years=1)
            prev_start = start - relativedelta(years=1)
        else:
            start = today.replace(day=1)
            end = start + relativedelta(months=1)
            prev_start = start - relativedelta(months=1)
        return {"current": (start, end), "previous": (prev_start, start)}

    @api.model
    def _local_day_start_utc(self, day):
        """Medianoche local del usuario para ``day``, como datetime UTC naive."""
        tz = pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
        local_midnight = tz.localize(datetime.combine(day, time.min))
        return local_midnight.astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _kpi_period_domain(self, spec, date_range):
        start, end = date_range
        if spec["is_datetime"]:
            start, end = self._local_day_start_utc(start), self._local_day_start_utc(end)
        return list(spec["domain"]) + [
            (spec["date_field"], ">=", start),
            (spec["date_field"], "<", end),
        ]

    @api.model
    def _to_company_currency(self, amount, currency):
        company = self.env.company
        if not amount or not currency or currency == company.currency_id:
            return amount or 0.0
        return currency._convert(amount, company.currency_id, company, fields.Date.context_today(self))

    @api.model
    def _kpi_totals(self, spec, date_range):
        Model = self.env[spec["model"]]
        groups = Model._read_group(
            self._kpi_period_domain(spec, date_range),
            [spec["currency_field"]],
            ["__count", f"{spec['amount_field']}:sum"],
        )
        count = 0
        total = 0.0
        for currency, group_count, amount in groups:
            count += group_count
            total += self._to_company_currency(amount, currency)
        return {"count": count, "total": total}

    @api.model
    def _recent_records(self, spec, date_range, limit=3):
        Model = self.env[spec["model"]]
        records = Model.search(
            self._kpi_period_domain(spec, date_range),
            limit=limit,
            order=f"{spec['date_field']} desc, id desc",
        )
        result = []
        for record in records:
            record_date = record[spec["date_field"]]
            if spec["is_datetime"] and record_date:
                record_date = fields.Datetime.context_timestamp(self, record_date).date()
            amount = abs(record[spec["amount_field"]])
            result.append({
                "id": record.id,
                "name": record.display_name,
                "partner_id": [record.partner_id.id, record.partner_id.display_name] if record.partner_id else False,
                "amount_total": self._to_company_currency(amount, record[spec["currency_field"]]),
                "date": fields.Date.to_string(record_date) if record_date else "",
            })
        return result

    @api.model
    def _order_status(self):
        if "sale.order" not in self.env or not self.env["sale.order"].has_access("read"):
            return []
        SaleOrder = self.env["sale.order"]
        labels = dict(SaleOrder._fields["state"]._description_selection(self.env))
        order = list(labels)
        groups = [
            (state, count)
            for state, count in SaleOrder._read_group([], ["state"], ["__count"])
            if count
        ]
        groups.sort(key=lambda group: order.index(group[0]) if group[0] in order else len(order))
        return [
            {"state": state, "count": count, "label": labels.get(state, state)}
            for state, count in groups
        ]

    @api.model
    def delete_custom_block(self, block_id):
        user = self.env.user
        use_custom = bool(user.xtd_use_custom_dashboard)
        if not use_custom and not user.has_group("base.group_system"):
            return self.get_dashboard_layout()

        block = self.env["xtd.dashboard.block"].sudo().browse(int(block_id)).exists()
        if not block or not self._can_delete_block(block):
            return self.get_dashboard_layout()

        self.env["xtd.dashboard.layout"].sudo().search([("block_id", "=", block.id)]).unlink()
        self.env["xtd.dashboard.user.layout"].sudo().search([("block_id", "=", block.id)]).unlink()
        block.unlink()
        return self.get_dashboard_layout()

    def _can_delete_block(self, block):
        return bool(block and block.component in {"generic_list", "generic_calendar", "generic_kanban"} and block.technical_key.startswith("custom_"))

    def _with_field_labels(self, model_name, config):
        config = dict(config or {})
        field_names = config.get("fields") or []
        if not model_name or model_name not in self.env or not field_names:
            return config
        fields_info = self.env[model_name].fields_get(field_names)
        config["field_labels"] = {
            field_name: fields_info.get(field_name, {}).get("string") or field_name
            for field_name in field_names
        }
        config["field_types"] = {
            field_name: fields_info.get(field_name, {}).get("type")
            for field_name in field_names
        }
        return config

