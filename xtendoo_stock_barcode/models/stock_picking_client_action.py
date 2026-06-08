# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.tools import _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_xt_get_barcode_data(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "picking_type_code": self.picking_type_id.code,
            "company_id": self.company_id.id,
            "scheduled_date": self.scheduled_date,
            "lines": [
                {
                    "id": m.id,
                    "product_id": m.product_id.id,
                    "product_name": m.product_id.display_name,
                    "product_barcode": m.product_id.barcode,
                    "qty_done": m.xt_barcode_scanned_qty,
                    "qty_demand": m.product_uom_qty,
                    "location_id": m.location_id.id,
                    "location_name": m.location_id.display_name,
                    "location_dest_id": m.location_dest_id.id,
                    "location_dest_name": m.location_dest_id.display_name,
                }
                for m in self.move_ids
                if m.state not in ('cancel', 'done')
            ],
            "locations": {
                loc.id: {"id": loc.id, "name": loc.display_name, "barcode": loc.barcode}
                for loc in (self.move_ids.location_id | self.move_ids.location_dest_id)
            },
        }

    def action_xt_process_barcode_scan(self, barcode):
        self.ensure_one()
        try:
            res = self._apply_scanned_barcode(barcode, raise_on_error=True)

            # Comprobar si hay exceso
            excess = False
            for m in self.move_ids:
                if m.state not in ('cancel', 'done') and m.xt_barcode_scanned_qty > m.product_uom_qty:
                    excess = True
                    break

            return {"success": True, "message": "Código escaneado correctamente.", "excess": excess}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def action_xt_complete_line(self, move_id):
        self.ensure_one()
        move = self.env["stock.move"].browse(move_id)
        if move in self.move_ids and move.state not in ('cancel', 'done'):
            missing_qty = move.product_uom_qty - move.xt_barcode_scanned_qty
            if missing_qty <= 0:
                return {"success": True}

            for ml in move.move_line_ids:
                if missing_qty <= 0:
                    break
                line_missing = getattr(ml, "quantity_product_uom", 0) - ml.quantity
                if line_missing > 0:
                    qty_to_add = min(missing_qty, line_missing)
                    ml.write({
                        "quantity": ml.quantity + qty_to_add,
                        "xt_barcode_product_scanned": True,
                    })
                    missing_qty -= qty_to_add
                elif not ml.xt_barcode_product_scanned:
                    ml.write({"xt_barcode_product_scanned": True})

            if missing_qty > 0:
                if move.move_line_ids:
                    ml = move.move_line_ids[0]
                    ml.write({
                        "quantity": ml.quantity + missing_qty,
                        "xt_barcode_product_scanned": True,
                    })
                else:
                    self._create_barcode_move_line(
                        move,
                        move.product_id,
                        move.location_id,
                        move.location_dest_id,
                        missing_qty,
                        barcode_flags=self._get_new_line_barcode_flags(move.product_id)
                    )
            return {"success": True}
        return {"success": False, "error": "Movimiento no válido."}

    def action_xt_reset_line(self, move_id):
        self.ensure_one()
        move = self.env["stock.move"].browse(move_id)
        if move in self.move_ids and move.state not in ('cancel', 'done'):
            move.move_line_ids.filtered(lambda ml: ml.xt_barcode_product_scanned).write({
                'quantity': 0.0,
                'xt_barcode_product_scanned': False
            })
            return {"success": True}
        return {"success": False}

    def action_xt_adjust_qty(self, move_id, qty):
        self.ensure_one()
        move = self.env["stock.move"].browse(move_id)
        if move in self.move_ids and move.state not in ('cancel', 'done'):
            if qty > 0:
                try:
                    self._apply_scanned_barcode(move.product_id.barcode, raise_on_error=True)
                    return {"success": True}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            else:
                # Restar cantidad
                ml = move.move_line_ids.filtered(lambda l: l.xt_barcode_product_scanned and l.quantity >= abs(qty))[:1]
                if ml:
                    ml.write({'quantity': ml.quantity + qty})
                    if ml.quantity == 0:
                        ml.write({'xt_barcode_product_scanned': False})
                return {"success": True}
        return {"success": False}

    @api.model
    def action_xt_get_aggregated_barcode_data(self, location_id):
        # Buscamos todos los pickings que tengan esa ubicación como destino (Recepciones) or origen (Entregas/Internas)
        # y que no estén finalizados ni cancelados.
        pickings = self.search([
            '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id),
            ('state', 'not in', ('cancel', 'done'))
        ])

        lines = []
        # Agrupamos los movimientos por producto
        moves = pickings.mapped('move_ids').filtered(lambda m: m.state not in ('cancel', 'done'))

        # Para simplificar la interfaz, podemos agrupar por producto y mostrar el sumatorio
        product_data = {}
        for m in moves:
            p_id = m.product_id.id
            if p_id not in product_data:
                product_data[p_id] = {
                    "product_id": p_id,
                    "product_name": m.product_id.display_name,
                    "product_barcode": m.product_id.barcode,
                    "qty_done": 0,
                    "qty_demand": 0,
                    "location_id": m.location_id.id,
                    "location_name": m.location_id.display_name,
                    "location_dest_id": m.location_dest_id.id,
                    "location_dest_name": m.location_dest_id.display_name,
                    "move_ids": [],
                }
            product_data[p_id]["qty_done"] += m.xt_barcode_scanned_qty
            product_data[p_id]["qty_demand"] += m.product_uom_qty
            product_data[p_id]["move_ids"].append(m.id)

        return {
            "id": False,
            "name": _("Transferencias Internas"),
            "state": 'assigned',
            "picking_type_code": 'internal',
            "lines": list(product_data.values()),
        }

    @api.model
    def action_xt_process_aggregated_barcode_scan(self, location_id, barcode):
        # Buscamos los pickings que tengan esa ubicación como destino u origen
        pickings = self.search([
            '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id),
            ('state', 'not in', ('cancel', 'done'))
        ])

        # Buscamos el producto por barcode
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if not product:
            return {"success": False, "error": _("Producto no encontrado.")}

        # Buscamos movimientos de este producto en los pickings
        moves = pickings.mapped('move_ids').filtered(lambda m: m.product_id == product and m.state not in ('cancel', 'done'))
        if not moves:
            return {"success": False, "error": _("El producto no está en ninguna transferencia pendiente.")}

        # Intentamos aplicar el escaneo al primer movimiento que le falte cantidad, o al primero si todos están llenos
        target_move = moves.filtered(lambda m: m.xt_barcode_scanned_qty < m.product_uom_qty)[:1] or moves[0]

        try:
            target_move.picking_id._apply_scanned_barcode(barcode, raise_on_error=True)
            return {"success": True, "message": _("Producto %s escaneado correctamente.") % product.display_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @api.model
    def action_xt_complete_aggregated_line(self, move_ids):
        moves = self.env['stock.move'].browse(move_ids)
        for move in moves:
            if move.state not in ('cancel', 'done'):
                move.picking_id.action_xt_complete_line(move.id)
        return {"success": True}

    @api.model
    def action_xt_reset_aggregated_line(self, move_ids):
        moves = self.env['stock.move'].browse(move_ids)
        for move in moves:
            if move.state not in ('cancel', 'done'):
                move.move_line_ids.filtered(lambda ml: ml.xt_barcode_product_scanned).write({
                    'quantity': 0.0,
                    'xt_barcode_product_scanned': False
                })
        return {"success": True}

    @api.model
    def action_xt_add_aggregated_qty(self, move_ids, qty):
        # Buscamos el producto implicado (todos los moves deben ser del mismo producto)
        moves = self.env['stock.move'].browse(move_ids)
        if not moves:
            return {"success": False}

        product = moves[0].product_id
        if qty > 0:
            # Reutilizamos la lógica de escaneo para añadir cantidad al primer movimiento disponible
            target_move = moves.filtered(lambda m: m.xt_barcode_scanned_qty < m.product_uom_qty)[:1] or moves[0]
            try:
                target_move.picking_id._apply_scanned_barcode(product.barcode, raise_on_error=True)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            # Para restar, buscamos movimientos que tengan cantidad escaneada
            source_move = moves.filtered(lambda m: m.xt_barcode_scanned_qty > 0).sorted('id', reverse=True)[:1]
            if not source_move:
                return {"success": True} # Nada que restar

            # Restamos de la primera move line escaneada que encontremos
            ml = source_move.move_line_ids.filtered(lambda l: l.xt_barcode_product_scanned and l.quantity >= abs(qty))[:1]
            if ml:
                ml.write({'quantity': ml.quantity + qty})
                if ml.quantity == 0:
                    ml.write({'xt_barcode_product_scanned': False})
            return {"success": True}

    @api.model
    def action_xt_validate_aggregated_pickings(self, location_id):
        pickings = self.search([
            '|', ('location_id', '=', location_id), ('location_dest_id', '=', location_id),
            ('state', 'not in', ('cancel', 'done'))
        ])

        # Procesamos solo pickings que tengan algo escaneado
        pickings_to_process = pickings.filtered(lambda p: any(m.xt_barcode_scanned_qty > 0 for m in p.move_ids))

        if not pickings_to_process:
            return {"success": False, "error": _("No hay nada escaneado para validar.")}

        for picking in pickings_to_process:
            try:
                if picking._check_backorder():
                    # Automatizamos la creación del backorder si es necesario
                    res = picking.button_validate()
                    if isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
                        wizard = self.env['stock.backorder.confirmation'].with_context(res['context']).create({})
                        wizard.process()
                else:
                    # Validación directa si está completo
                    picking.button_validate()
            except Exception as e:
                return {"success": False, "error": _("Error al validar %s: %s") % (picking.name, str(e))}

        return {
            "success": True,
            "message": _("Todos los movimientos con cantidades han sido validados directamente (con entregas parciales donde aplicaba)."),
            "finished": True
        }
