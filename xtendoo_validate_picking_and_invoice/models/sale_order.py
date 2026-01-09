from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"


    def action_validate_picking_and_invoice(self):
        for order in self:
            _logger.info("=== Iniciando proceso para orden de venta %s ===", order.name)

            if order.state == 'draft':
                _logger.info("Confirmando orden de venta %s (estado: draft)", order.name)
                order.action_confirm()
                _logger.info("Orden de venta %s confirmada exitosamente", order.name)

            _logger.info("Asignando albaranes para orden %s. Total albaranes: %s",
                        order.name, len(order.picking_ids))
            order.picking_ids.action_assign()
            _logger.info("Albaranes asignados para orden %s", order.name)

            _logger.info("Validando albaranes para orden %s", order.name)
            order.picking_ids.button_validate()
            _logger.info("Albaranes validados para orden %s", order.name)

            _logger.info("Creando factura para orden %s", order.name)
            invoice = order._create_invoices()
            if not invoice:
                _logger.warning("No se pudo crear factura para orden %s", order.name)
                continue

            _logger.info("Factura %s creada para orden %s", invoice.name, order.name)

            _logger.info("Publicando factura %s", invoice.name)
            invoice.action_post()
            _logger.info("Factura %s publicada exitosamente", invoice.name)

            _logger.info("=== Proceso completado para orden %s. Abriendo factura %s ===",
                        order.name, invoice.name)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Customer Invoice',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
                'target': 'current',
            }
