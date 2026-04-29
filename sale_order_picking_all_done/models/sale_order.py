# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_sale_order_confirm_and_delivery(self):
        # Solo confirmar si el pedido está en estado borrador o enviado
        if self.state in ("draft", "sent"):
            self.action_confirm()
        for picking in self.picking_ids:
            for line in picking.move_ids_without_package.filtered(
                lambda m: m.state not in ["done", "cancel"]
            ):
                line.quantity = line.product_uom_qty
            picking.with_context(skip_overprocessed_check=True).button_validate()
            print("*"*50)
            print("Picking validado")
            print("*"*50)

    def action_sale_order_confirm_and_invoice(self):
        """
        Confirma el pedido, valida la entrega y crea la factura usando el método estándar de ventas (action_create_invoice), forzando cantidades y políticas si es necesario.
        Restaura los valores originales tras facturar y muestra logs de los cambios.
        """
        import logging
        logger = logging.getLogger(__name__)
        # Solo confirmar si el pedido está en estado borrador o enviado
        if self.state in ("draft", "sent"):
            self.action_confirm()
        self.action_sale_order_confirm_and_delivery()
        # Verificar que todos los pickings estén validados antes de facturar
        pickings_pendientes = self.picking_ids.filtered(lambda p: p.state not in ["done", "cancel"])
        if pickings_pendientes:
            raise UserError(_("No se puede facturar porque hay entregas pendientes de validar."))
        # Guardar valores originales
        original_invoice_policy = {}
        original_qty_delivered = {}
        original_qty_to_invoice = {}
        for line in self.order_line:
            if line.product_id and hasattr(line.product_id, 'invoice_policy'):
                original_invoice_policy[line.id] = line.product_id.invoice_policy
            original_qty_delivered[line.id] = line.qty_delivered
            original_qty_to_invoice[line.id] = getattr(line, 'qty_to_invoice', None)
        # Forzar política y cantidades
        for line in self.order_line:
            if line.product_id and hasattr(line.product_id, 'invoice_policy'):
                if line.product_id.type in ('product', 'consu'):
                    line.product_id.invoice_policy = 'order'
                elif line.product_id.type == 'service':
                    line.product_id.invoice_policy = 'prepaid'
                logger.info(f"Línea {line.id}: política cambiada a {line.product_id.invoice_policy}")
            line.qty_delivered = line.product_uom_qty
            # Forzar qty_to_invoice si existe
            if hasattr(line, 'qty_to_invoice'):
                line.qty_to_invoice = line.product_uom_qty
                logger.info(f"Línea {line.id}: qty_to_invoice forzada a {line.qty_to_invoice}")
            logger.info(f"Línea {line.id}: qty_delivered forzada a {line.qty_delivered}")
        # Recalcular el estado de facturación
        self._compute_invoice_status()
        lines_to_invoice = self.order_line.filtered(lambda l: l.invoice_status == 'to invoice')
        if not lines_to_invoice:
            # Restaurar valores originales
            for line in self.order_line:
                if line.product_id and hasattr(line.product_id, 'invoice_policy') and line.id in original_invoice_policy:
                    line.product_id.invoice_policy = original_invoice_policy[line.id]
                if line.id in original_qty_delivered:
                    line.qty_delivered = original_qty_delivered[line.id]
                if line.id in original_qty_to_invoice and hasattr(line, 'qty_to_invoice'):
                    line.qty_to_invoice = original_qty_to_invoice[line.id]
            logger.error("No se pudo forzar la facturación. Se restauraron los valores originales.")
            raise UserError(_(
                "No se pudo forzar la facturación.\n\n"
                "Revise la configuración de los productos y vuelva a intentarlo."
            ))
        # Usar el método estándar de ventas para crear la factura
        self.sudo().action_create_invoice()
        # Restaurar valores originales tras facturar
        for line in self.order_line:
            if line.product_id and hasattr(line.product_id, 'invoice_policy') and line.id in original_invoice_policy:
                line.product_id.invoice_policy = original_invoice_policy[line.id]
            if line.id in original_qty_delivered:
                line.qty_delivered = original_qty_delivered[line.id]
            if line.id in original_qty_to_invoice and hasattr(line, 'qty_to_invoice'):
                line.qty_to_invoice = original_qty_to_invoice[line.id]
            logger.info(f"Línea {line.id}: política, qty_delivered y qty_to_invoice restauradas")
        return True

    # Pedido confirmado( ya es un pedido de ventas)

    def action_sale_order_delivery(self):
        for picking in self.picking_ids:
            if picking.state != "done":
                for line in picking.move_ids_without_package:
                    line.quantity = line.product_uom_qty
                picking.button_validate()

    def action_sale_order_delivery_and_invoiced(self):

        self = self.with_context({"is_sale": True,})
        self.action_sale_order_delivery()
        payment = self.env["sale.advance.payment.inv"].create({})
        payment.with_context(active_ids=self.ids).create_invoices()
