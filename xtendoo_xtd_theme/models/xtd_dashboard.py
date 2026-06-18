# -*- coding: utf-8 -*-

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
            "config": config,
        }

    def _format_block(self, block):
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
            "config": block.config or {},
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
