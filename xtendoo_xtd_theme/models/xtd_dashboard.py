# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from lxml import etree

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
            "available_blocks": [
                self._format_block(block)
                for block in self.env["xtd.dashboard.block"].sudo().search([("active", "=", True)])
            ],
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

    def _format_block(self, block):
        config = self._with_field_labels(block.model_name, block.config or {})
        return {
            "block_id": block.id,
            "key": block.technical_key,
            "name": block.name,
            "type": block.block_type,
            "component": block.component,
            "model": block.model_name,
            "action_xmlid": block.action_xmlid,
            "size": block.default_size,
            "sequence": block.sequence,
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

    @api.model
    def get_dashboard_kpis(self):
        today = fields.Date.today()
        first_of_month = today.replace(day=1)
        first_of_prev_month = (first_of_month - relativedelta(days=1)).replace(day=1)

        kpis = {
            "sales": {"value": 0, "trend": 0, "previous_value": 0, "label": "Ventas (mes)", "icon": "fa-money"},
            "orders": {"value": 0, "trend": 0, "previous_value": 0, "label": "Pedidos", "icon": "fa-shopping-bag"},
            "purchase_orders": {"value": 0, "trend": 0, "previous_value": 0, "label": "Pedidos de compra", "icon": "fa-truck"},
            "invoiced": {"value": 0, "trend": 0, "previous_value": 0, "label": "Facturado (mes)", "icon": "fa-file-text-o"},
        }

        # Ventas facturadas (account.move)
        try:
            self.env["account.move"].check_access_rights("read")
            cur_total = self.env["account.move"].read_group([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", first_of_month),
            ], ["amount_total:sum"], [])
            prev_total = self.env["account.move"].read_group([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", first_of_prev_month),
                ("invoice_date", "<", first_of_month),
            ], ["amount_total:sum"], [])
            cur_val = cur_total[0]["amount_total"] or 0 if cur_total else 0
            prev_val = prev_total[0]["amount_total"] or 0 if prev_total else 0
            kpis["sales"]["value"] = cur_val
            kpis["sales"]["previous_value"] = prev_val
            kpis["sales"]["trend"] = self._calc_trend(cur_val, prev_val)
            kpis["invoiced"]["value"] = cur_val
            kpis["invoiced"]["previous_value"] = prev_val
            kpis["invoiced"]["trend"] = self._calc_trend(cur_val, prev_val)
        except Exception:
            pass

        # Pedidos de venta (sale.order)
        try:
            self.env["sale.order"].check_access_rights("read")
            cur_count = self.env["sale.order"].search_count([
                ("state", "in", ["sale", "done"]),
                ("date_order", ">=", first_of_month),
            ])
            prev_count = self.env["sale.order"].search_count([
                ("state", "in", ["sale", "done"]),
                ("date_order", ">=", first_of_prev_month),
                ("date_order", "<", first_of_month),
            ])
            kpis["orders"]["value"] = cur_count
            kpis["orders"]["previous_value"] = prev_count
            kpis["orders"]["trend"] = self._calc_trend(cur_count, prev_count)
        except Exception:
            pass

        # Pedidos de compra (purchase.order)
        try:
            self.env["purchase.order"].check_access_rights("read")
            cur_count = self.env["purchase.order"].search_count([
                ("state", "in", ["purchase", "done"]),
                ("date_order", ">=", first_of_month),
            ])
            prev_count = self.env["purchase.order"].search_count([
                ("state", "in", ["purchase", "done"]),
                ("date_order", ">=", first_of_prev_month),
                ("date_order", "<", first_of_month),
            ])
            kpis["purchase_orders"]["value"] = cur_count
            kpis["purchase_orders"]["previous_value"] = prev_count
            kpis["purchase_orders"]["trend"] = self._calc_trend(cur_count, prev_count)
        except Exception:
            pass

        return kpis

    @api.model
    def get_sales_chart_data(self):
        today = fields.Date.today()
        start_date = (today - relativedelta(years=1)).replace(day=1)

        labels = []
        sales_by_month = {}
        orders_by_month = {}

        # Ventas mensuales agrupadas
        try:
            self.env["account.move"].check_access_rights("read")
            sales_data = self.env["account.move"].read_group([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", start_date),
            ], ["amount_total:sum"], ["invoice_date:month"])
            for item in sales_data:
                raw = item["invoice_date:month"]
                key = raw[:7] if isinstance(raw, str) else f"{raw['year']}-{str(raw['month']).zfill(2)}"
                sales_by_month[key] = item["amount_total"] or 0
        except Exception:
            pass

        # Pedidos mensuales agrupados
        try:
            self.env["sale.order"].check_access_rights("read")
            orders_data = self.env["sale.order"].read_group([
                ("state", "in", ["sale", "done"]),
                ("date_order", ">=", start_date),
            ], [], ["date_order:month"])
            for item in orders_data:
                raw = item["date_order:month"]
                key = raw[:7] if isinstance(raw, str) else f"{raw['year']}-{str(raw['month']).zfill(2)}"
                orders_by_month[key] = item["__count"] or 0
        except Exception:
            pass

        sales_arr = []
        orders_arr = []
        current = start_date
        while current <= today:
            key = current.strftime("%Y-%m")
            labels.append(current.strftime("%b %Y"))
            sales_arr.append(float(sales_by_month.get(key, 0) or 0))
            orders_arr.append(orders_by_month.get(key, 0) or 0)
            current += relativedelta(months=1)

        return {
            "labels": labels,
            "sales": sales_arr,
            "orders_count": orders_arr,
        }

    def _calc_trend(self, current, previous):
        if not previous:
            return 100.0 if current else 0.0
        return round(((current - previous) / previous) * 100, 1)

    @api.model
    def get_order_status_data(self):
        try:
            self.env["sale.order"].check_access_rights("read")
            data = self.env["sale.order"].read_group(
                [], ["state"], ["state"]
            )
            return [
                {"state": item["state"], "count": item["__count"]}
                for item in data
                if item["__count"] > 0
            ]
        except Exception:
            return []

    @api.model
    def get_block_builder_options(self, model_name=False):
        available_models = self.env["ir.model"].get_available_models()
        model_names = [model["model"] for model in available_models]
        model_records = self.env["ir.model"].sudo().search([("model", "in", model_names)])
        model_by_name = {model.model: model for model in model_records}
        module_names = set()
        for model in model_records:
            module_names.update(self._model_module_names(model))
        module_labels = self._get_module_labels(module_names)
        preferred_apps = ["sale", "stock", "purchase", "account", "contacts", "crm", "project"]
        app_options = [
            {
                "key": module_name,
                "name": module_labels.get(module_name) or module_name,
            }
            for module_name in sorted(
                module_names,
                key=lambda name: (
                    preferred_apps.index(name) if name in preferred_apps else 1000,
                    (module_labels.get(name) or name).lower(),
                ),
            )
        ]
        preferred_models = {
            "sale.order": 0,
            "stock.picking": 1,
            "purchase.order": 2,
            "account.move": 3,
            "res.partner": 4,
            "product.template": 5,
            "product.product": 6,
            "mail.activity": 7,
        }
        sorted_models = sorted(
            available_models,
            key=lambda model: (
                preferred_models.get(model["model"], 1000),
                model["display_name"].lower(),
                model["model"],
            ),
        )
        result = {
            "models": [
                {
                    "model": model["model"],
                    "name": model["display_name"],
                    "apps": self._model_module_names(model_by_name.get(model["model"])),
                }
                for model in sorted_models
            ],
            "apps": app_options,
            "fields": [],
        }
        if model_name and model_name in self.env:
            fields_info = self.env[model_name].fields_get()
            view_field_names = self._get_model_view_field_names(model_name)
            supported_types = {"char", "text", "html", "integer", "float", "monetary", "date", "datetime", "boolean", "selection", "many2one"}
            result["fields"] = [
                {
                    "name": field_name,
                    "string": field.get("string") or field_name,
                    "type": field.get("type"),
                }
                for field_name, field in sorted(fields_info.items(), key=lambda item: item[1].get("string") or item[0])
                if field_name in view_field_names and field.get("type") in supported_types
            ]
        return result

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

    @api.model
    def create_custom_block(self, vals):
        user = self.env.user
        use_custom = bool(user.xtd_use_custom_dashboard)
        if not use_custom and not user.has_group("base.group_system"):
            return self.get_dashboard_layout()

        block_type = vals.get("block_type") or "generic_list"
        if block_type not in {"generic_list", "generic_calendar", "generic_kanban"}:
            block_type = "generic_list"
        model_name = vals.get("model")
        if not model_name or model_name not in self.env:
            return self.get_dashboard_layout()
        if not self._can_read_model(model_name):
            return self.get_dashboard_layout()

        fields_list = vals.get("fields") or ["display_name"]
        if isinstance(fields_list, str):
            fields_list = [field.strip() for field in fields_list.split(",") if field.strip()]
        fields_info = self.env[model_name].fields_get()
        fields_list = [field for field in fields_list if field in fields_info][:6] or ["display_name"]
        date_field = vals.get("date_field")
        if date_field and date_field not in fields_info:
            date_field = False
        try:
            limit = int(vals.get("limit") or 5)
        except (TypeError, ValueError):
            limit = 5

        block = self.env["xtd.dashboard.block"].sudo().create({
            "name": vals.get("name") or self.env["ir.model"].sudo()._get(model_name).name,
            "technical_key": self._new_custom_block_key(model_name),
            "block_type": "list" if block_type == "generic_list" else "custom",
            "component": block_type,
            "model_name": model_name,
            "default_size": vals.get("size") or "medium",
            "config": {
                "fields": fields_list,
                "limit": max(1, min(limit, 20)),
                "domain": vals.get("domain") or [],
                "date_field": date_field,
            },
        })

        layout_model = self.env["xtd.dashboard.user.layout" if use_custom else "xtd.dashboard.layout"].sudo()
        layout_vals = {
            "block_id": block.id,
            "sequence": 999,
            "size": vals.get("size") or "medium",
            "visible": True,
        }
        if use_custom:
            layout_vals["user_id"] = user.id
        layout_model.create(layout_vals)
        return self.get_dashboard_layout()

    def _new_custom_block_key(self, model_name):
        base_key = f"custom_{model_name.replace('.', '_')}"
        key = base_key
        index = 1
        Block = self.env["xtd.dashboard.block"].sudo()
        while Block.search_count([("technical_key", "=", key)]):
            index += 1
            key = f"{base_key}_{index}"
        return key

    def _can_read_model(self, model_name):
        try:
            return self.env[model_name].check_access_rights("read", raise_exception=False)
        except Exception:
            return False

    def _can_delete_block(self, block):
        return bool(block and block.component in {"generic_list", "generic_calendar", "generic_kanban"} and block.technical_key.startswith("custom_"))

    def _model_module_names(self, model):
        if not model:
            return []
        modules = model.modules or ""
        return [module.strip() for module in modules.split(",") if module.strip()]

    def _get_module_labels(self, module_names):
        if not module_names:
            return {}
        modules = self.env["ir.module.module"].sudo().search([("name", "in", list(module_names))])
        labels = {}
        for module in modules:
            labels[module.name] = module.shortdesc or module.summary or module.name
        return labels

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

    def _get_model_view_field_names(self, model_name):
        view_field_names = set()
        views = self.env["ir.ui.view"].sudo().search([
            ("model", "=", model_name),
            ("type", "in", ["list", "form", "kanban", "calendar", "search"]),
        ])
        for view in views:
            try:
                arch = etree.fromstring(view.arch_db.encode())
            except Exception:
                continue
            view_field_names.update(
                field_name
                for field_name in arch.xpath("//field/@name")
                if field_name
            )
        return view_field_names or set(self.env[model_name]._fields)
