# Copyright (C) 2017 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64

from odoo import Command, _, api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _prepare_from_pos(self, order_data):
        session = self.env["pos.session"].browse(order_data["pos_session_id"])
        order_lines = [
            Command.create(self.env["sale.order.line"]._prepare_from_pos(seq, line[2]))
            for seq, line in enumerate(order_data["lines"], start=1)
        ]
        return {
            "partner_id": order_data["partner_id"],
            "origin": _("Point of Sale %s") % session.name,
            "client_order_ref": order_data["name"],
            "user_id": order_data["user_id"],
            "pricelist_id": order_data["pricelist_id"],
            "fiscal_position_id": order_data["fiscal_position_id"],
            "order_line": order_lines,
        }

    @api.model
    def create_order_from_pos(self, order_data, action):
        # Crear la orden de venta en borrador
        order_vals = self._prepare_from_pos(order_data)
        sale_order = self.with_context(
            pos_order_lines_data=[x[2] for x in order_data.get("lines", [])]
        ).create(order_vals)


        # Confirmar la orden de venta
        sale_order.action_confirm()

        # Marcar todos los movimientos como entregados
        for move in sale_order.mapped("picking_ids.move_ids_without_package"):
            move.quantity = move.product_uom_qty

        # Validar el picking
        pickings = sale_order.mapped("picking_ids")
        pickings.button_validate()

        # Devolver el ID del picking
        return {
            'picking_id': pickings.ids[0] if pickings else None,
        }
