from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Estos dos métodos se han añadido para poder confirmar y entregar un pedido en un solo clic
    # y para confirmar y facturar un pedido en un solo clic.
    # Pero la entrega y la factura hay que confirmarlas manualmente.
    def action_confirm_and_deliver(self):
        print("*" * 80, "print 1")
        self.action_confirm()
        print("*" * 80 , "despues action_confirm")
        for order in self:
            print("*" * 80, "for order in self")
            if order.state in ['sale', 'draft'] and order.picking_ids:
                print("*" * 80 , "order.state in ['sale', 'draft']")
                for picking in order.picking_ids:
                    print("*" * 80, "picking in order.picking_ids")
                    picking.action_assign()
                    # if picking.state == 'assigned':
                    if picking.state in ['assigned', 'confirmed']:
                        print("*" * 80, "picking.state in ['assigned', 'confirmed']:")
                        if not picking.move_line_ids:
                            print("No move lines for this picking")
                        for move_line in picking.move_line_ids:
                            print("*"*80)
                            print(move_line.product_uom_qty, "cantidad")
                            print(move_line.quantity_done, "cantidad hecha")
                            move_line.quantity_done = move_line.product_uom_qty
                        picking.button_validate()

    def action_confirm_and_invoice(self):
        self.action_confirm_and_deliver()
        for order in self:
            order._create_invoices()
