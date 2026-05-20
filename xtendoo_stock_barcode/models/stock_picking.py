# -*- coding: utf-8 -*-

import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "barcodes.barcode_events_mixin"]

    xt_barcode_mode = fields.Selection(
        selection=[
            ("product", "Producto"),
            ("source", "Ubicación origen"),
            ("destination", "Ubicación destino"),
            ("lot", "Lote/serie"),
            ("package", "Paquete"),
        ],
        string="Modo de escaneo",
        default="product",
        copy=False,
    )
    xt_barcode_current_line_id = fields.Many2one(
        "stock.move.line",
        string="Línea actual de escaneo",
        copy=False,
    )
    xt_barcode_source_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación origen escaneada",
        copy=False,
        domain="[('usage', '!=', 'view')]",
    )
    xt_barcode_destination_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación destino escaneada",
        copy=False,
        domain="[('usage', '!=', 'view')]",
    )
    xt_barcode_last_scan = fields.Char(string="Último código escaneado", copy=False)
    xt_barcode_last_message = fields.Text(string="Último mensaje de escaneo", copy=False)
    xt_barcode_current_package_id = fields.Many2one(
        "stock.package",
        string="Paquete actual de escaneo",
        copy=False,
    )
    xt_barcode_pending_tracking_count = fields.Integer(
        string="Líneas con lote/serie pendiente",
        compute="_compute_xt_barcode_pending_counts",
    )
    xt_barcode_pending_destination_count = fields.Integer(
        string="Líneas con destino pendiente",
        compute="_compute_xt_barcode_pending_counts",
    )
    xt_barcode_pending_package_count = fields.Integer(
        string="Líneas con paquete pendiente",
        compute="_compute_xt_barcode_pending_counts",
    )
    xt_barcode_supported = fields.Boolean(
        string="Barcode clásico disponible",
        compute="_compute_xt_barcode_supported",
    )

    def _compute_xt_barcode_supported(self):
        allowed_codes = set(self._barcode_scan_supported_operation_codes())
        for picking in self:
            picking.xt_barcode_supported = (
                picking.picking_type_code in allowed_codes
                and picking.state not in ("done", "cancel")
            )

    def _compute_xt_barcode_pending_counts(self):
        for picking in self:
            lines = picking._get_relevant_barcode_lines()
            picking.xt_barcode_pending_tracking_count = len(
                lines.filtered(lambda line: picking._line_requires_tracking_scan(line))
            )
            picking.xt_barcode_pending_destination_count = len(
                lines.filtered(lambda line: picking._line_requires_destination_scan(line))
            )
            picking.xt_barcode_pending_package_count = len(
                lines.filtered(lambda line: picking._line_requires_package_scan(line))
            )

    def _barcode_scan_allowed_states(self):
        return {"draft", "waiting", "confirmed", "assigned"}

    def _barcode_scan_supported_operation_codes(self):
        return ("incoming", "outgoing", "internal")

    def _barcode_scan_log_prefix(self):
        self.ensure_one()
        return f"[xtendoo_stock_barcode] [{self.name or self.id or 'new'}]"

    @api.model
    def action_xt_barcode_get_main_menu_data(self):
        user = self.env.user
        return {
            "groups": {
                "locations": user.has_group("stock.group_stock_multi_locations"),
                "package": user.has_group("stock.group_tracking_lot"),
                "tracking": user.has_group("stock.group_production_lot"),
            }
        }

    @api.model
    def _xt_barcode_main_menu_company_domain(self):
        return ["|", ("company_id", "=", False), ("company_id", "=", self.env.company.id)]

    @api.model
    def _xt_barcode_normalize(self, value):
        return re.sub(r"[^0-9A-Za-z]+", "", (value or "")).lower()

    @api.model
    def _xt_barcode_search_normalized_records(
        self,
        model_name,
        field_name,
        barcode,
        *,
        limit=2,
        extra_domain=None,
        company_domain=True,
    ):
        normalized = self._xt_barcode_normalize(barcode)
        if not normalized:
            return self.env[model_name]

        model = self.env[model_name]
        if field_name not in model._fields:
            return model

        sql = f'''
            SELECT id
              FROM "{model._table}"
             WHERE regexp_replace(lower(COALESCE("{field_name}"::text, '')), '[^[:alnum:]]+', '', 'g') = %s
        '''
        params = [normalized]
        if company_domain and "company_id" in model._fields:
            sql += ' AND ("company_id" IS NULL OR "company_id" = %s)'
            params.append(self.env.company.id)
        sql += ' ORDER BY id LIMIT %s'
        params.append(max(limit * 5, limit))

        self.env.cr.execute(sql, params)
        records = model.browse([row[0] for row in self.env.cr.fetchall()])
        if extra_domain:
            records = records.filtered_domain(extra_domain)
        return records[:limit]

    @api.model
    def _xt_barcode_get_picking_open_action(self, picking):
        return {
            "type": "ir.actions.act_window",
            "name": picking.display_name,
            "res_model": "stock.picking",
            "view_mode": "form",
            "views": [(self.env.ref("stock.view_picking_form").id, "form")],
            "res_id": picking.id,
            "target": "current",
        }

    @api.model
    def _xt_barcode_get_product_quants_action(self, product):
        return {
            "type": "ir.actions.act_window",
            "name": product.display_name,
            "res_model": "stock.quant",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("stock.view_stock_quant_tree").id, "list"),
                (self.env.ref("stock.view_stock_quant_form").id, "form"),
            ],
            "domain": [
                ("product_id", "=", product.id),
                ("location_id.usage", "=", "internal"),
            ],
            "context": {
                "search_default_internal_loc": True,
                "default_product_id": product.id,
            },
            "target": "current",
        }

    @api.model
    def _xt_barcode_get_lot_open_action(self, lot):
        return {
            "type": "ir.actions.act_window",
            "name": lot.display_name,
            "res_model": "stock.lot",
            "view_mode": "form",
            "views": [(self.env.ref("stock.view_production_lot_form").id, "form")],
            "res_id": lot.id,
            "target": "current",
        }

    @api.model
    def _xt_barcode_get_package_open_action(self, package):
        return {
            "type": "ir.actions.act_window",
            "name": package.display_name,
            "res_model": "stock.package",
            "view_mode": "form",
            "views": [(self.env.ref("stock.stock_package_view_form").id, "form")],
            "res_id": package.id,
            "target": "current",
            "context": {"active_id": package.id},
        }

    @api.model
    def _xt_barcode_create_new_picking_from_type(self, picking_type):
        location_dest, location_src = picking_type.warehouse_id._get_partner_locations()
        if picking_type.default_location_src_id:
            location_src = picking_type.default_location_src_id
        if picking_type.default_location_dest_id:
            location_dest = picking_type.default_location_dest_id
        return self.create(
            {
                "user_id": False,
                "picking_type_id": picking_type.id,
                "location_id": location_src.id,
                "location_dest_id": location_dest.id,
            }
        )

    @api.model
    def _xt_barcode_try_open_picking_from_main_menu(self, barcode):
        picking = self.search([("name", "=ilike", barcode)], limit=1)
        if not picking:
            picking = self._xt_barcode_search_normalized_records(
                "stock.picking",
                "name",
                barcode,
                limit=1,
                company_domain=True,
            )
        if picking:
            return {"action": self._xt_barcode_get_picking_open_action(picking)}
        return False

    @api.model
    def _xt_barcode_try_open_picking_type_from_main_menu(self, barcode):
        picking_type = self.env["stock.picking.type"].search(
            [
                ("barcode", "=ilike", barcode),
                ("code", "in", self._barcode_scan_supported_operation_codes()),
                *self._xt_barcode_main_menu_company_domain(),
            ],
            limit=1,
        )
        if not picking_type:
            picking_type = self._xt_barcode_search_normalized_records(
                "stock.picking.type",
                "barcode",
                barcode,
                limit=1,
                extra_domain=[("code", "in", self._barcode_scan_supported_operation_codes())],
                company_domain=True,
            )
        if picking_type:
            picking = self._xt_barcode_create_new_picking_from_type(picking_type)
            return {"action": self._xt_barcode_get_picking_open_action(picking)}
        return False

    @api.model
    def _xt_barcode_try_open_product_locations_from_main_menu(self, barcode):
        product = self.env["product.product"].search(
            [("barcode", "=ilike", barcode), ("type", "!=", "service")],
            limit=1,
        )
        if not product:
            product = self._xt_barcode_search_normalized_records(
                "product.product",
                "barcode",
                barcode,
                limit=1,
                extra_domain=[("type", "!=", "service")],
                company_domain=False,
            )
        if not product and self.env.user.has_group("uom.group_uom"):
            packaging = self.env["product.uom"].search([("barcode", "=ilike", barcode)], limit=1)
            if not packaging:
                packaging = self._xt_barcode_search_normalized_records(
                    "product.uom",
                    "barcode",
                    barcode,
                    limit=1,
                    company_domain=True,
                )
            product = packaging.product_id
        if product:
            return {"action": self._xt_barcode_get_product_quants_action(product)}
        return False

    @api.model
    def _xt_barcode_try_open_lot_from_main_menu(self, barcode):
        if not self.env.user.has_group("stock.group_production_lot"):
            return False
        lot = self.env["stock.lot"].search(
            [("name", "=ilike", barcode), *self._xt_barcode_main_menu_company_domain()],
            limit=1,
        )
        if not lot:
            lot = self._xt_barcode_search_normalized_records(
                "stock.lot",
                "name",
                barcode,
                limit=1,
                company_domain=True,
            )
        if lot:
            return {"action": self._xt_barcode_get_lot_open_action(lot)}
        return False

    @api.model
    def _xt_barcode_try_open_package_from_main_menu(self, barcode):
        if not self.env.user.has_group("stock.group_tracking_lot"):
            return False
        package = self.env["stock.package"].search([("name", "=ilike", barcode)], limit=1)
        if not package:
            package = self._xt_barcode_search_normalized_records(
                "stock.package",
                "name",
                barcode,
                limit=1,
                company_domain=True,
            )
        if package:
            return {"action": self._xt_barcode_get_package_open_action(package)}
        return False

    @api.model
    def _xt_barcode_try_create_internal_picking_from_location(self, barcode):
        if not self.env.user.has_group("stock.group_stock_multi_locations"):
            return False
        location = self.env["stock.location"].search(
            [
                ("barcode", "=ilike", barcode),
                ("usage", "=", "internal"),
                *self._xt_barcode_main_menu_company_domain(),
            ],
            limit=1,
        )
        if not location:
            location = self._xt_barcode_search_normalized_records(
                "stock.location",
                "barcode",
                barcode,
                limit=1,
                extra_domain=[("usage", "=", "internal")],
                company_domain=True,
            )
        if not location:
            return False
        picking_type = False
        if location.warehouse_id and location.warehouse_id.int_type_id:
            picking_type = location.warehouse_id.with_context(active_test=False).int_type_id
        if not picking_type:
            internal_types = self.env["stock.picking.type"].with_context(active_test=False).search(
                [
                    ("code", "=", "internal"),
                    *self._xt_barcode_main_menu_company_domain(),
                ]
            )
            if location.warehouse_id:
                internal_types = internal_types.filtered(lambda internal_type: internal_type.warehouse_id == location.warehouse_id) or internal_types
            picking_type = internal_types[:1]
        if not picking_type:
            return {
                "warning": {
                    "title": _("Xtendoo Barcode"),
                    "message": _("No existe un tipo de operación interna configurado para esta compañía."),
                }
            }
        destination = location
        while destination.location_id and destination.location_id.usage == "internal":
            destination = destination.location_id
        picking = self.create(
            {
                "user_id": False,
                "picking_type_id": picking_type.id,
                "location_id": location.id,
                "location_dest_id": destination.id,
            }
        )
        picking.action_confirm()
        return {"action": self._xt_barcode_get_picking_open_action(picking)}

    @api.model
    def action_xt_barcode_scan_from_main_menu(self, barcode):
        barcode = (barcode or "").strip()
        if not barcode:
            return {
                "warning": {
                    "title": _("Xtendoo Barcode"),
                    "message": _("Escanea o introduce un código de barras."),
                }
            }

        resolvers = [
            self._xt_barcode_try_open_picking_from_main_menu,
            self._xt_barcode_try_open_picking_type_from_main_menu,
            self._xt_barcode_try_create_internal_picking_from_location,
            self._xt_barcode_try_open_product_locations_from_main_menu,
            self._xt_barcode_try_open_lot_from_main_menu,
            self._xt_barcode_try_open_package_from_main_menu,
        ]
        for resolver in resolvers:
            result = resolver(barcode)
            if result:
                return result

        if self.env.user.has_group("stock.group_stock_multi_locations"):
            message = _(
                "No se ha encontrado ningún picking, ubicación, producto, lote o paquete para el código '%s'.",
                barcode,
            )
        else:
            message = _(
                "No se ha encontrado ningún picking, producto, lote o paquete para el código '%s'.",
                barcode,
            )
        return {"warning": {"title": _("Xtendoo Barcode"), "message": message}}

    def _set_barcode_feedback(self, barcode, message):
        self.ensure_one()
        self.xt_barcode_last_scan = barcode
        self.xt_barcode_last_message = message
        _logger.info("%s %s", self._barcode_scan_log_prefix(), message)

    def _barcode_scan_warning(self, barcode, message, *, raise_on_error=False):
        self.ensure_one()
        self._set_barcode_feedback(barcode, message)
        if raise_on_error:
            raise UserError(message)
        return {
            "warning": {
                "title": _("Escaneo de código de barras"),
                "message": message,
            }
        }

    def _barcode_scan_success(self, barcode, message):
        self.ensure_one()
        self._set_barcode_feedback(barcode, message)
        return False

    def _is_barcode_scan_allowed(self):
        self.ensure_one()
        return (
            self.id
            and self.state in self._barcode_scan_allowed_states()
            and self.picking_type_code in self._barcode_scan_supported_operation_codes()
        )

    def _get_barcode_company_domain(self):
        self.ensure_one()
        return [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.company_id.id),
        ]

    def _barcode_allow_extra_product(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_allow_extra_product

    def _barcode_source_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_scan_source_location or "no"

    def _barcode_destination_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_scan_dest_location or "no"

    def _barcode_tracking_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_scan_tracking_number or "optional"

    def _barcode_package_scan_policy(self):
        self.ensure_one()
        return self.picking_type_id.xt_barcode_restrict_put_in_pack or "no"

    def _barcode_destination_validation_required(self):
        self.ensure_one()
        policy = self._barcode_destination_scan_policy()
        return policy == "mandatory" or (
            policy == "optional" and self.picking_type_id.xt_barcode_validation_after_dest_location
        )

    def _barcode_package_validation_required(self):
        self.ensure_one()
        policy = self._barcode_package_scan_policy()
        return policy == "mandatory" or (
            policy == "optional" and self.picking_type_id.xt_barcode_validation_all_product_packed
        )

    def _find_product_from_barcode(self, barcode):
        self.ensure_one()
        products = self.env["product.product"].search(
            [("barcode", "=ilike", barcode), ("type", "!=", "service")],
            limit=2,
        )
        if not products:
            products = self._xt_barcode_search_normalized_records(
                "product.product",
                "barcode",
                barcode,
                limit=2,
                extra_domain=[("type", "!=", "service")],
                company_domain=False,
            )
        if products:
            return products
        packagings = self.env["product.uom"].search(
            [("barcode", "=ilike", barcode)],
            limit=2,
        )
        if not packagings:
            packagings = self._xt_barcode_search_normalized_records(
                "product.uom",
                "barcode",
                barcode,
                limit=2,
                company_domain=True,
            )
        return packagings.product_id.filtered(lambda product: product.type != "service")

    def _find_location_from_barcode(self, barcode):
        self.ensure_one()
        domain = [("barcode", "=ilike", barcode), ("usage", "!=", "view")]
        company_domain = self._get_barcode_company_domain()
        if self.company_id:
            domain.extend(company_domain)
        locations = self.env["stock.location"].search(domain, limit=2)
        if not locations:
            locations = self._xt_barcode_search_normalized_records(
                "stock.location",
                "barcode",
                barcode,
                limit=2,
                extra_domain=[("usage", "!=", "view")],
                company_domain=True,
            )
        return locations

    def _find_lot_from_barcode(self, product, barcode):
        self.ensure_one()
        domain = [("product_id", "=", product.id), ("name", "=ilike", barcode)]
        domain.extend(self._get_barcode_company_domain())
        lots = self.env["stock.lot"].search(domain, limit=2)
        if not lots:
            lots = self._xt_barcode_search_normalized_records(
                "stock.lot",
                "name",
                barcode,
                limit=2,
                extra_domain=[("product_id", "=", product.id)],
                company_domain=True,
            )
        return lots

    def _find_package_from_barcode(self, barcode):
        self.ensure_one()
        packages = self.env["stock.package"].search([("name", "=ilike", barcode)], limit=2)
        if not packages:
            packages = self._xt_barcode_search_normalized_records(
                "stock.package",
                "name",
                barcode,
                limit=2,
                company_domain=True,
            )
        return packages

    def _get_scan_source_location(self):
        self.ensure_one()
        return self.xt_barcode_source_location_id or self.location_id

    def _get_scan_destination_location(self):
        self.ensure_one()
        return self.xt_barcode_destination_location_id or self.location_dest_id

    def _get_current_barcode_line(self):
        self.ensure_one()
        line = self.xt_barcode_current_line_id
        if line and line.picking_id == self and line.state not in ("done", "cancel"):
            return line
        return self.env["stock.move.line"]

    def _get_relevant_barcode_lines(self):
        self.ensure_one()
        return self.move_line_ids.filtered(
            lambda line: line.state not in ("done", "cancel") and (line.quantity or line.picked)
        )

    def _line_requires_tracking_scan(self, line):
        self.ensure_one()
        return (
            line.picking_id == self
            and line.product_id.tracking != "none"
            and not line.xt_barcode_tracking_scanned
        )

    def _line_requires_destination_scan(self, line):
        self.ensure_one()
        return (
            line.picking_id == self
            and self._barcode_destination_validation_required()
            and not line.xt_barcode_destination_scanned
        )

    def _line_requires_package_scan(self, line):
        self.ensure_one()
        return (
            line.picking_id == self
            and self._barcode_package_validation_required()
            and not line.xt_barcode_package_scanned
        )

    def _line_followup_mode(self, line):
        self.ensure_one()
        if not line:
            return "product"
        if self._line_requires_tracking_scan(line):
            return "lot"
        if self._barcode_destination_scan_policy() == "mandatory" and not line.xt_barcode_destination_scanned:
            return "destination"
        if self._barcode_package_scan_policy() == "mandatory" and not line.xt_barcode_package_scanned:
            return "package"
        return "product"

    def _get_new_line_barcode_flags(self, product):
        self.ensure_one()
        return {
            "xt_barcode_source_scanned": self._barcode_source_scan_policy() != "mandatory"
            or bool(self.xt_barcode_source_location_id),
            "xt_barcode_destination_scanned": self._barcode_destination_scan_policy() == "no",
            "xt_barcode_tracking_scanned": product.tracking == "none",
            "xt_barcode_package_scanned": self._barcode_package_scan_policy() == "no",
        }

    def _get_pending_line_warning(self, line, barcode, *, raise_on_error=False):
        self.ensure_one()
        next_mode = self._line_followup_mode(line)
        if next_mode == "lot":
            return self._barcode_scan_warning(
                barcode,
                _(
                    "La línea actual de %s requiere completar antes el lote o la serie.",
                    line.product_id.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        if next_mode == "destination":
            return self._barcode_scan_warning(
                barcode,
                _(
                    "La línea actual de %s requiere confirmar antes la ubicación destino.",
                    line.product_id.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        if next_mode == "package":
            return self._barcode_scan_warning(
                barcode,
                _(
                    "La línea actual de %s requiere escanear antes el paquete de destino.",
                    line.product_id.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        return False

    def _get_candidate_move(self, product, location_id, location_dest_id):
        self.ensure_one()
        return self.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
            and move.product_id == product
            and move.location_id == location_id
            and move.location_dest_id == location_dest_id
        )[:1]

    def _get_candidate_move_anywhere(self, product):
        self.ensure_one()
        return self.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
            and move.product_id == product
        )[:1]

    def _get_candidate_line_for_untracked(self, product, location_id, location_dest_id):
        self.ensure_one()
        expected_package = self.xt_barcode_current_package_id
        current_line = self._get_current_barcode_line()
        if (
            current_line
            and current_line.product_id == product
            and current_line.location_id == location_id
            and current_line.location_dest_id == location_dest_id
            and not current_line.lot_id
            and not current_line.lot_name
            and current_line.result_package_id == expected_package
        ):
            return current_line
        return self.move_line_ids.filtered(
            lambda line: line.state not in ("done", "cancel")
            and line.product_id == product
            and line.location_id == location_id
            and line.location_dest_id == location_dest_id
            and not line.lot_id
            and not line.lot_name
            and line.result_package_id == expected_package
        )[:1]

    def _create_barcode_move(self, product, location_id, location_dest_id, quantity):
        self.ensure_one()
        move = self.env["stock.move"].create(
            {
                "picking_id": self.id,
                "picking_type_id": self.picking_type_id.id,
                "company_id": self.company_id.id,
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "product_uom_qty": quantity,
                "location_id": location_id.id,
                "location_dest_id": location_dest_id.id,
            }
        )
        if self.state != "draft":
            move._action_confirm()
        return move

    def _sync_move_demand_with_lines(self, move):
        self.ensure_one()
        total_done_qty = sum(move.move_line_ids.mapped("quantity"))
        if total_done_qty > move.product_uom_qty:
            move.product_uom_qty = total_done_qty

    def _create_barcode_move_line(self, move, product, location_id, location_dest_id, quantity, barcode_flags=None):
        self.ensure_one()
        values = {
            "picking_id": self.id,
            "move_id": move.id,
            "company_id": self.company_id.id,
            "product_id": product.id,
            "product_uom_id": product.uom_id.id,
            "location_id": location_id.id,
            "location_dest_id": location_dest_id.id,
            "quantity": quantity,
            "picked": bool(quantity),
        }
        if barcode_flags:
            values.update(barcode_flags)
        line = self.env["stock.move.line"].create(values)
        self._sync_move_demand_with_lines(move)
        return line

    def _increase_line_quantity(self, line, quantity, barcode_flags=None):
        self.ensure_one()
        values = {"quantity": line.quantity + quantity}
        if values["quantity"] > 0 and not line.picked:
            values["picked"] = True
        if barcode_flags:
            values.update(barcode_flags)
        line.write(values)
        self._sync_move_demand_with_lines(line.move_id)
        return line

    def _set_current_line(self, line):
        self.ensure_one()
        self.xt_barcode_current_line_id = line
        return line

    def _apply_current_package_to_line(self, line):
        self.ensure_one()
        package = self.xt_barcode_current_package_id
        if not package:
            return line
        if line.result_package_id != package:
            line.action_put_in_pack(package_id=package.id)
        line.xt_barcode_package_scanned = True
        return line

    def _scan_source_location(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        locations = self._find_location_from_barcode(barcode)
        if not locations:
            return self._barcode_scan_warning(
                barcode,
                _("No se ha encontrado ninguna ubicación con el código '%s'.", barcode),
                raise_on_error=raise_on_error,
            )
        if len(locations) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varias ubicaciones.", barcode),
                raise_on_error=raise_on_error,
            )
        location = locations[0]
        self.xt_barcode_source_location_id = location
        current_line = self._get_current_barcode_line()
        if current_line and current_line.state not in ("done", "cancel"):
            current_line.write(
                {
                    "location_id": location.id,
                    "xt_barcode_source_scanned": True,
                }
            )
        self.xt_barcode_mode = "product"
        return self._barcode_scan_success(
            barcode,
            _("Ubicación origen seleccionada: %s", location.display_name),
        )

    def _scan_destination_location(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        locations = self._find_location_from_barcode(barcode)
        if not locations:
            return self._barcode_scan_warning(
                barcode,
                _("No se ha encontrado ninguna ubicación con el código '%s'.", barcode),
                raise_on_error=raise_on_error,
            )
        if len(locations) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varias ubicaciones.", barcode),
                raise_on_error=raise_on_error,
            )
        location = locations[0]
        self.xt_barcode_destination_location_id = location
        current_line = self._get_current_barcode_line()
        if current_line and current_line.state not in ("done", "cancel"):
            current_line.write(
                {
                    "location_dest_id": location.id,
                    "xt_barcode_destination_scanned": True,
                }
            )
            self.xt_barcode_mode = self._line_followup_mode(current_line)
        else:
            self.xt_barcode_mode = "product"
        return self._barcode_scan_success(
            barcode,
            _("Ubicación destino seleccionada: %s", location.display_name),
        )

    def _scan_package(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        packages = self._find_package_from_barcode(barcode)
        if len(packages) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varios paquetes.", barcode),
                raise_on_error=raise_on_error,
            )
        package = packages[:1]
        if not package:
            package = self.env["stock.package"].create({"name": barcode})

        self.xt_barcode_current_package_id = package
        current_line = self._get_current_barcode_line()
        if current_line:
            self._apply_current_package_to_line(current_line)
            self.xt_barcode_mode = self._line_followup_mode(current_line)
            return self._barcode_scan_success(
                barcode,
                _(
                    "Línea actual añadida al paquete %s.",
                    package.display_name,
                ),
            )
        self.xt_barcode_mode = "product"
        return self._barcode_scan_success(
            barcode,
            _("Paquete activo seleccionado: %s", package.display_name),
        )

    def _scan_product(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        pending_line = self._get_current_barcode_line()
        if pending_line:
            pending_warning = self._get_pending_line_warning(
                pending_line,
                barcode,
                raise_on_error=raise_on_error,
            )
            if pending_warning:
                return pending_warning

        if self._barcode_source_scan_policy() == "mandatory" and not self.xt_barcode_source_location_id:
            return self._barcode_scan_warning(
                barcode,
                _("Debes escanear primero la ubicación origen antes de procesar productos."),
                raise_on_error=raise_on_error,
            )

        products = self._find_product_from_barcode(barcode)
        if not products:
            return self._barcode_scan_warning(
                barcode,
                _("No se ha encontrado ningún producto almacenable o consumible con el código '%s'.", barcode),
                raise_on_error=raise_on_error,
            )
        if len(products) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varios productos.", barcode),
                raise_on_error=raise_on_error,
            )
        product = products[0]
        source = self._get_scan_source_location()
        destination = self._get_scan_destination_location()
        if not source or not destination:
            return self._barcode_scan_warning(
                barcode,
                _("El picking debe tener ubicaciones origen y destino definidas antes de escanear productos."),
                raise_on_error=raise_on_error,
            )

        quantity = 1.0
        tracking = product.tracking
        line = self.env["stock.move.line"]
        barcode_flags = self._get_new_line_barcode_flags(product)

        exact_move = self._get_candidate_move(product, source, destination)
        existing_move = exact_move or self._get_candidate_move_anywhere(product)
        if not self._barcode_allow_extra_product() and not existing_move:
            return self._barcode_scan_warning(
                barcode,
                _(
                    "El producto %s no estaba previsto en esta operación y la configuración no permite añadir productos extra.",
                    product.display_name,
                ),
                raise_on_error=raise_on_error,
            )
        if existing_move and not exact_move and not self._barcode_allow_extra_product():
            source = existing_move.location_id
            destination = existing_move.location_dest_id

        if tracking == "serial":
            move = exact_move or existing_move or self._create_barcode_move(product, source, destination, quantity)
            line = self._create_barcode_move_line(
                move,
                product,
                source,
                destination,
                quantity,
                barcode_flags=barcode_flags,
            )
            self._set_current_line(line)
            self.xt_barcode_mode = self._line_followup_mode(line)
            return self._barcode_scan_success(
                barcode,
                _("Serie pendiente para %s.", product.display_name),
            )

        candidate_line = self._get_candidate_line_for_untracked(product, source, destination)
        if candidate_line:
            line = self._increase_line_quantity(candidate_line, quantity, barcode_flags=barcode_flags)
        else:
            move = exact_move or existing_move or self._create_barcode_move(
                product,
                source,
                destination,
                quantity,
            )
            line = self._create_barcode_move_line(
                move,
                product,
                source,
                destination,
                quantity,
                barcode_flags=barcode_flags,
            )

        if self.xt_barcode_current_package_id and self._barcode_package_scan_policy() != "mandatory":
            self._apply_current_package_to_line(line)

        self._set_current_line(line)
        if tracking == "lot":
            self.xt_barcode_mode = self._line_followup_mode(line)
            return self._barcode_scan_success(
                barcode,
                _("Lote pendiente para %s.", product.display_name),
            )
        self.xt_barcode_mode = self._line_followup_mode(line)
        return self._barcode_scan_success(
            barcode,
            _(
                "Producto %s actualizado. Cantidad actual en la línea: %s",
                product.display_name,
                line.quantity,
            ),
        )

    def _scan_lot_or_serial(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        line = self._get_current_barcode_line()
        if not line:
            return self._barcode_scan_warning(
                barcode,
                _("No hay ninguna línea activa. Escanea primero un producto."),
                raise_on_error=raise_on_error,
            )
        product = line.product_id
        if product.tracking == "none":
            return self._barcode_scan_warning(
                barcode,
                _("La línea actual no requiere lote ni serie."),
                raise_on_error=raise_on_error,
            )

        lots = self._find_lot_from_barcode(product, barcode)
        if len(lots) > 1:
            return self._barcode_scan_warning(
                barcode,
                _("El código '%s' coincide con varios lotes/series para el producto actual.", barcode),
                raise_on_error=raise_on_error,
            )

        if product.tracking == "serial" and line.quantity > 1:
            return self._barcode_scan_warning(
                barcode,
                _("Una línea con seguimiento por serie no puede tener cantidad mayor que 1."),
                raise_on_error=raise_on_error,
            )

        duplicate_serial_line = self.move_line_ids.filtered(
            lambda other: other.id != line.id
            and other.product_id == product
            and (
                (other.lot_id and lots and other.lot_id == lots[0])
                or (other.lot_name and other.lot_name == barcode)
            )
        )[:1]
        if product.tracking == "serial" and duplicate_serial_line:
            return self._barcode_scan_warning(
                barcode,
                _("La serie '%s' ya está usada en otra línea del picking.", barcode),
                raise_on_error=raise_on_error,
            )

        values = {"picked": True, "xt_barcode_tracking_scanned": True}
        if lots:
            values.update({"lot_id": lots[0].id, "lot_name": False})
            message = _(
                "Lote/serie %s asignado a %s.",
                lots[0].display_name,
                product.display_name,
            )
        elif self.use_create_lots:
            values.update({"lot_id": False, "lot_name": barcode})
            message = _(
                "Nuevo lote/serie %s asignado a %s.",
                barcode,
                product.display_name,
            )
        else:
            return self._barcode_scan_warning(
                barcode,
                _(
                    "No existe un lote/serie '%s' para %s y este tipo de operación no permite crear uno nuevo.",
                    barcode,
                    product.display_name,
                ),
                raise_on_error=raise_on_error,
            )

        line.write(values)
        if self.xt_barcode_current_package_id and self._barcode_package_scan_policy() != "mandatory":
            self._apply_current_package_to_line(line)
        self.xt_barcode_mode = self._line_followup_mode(line)
        return self._barcode_scan_success(barcode, message)

    def _get_barcode_validation_errors(self):
        self.ensure_one()
        errors = []
        lines = self._get_relevant_barcode_lines()
        if not self.picking_type_id.xt_barcode_validation_full and not lines:
            errors.append(
                _("Debes trabajar al menos una línea con barcode antes de validar esta operación.")
            )

        pending_tracking = lines.filtered(lambda line: self._line_requires_tracking_scan(line))
        if pending_tracking and self._barcode_tracking_scan_policy() == "mandatory":
            errors.append(
                _(
                    "Hay líneas con lote/serie pendiente: %s",
                    ", ".join(pending_tracking.mapped("product_id.display_name")),
                )
            )

        pending_destination = lines.filtered(lambda line: self._line_requires_destination_scan(line))
        if pending_destination:
            errors.append(
                _(
                    "Hay líneas con destino pendiente de confirmar: %s",
                    ", ".join(pending_destination.mapped("product_id.display_name")),
                )
            )

        pending_package = lines.filtered(lambda line: self._line_requires_package_scan(line))
        if pending_package:
            errors.append(
                _(
                    "Hay líneas pendientes de paquete: %s",
                    ", ".join(pending_package.mapped("product_id.display_name")),
                )
            )
        return errors

    def _apply_scanned_barcode(self, barcode, *, raise_on_error=False):
        self.ensure_one()
        barcode = (barcode or "").strip()
        if not barcode:
            return {"status": "ignored"}

        if not self.id:
            return self._barcode_scan_warning(
                barcode,
                _("Guarda el picking antes de empezar a escanear."),
                raise_on_error=raise_on_error,
            )

        if not self._is_barcode_scan_allowed():
            return self._barcode_scan_warning(
                barcode,
                _("El picking no está en un estado compatible con el escaneo clásico."),
                raise_on_error=raise_on_error,
            )

        mode = self.xt_barcode_mode or "product"
        if mode == "source":
            return self._scan_source_location(barcode, raise_on_error=raise_on_error)
        if mode == "destination":
            return self._scan_destination_location(barcode, raise_on_error=raise_on_error)
        if mode == "lot":
            return self._scan_lot_or_serial(barcode, raise_on_error=raise_on_error)
        if mode == "package":
            return self._scan_package(barcode, raise_on_error=raise_on_error)
        return self._scan_product(barcode, raise_on_error=raise_on_error)

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        return self._apply_scanned_barcode(barcode, raise_on_error=False)

    def action_scan_barcode(self, barcode):
        self.ensure_one()
        return self._apply_scanned_barcode(barcode, raise_on_error=True)

    def action_xt_barcode_set_mode_product(self):
        self.ensure_one()
        self.xt_barcode_mode = "product"

    def action_xt_barcode_set_mode_source(self):
        self.ensure_one()
        self.xt_barcode_mode = "source"

    def action_xt_barcode_set_mode_destination(self):
        self.ensure_one()
        self.xt_barcode_mode = "destination"

    def action_xt_barcode_set_mode_lot(self):
        self.ensure_one()
        self.xt_barcode_mode = "lot"

    def action_xt_barcode_set_mode_package(self):
        self.ensure_one()
        self.xt_barcode_mode = "package"

    def action_xt_barcode_validate(self):
        self.ensure_one()
        errors = self._get_barcode_validation_errors()
        if errors:
            raise UserError("\n".join(errors))
        return self.button_validate()

    def action_xt_barcode_reset_context(self):
        self.ensure_one()
        self.write(
            {
                "xt_barcode_mode": "product",
                "xt_barcode_current_line_id": False,
                "xt_barcode_current_package_id": False,
                "xt_barcode_source_location_id": False,
                "xt_barcode_destination_location_id": False,
                "xt_barcode_last_message": False,
            }
        )



