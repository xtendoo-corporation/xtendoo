# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools.float_utils import float_compare, float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_sale_order_confirm_and_delivery(self):
        """Confirmar los pedidos y validar todos sus albaranes pendientes."""
        self._confirm_and_deliver_orders()
        return True

    def action_sale_order_confirm_and_invoice(self):
        """Confirmar, entregar, facturar y publicar las facturas resultantes."""
        self._confirm_and_deliver_orders()
        invoices = self._create_and_post_invoices()
        return self.action_view_invoice(invoices=invoices)

    def action_sale_order_delivery(self):
        """Validar todos los albaranes pendientes de pedidos ya confirmados."""
        self._deliver_orders()
        return True

    def action_sale_order_delivery_and_invoiced(self):
        """Entregar pedidos confirmados, facturar y publicar sus facturas."""
        self._deliver_orders()
        invoices = self._create_and_post_invoices()
        return self.action_view_invoice(invoices=invoices)

    def _confirm_and_deliver_orders(self):
        for order in self:
            order._confirm_order_if_needed()
        self._deliver_orders()

    def _confirm_order_if_needed(self):
        self.ensure_one()
        if self.state in ("draft", "sent"):
            self.action_confirm()
        if self.state != "sale":
            raise UserError(
                _(
                    "Solo se pueden procesar presupuestos o pedidos de venta. "
                    "El pedido %(order)s está en estado %(state)s.",
                    order=self.display_name,
                    state=self.state,
                )
            )

    def _deliver_orders(self):
        for order in self:
            order._confirm_order_if_needed()
            order._validate_pending_pickings()

    def _validate_pending_pickings(self):
        self.ensure_one()
        while True:
            pending_pickings = self._get_pending_pickings()
            if not pending_pickings:
                break

            processed_states = {
                picking.id: picking.state for picking in pending_pickings
            }
            for picking in pending_pickings:
                self._validate_picking_with_order_quantities(picking)

            if self._get_pending_pickings() and all(
                picking.state == processed_states[picking.id]
                for picking in pending_pickings
            ):
                pending_names = ", ".join(self._get_pending_pickings().mapped("name"))
                raise UserError(
                    _(
                        "No se pudieron validar todas las entregas del pedido "
                        "%(order)s. Entregas pendientes: %(pickings)s.",
                        order=self.display_name,
                        pickings=pending_names,
                    )
                )

    def _get_pending_pickings(self):
        self.ensure_one()
        pending_pickings = self.picking_ids.filtered(
            lambda picking: picking.state not in ("done", "cancel")
        )
        return pending_pickings.sorted(
            lambda picking: (
                picking.scheduled_date or picking.create_date,
                picking.id,
            )
        )

    def _validate_picking_with_order_quantities(self, picking):
        if picking.state == "draft":
            picking.action_confirm()
        if picking.move_ids.filtered(lambda move: move.state not in ("done", "cancel")):
            picking.action_assign()

        for move in picking.move_ids.filtered(
            lambda move: move.state not in ("done", "cancel")
        ):
            self._set_move_quantity_to_order_demand(move)

        result = picking.with_context(
            skip_backorder=True,
            skip_immediate=True,
            skip_sms=True,
        ).button_validate()
        if picking.state not in ("done", "cancel"):
            raise UserError(
                _(
                    "No se pudo validar la entrega %(picking)s. "
                    "Resultado devuelto: %(result)s.",
                    picking=picking.display_name,
                    result=result,
                )
            )

    def _set_move_quantity_to_order_demand(self, move):
        demand = move.product_uom_qty
        if float_is_zero(demand, precision_rounding=move.product_uom.rounding):
            move.quantity = 0
            return

        if move.restrict_lot_id and move.product_id.tracking != "none":
            self._set_restricted_lot_move_quantity(move, demand)
            return

        move.quantity = demand

    def _set_restricted_lot_move_quantity(self, move, demand):
        demand_in_product_uom = move.product_uom._compute_quantity(
            demand,
            move.product_id.uom_id,
            round=False,
        )
        if move.product_id.tracking == "serial" and float_compare(
            demand_in_product_uom,
            1.0,
            precision_rounding=move.product_id.uom_id.rounding,
        ) != 0:
            raise UserError(
                _(
                    "El producto %(product)s se gestiona por números de serie. "
                    "La línea del pedido debe tener cantidad 1 para el "
                    "lote/serie %(lot)s.",
                    product=move.product_id.display_name,
                    lot=move.restrict_lot_id.display_name,
                )
            )

        move.move_line_ids.filtered(lambda line: line.state != "done").unlink()
        move.move_line_ids = [
            Command.create(
                {
                    **move._prepare_move_line_vals(quantity=0),
                    "lot_id": move.restrict_lot_id.id,
                    "quantity": demand,
                    "product_uom_id": move.product_uom.id,
                }
            )
        ]
        move.invalidate_recordset(["quantity"])

    def _create_and_post_invoices(self):
        invoices = self.env["account.move"]
        orders_to_invoice = self.filtered(
            lambda order: order.invoice_status != "invoiced"
        )
        if orders_to_invoice:
            invoices |= orders_to_invoice._create_invoices(final=True)
        invoices |= (self - orders_to_invoice).mapped("invoice_ids")

        draft_invoices = invoices.filtered(lambda invoice: invoice.state == "draft")
        if draft_invoices:
            draft_invoices.action_post()
        return invoices
