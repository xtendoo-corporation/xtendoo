from odoo import models, api
from odoo.exceptions import UserError
from datetime import datetime

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_confirm_receive_invoice(self):
        """
        Confirma el pedido, valida el picking y crea la factura con la fecha del pedido.
        Compatible con Odoo 19.0 (usa move_ids y move_line_ids con qty_done).
        """
        for order in self:
            if order.state == 'draft':
                order.button_confirm()
            pickings = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            for picking in pickings:
                for move in picking.move_ids:
                    # Si no hay líneas de movimiento, crearlas
                    if not move.move_line_ids:
                        move.move_line_ids.create({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'quantity': move.product_uom_qty,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'picking_id': picking.id,
                            'company_id': move.company_id.id,
                        })
                    else:
                        for move_line in move.move_line_ids:
                            move_line.quantity = move.product_uom_qty
                picking.button_validate()
            # Crear factura
            invoice_wizard = self.env['purchase.order'].browse(order.id).action_create_invoice()
            # Ajustar fecha de factura
            invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('draft', 'posted'))
            for invoice in invoices:
                invoice.invoice_date = order.date_order.date() if order.date_order else datetime.today().date()
        return True
# Fin de la corrección: ahora se usa qty_done en move_line_ids para Odoo 19
