# -*- coding: utf-8 -*-

import re
from odoo import api, models
from odoo.tools import _

class StockPicking(models.Model):
    _inherit = "stock.picking"

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
    def _xt_barcode_get_picking_form_action(self, picking):
        return {
            "type": "ir.actions.act_window",
            "name": picking.display_name,
            "res_model": "stock.picking",
            "view_mode": "form",
            "views": [(self.env.ref("stock.view_picking_form").id, "form")],
            "res_id": picking.id,
            "target": "current",
            "context": {
                "active_model": "stock.picking",
                "active_id": picking.id,
                "active_ids": [picking.id],
            },
        }

    @api.model
    def _xt_barcode_get_picking_open_action(self, picking):
        return picking.action_xt_barcode_open_pda()

    def _xt_barcode_get_pda_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_stock_barcode_client_action",
            "name": _("Barcode %s", self.display_name),
            "target": "fullscreen",
            "params": {
                "model": "stock.picking",
                "picking_id": self.id,
            }
        }

    def action_xt_barcode_open_pda(self):
        self.ensure_one()
        if not self._is_barcode_scan_allowed():
            return self._xt_barcode_get_picking_form_action(self)
        return self._xt_barcode_get_pda_action()

    def action_xt_barcode_open_form(self):
        self.ensure_one()
        return self._xt_barcode_get_picking_form_action(self)

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
                    "title": _("Transferencias internas"),
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
                    "title": _("Transferencias internas"),
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
        return {"warning": {"title": _("Transferencias internas"), "message": message}}

    @api.model
    def action_xt_get_picking_list_data(self, domain):
        pickings = self.search_read(
            domain,
            ["id", "name", "origin", "location_id", "location_dest_id", "state", "scheduled_date", "picking_type_id", "partner_id"],
            order="scheduled_date desc, id desc"
        )
        for p in pickings:
            p["location_name"] = p["location_id"][1] if p["location_id"] else ""
            p["location_dest_name"] = p["location_dest_id"][1] if p["location_dest_id"] else ""
            p["picking_type_name"] = p["picking_type_id"][1] if p["picking_type_id"] else ""
            p["partner_name"] = p["partner_id"][1] if p["partner_id"] else ""
        return pickings
