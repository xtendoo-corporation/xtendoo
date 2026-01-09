from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"


    def action_validate_picking_and_invoice(self):
        for order in self:
            _logger.info("=== Iniciando proceso para orden de venta %s ===", order.name)
            _logger.info("Estado inicial de la orden: %s", order.state)
            _logger.info("Total de albaranes: %s", len(order.picking_ids))
            if order.picking_ids:
                for picking in order.picking_ids:
                    _logger.info("- Albarán %s, estado: %s", picking.name, picking.state)

            if order.state == 'draft':
                _logger.info("Confirmando orden de venta %s (estado: draft)", order.name)
                order.action_confirm()
                _logger.info("Orden de venta %s confirmada exitosamente", order.name)
                _logger.info("Nuevo estado de la orden: %s", order.state)
                _logger.info("Albaranes después de confirmar: %s", len(order.picking_ids))
                for picking in order.picking_ids:
                    _logger.info("- Albarán %s, estado: %s", picking.name, picking.state)

            _logger.info("Asignando albaranes para orden %s. Total albaranes: %s",
                        order.name, len(order.picking_ids))
            _logger.info("Estado de la orden antes de asignar: %s", order.state)
            for picking in order.picking_ids:
                _logger.info("- Albarán %s, estado antes de asignar: %s", picking.name, picking.state)

            order.picking_ids.action_assign()

            _logger.info("Albaranes asignados para orden %s", order.name)
            _logger.info("Estado de la orden después de asignar: %s", order.state)
            for picking in order.picking_ids:
                _logger.info("- Albarán %s, estado después de asignar: %s", picking.name, picking.state)

            _logger.info("Validando albaranes para orden %s", order.name)
            for picking in order.picking_ids:
                _logger.info("- Albarán %s, estado antes de validar: %s", picking.name, picking.state)

                # Forzar las cantidades realizadas para cada línea de movimiento
                for move in picking.move_ids:
                    _logger.info("  * Movimiento producto %s: demanda=%s",
                                move.product_id.name, move.product_uom_qty)

                    # Revisar las líneas de movimiento (move_line_ids)
                    if not move.move_line_ids:
                        _logger.info("    - No hay líneas de movimiento, creando una automáticamente")
                    else:
                        total_qty = sum(ml.quantity for ml in move.move_line_ids)
                        _logger.info("    - Total líneas de movimiento: %s, cantidad total: %s",
                                    len(move.move_line_ids), total_qty)
                        for move_line in move.move_line_ids:
                            _logger.info("    - Línea: cantidad actual=%s", move_line.quantity)
                            if move_line.quantity == 0:
                                # Establecer la cantidad realizada igual a la demanda del movimiento
                                move_line.quantity = move.product_uom_qty
                                _logger.info("    - Estableciendo cantidad realizada a: %s", move_line.quantity)

            # Validar los albaranes
            for picking in order.picking_ids:
                if picking.state not in ('done', 'cancel'):
                    _logger.info("Validando albarán %s (estado inicial: %s)", picking.name, picking.state)
                    result = picking.button_validate()
                    _logger.info("Resultado de button_validate: %s", result)

                    # Si devuelve un wizard, procesarlo automáticamente
                    if isinstance(result, dict):
                        res_model = result.get('res_model')
                        res_id = result.get('res_id')
                        _logger.info("Wizard detectado: modelo=%s, id=%s", res_model, res_id)

                        if res_model == 'stock.immediate.transfer':
                            _logger.info("Procesando wizard de transferencia inmediata...")
                            wizard = self.env['stock.immediate.transfer'].browse(res_id)
                            wizard.process()
                            _logger.info("Wizard de transferencia inmediata procesado correctamente")

                        elif res_model == 'confirm.stock.sms':
                            # Este wizard es solo para confirmar el envío de SMS
                            # Podemos ignorarlo y forzar la validación del picking directamente
                            _logger.info("Wizard de SMS detectado, omitiendo y validando directamente...")
                            # El picking ya tiene las cantidades establecidas, forzar su estado a done
                            picking._action_done()
                            _logger.info("Picking validado directamente mediante _action_done()")

                        else:
                            # Para cualquier otro wizard, intentar métodos comunes
                            _logger.info("Procesando wizard %s con método genérico...", res_model)
                            try:
                                wizard = self.env[res_model].browse(res_id)
                                processed = False

                                # Intentar diferentes métodos comunes en orden de prioridad
                                for method_name in ['action_confirm', 'process', 'action_validate', 'button_validate']:
                                    if hasattr(wizard, method_name):
                                        _logger.info("Llamando a método %s del wizard %s", method_name, res_model)
                                        method = getattr(wizard, method_name)
                                        method()
                                        _logger.info("Wizard %s procesado correctamente con método %s", res_model, method_name)
                                        processed = True
                                        break

                                if not processed:
                                    _logger.warning("No se encontró un método válido para el wizard %s. Métodos disponibles: %s",
                                                  res_model, [m for m in dir(wizard) if not m.startswith('_') and callable(getattr(wizard, m))])
                            except Exception as e:
                                _logger.error("Error al procesar wizard %s: %s", res_model, str(e), exc_info=True)

                    # Verificar estado después de procesar wizard
                    picking.invalidate_recordset()
                    _logger.info("Estado del albarán después de procesar wizard: %s", picking.state)

                    # Si sigue sin estar done, intentar validar de nuevo
                    if picking.state not in ('done', 'cancel'):
                        _logger.info("El albarán aún no está validado, intentando button_validate de nuevo...")
                        result2 = picking.button_validate()
                        _logger.info("Segundo resultado de button_validate: %s", result2)

                        # Si devuelve otro wizard, procesarlo también
                        if isinstance(result2, dict):
                            res_model2 = result2.get('res_model')
                            res_id2 = result2.get('res_id')
                            _logger.info("Segundo wizard detectado: %s", res_model2)
                            if res_model2 == 'stock.backorder.confirmation':
                                _logger.info("Wizard de backorder detectado, procesando sin crear backorder...")
                                wizard2 = self.env['stock.backorder.confirmation'].browse(res_id2)
                                wizard2.process_cancel_backorder()
                                _logger.info("Wizard de backorder procesado correctamente")

            _logger.info("Albaranes validados para orden %s", order.name)
            _logger.info("Estado de la orden después de validar albaranes: %s", order.state)
            for picking in order.picking_ids:
                _logger.info("- Albarán %s, estado después de validar: %s", picking.name, picking.state)

            _logger.info("Creando factura para orden %s", order.name)
            _logger.info("Estado de la orden antes de crear factura: %s", order.state)

            invoice = order._create_invoices()

            if not invoice:
                _logger.warning("No se pudo crear factura para orden %s", order.name)
                _logger.warning("Estado de la orden: %s", order.state)
                continue

            _logger.info("Factura %s creada para orden %s", invoice.name, order.name)
            _logger.info("Estado de la factura recién creada: %s", invoice.state)
            _logger.info("Estado de la orden después de crear factura: %s", order.state)

            _logger.info("Publicando factura %s", invoice.name)
            _logger.info("Estado de la factura antes de publicar: %s", invoice.state)

            invoice.action_post()

            _logger.info("Factura %s publicada exitosamente", invoice.name)
            _logger.info("Estado de la factura después de publicar: %s", invoice.state)
            _logger.info("Estado final de la orden: %s", order.state)

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
