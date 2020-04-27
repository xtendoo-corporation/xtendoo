# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
from odoo import api, _, fields, models
from odoo.tools.float_utils import float_compare
from odoo.exceptions import ValidationError
from odoo.fields import first
from odoo.addons import decimal_precision as dp
from datetime import datetime


class WizStockBarcodesReadInternalTransfer(models.TransientModel):
    _name = 'wiz.stock.barcodes.read.internal.transfer'
    _inherit = 'wiz.stock.barcodes.read'
    _description = 'Wizard to read barcode on internal transfer'

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
        readonly=True,
    )
    picking_product_qty = fields.Float(
        string='Picking quantities',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
    )

    def name_get(self):
        return [
            (rec.id, '{} - {} - {}'.format(
                _('Barcode reader'),
                rec.picking_id.name,
                self.env.user.name)) for rec in self]

    def _prepare_internal_transfer_move(self):
        return {
            'picking_id': self.picking_id.id,
            'product_id': self.product_id.id,
            'name': self.product_id.name,
            'product_uom': self.product_id.uom_id.id,
            'product_uom_qty': 1.0,
            'location_id': self.picking_id.location_id.id,
            'location_dest_id': self.picking_id.location_dest_id.id,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_expected': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'procure_method': 'make_to_stock',
        }

    def _prepare_internal_transfer_move_domain(self):
        return [
            ('picking_id', '=', self.picking_id.id),
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.picking_id.location_id.id),
            ('location_dest_id', '=', self.picking_id.location_dest_id.id),
        ]

    def _prepare_internal_transfer_move_line(self, move):
        return {
            'move_id': move.id,
            'lot_id': self.lot_id.id,
            'qty_done': move.product_uom_qty,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        }

    def _prepare_internal_transfer_move_line_domain(self, move):
        return [
            ('move_id', '=', self.picking_id.id),
            ('lot_id', '=', self.lot_id.id),
        ]

    def _add_internal_transfer_move(self):

        print("_prepare_internal_transfer_move_domain*****************", self._prepare_internal_transfer_move_domain())

        StockMove = self.env['stock.move']
        StockMoveLine = self.env['stock.move.line']

        move = StockMove.search(
            self._prepare_internal_transfer_move_domain(), limit=1
        )
        if move:
            print("move found *********************", move)
            line = move.mapped('move_line_ids').filtered(
                lambda m: m.lot_id == self.lot_id
            )
            if line:
                line.write({
                    'product_qty': line.product_uom_qty + 1.0,
                })
                print("line found *********************", line)
                return

        move = StockMove.create(self._prepare_internal_transfer_move())
        StockMoveLine.create(
            self._prepare_internal_transfer_move_line(move)
        )

        #StockInventoryLine = self.env['stock.inventory.line']
        #line = StockInventoryLine.search(
        #    self._prepare_internal_transfer_line_domain(), limit=1)
        #if line:
        #    line.write({
        #        'product_qty': line.product_qty + self.product_qty,
        #    })
        #else:
        #    line = StockInventoryLine.create(self._prepare_inventory_line())
        #self.inventory_product_qty = line.product_qty

    def action_done(self):
        result = super().action_done()
        if result:
            self._add_internal_transfer_move()
        return result

    def action_manual_entry(self):
        result = super().action_manual_entry()
        if result:
            self.action_done()
        return result

    def _prepare_move_line_values(self, candidate_move, available_qty):
        """When we've got an out picking, the logical workflow is that
           the scanned location is the location we're getting the stock
           from"""
        out_move = candidate_move.picking_code == 'outgoing'
        location_id = (
            self.location_id if out_move else self.picking_id.location_id)
        location_dest_id = (
            self.picking_id.location_dest_id if out_move else self.location_id)
        return {
            'picking_id': self.picking_id.id,
            'move_id': candidate_move.id,
            'qty_done': available_qty,
            'product_uom_id': self.product_id.uom_po_id.id,
            'product_id': self.product_id.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'lot_id': self.lot_id.id,
            'lot_name': self.lot_id.name,
        }

    def _prepare_stock_moves_domain(self):
        domain = [
            ('product_id', '=', self.product_id.id),
            ('picking_id.picking_type_id.code', '=', self.picking_type_code),
        ]
        if self.picking_id:
            domain.append(('picking_id', '=', self.picking_id.id))
        return domain

    def _process_stock_move_line(self):
        """
        Search assigned or confirmed stock moves from a picking operation type
        or a picking. If there is more than one picking with demand from
        scanned product the interface allow to select what picking to work.
        If only there is one picking the scan data is assigned to it.
        """
        StockMove = self.env['stock.move']
        StockMoveLine = self.env['stock.move.line']
        moves_todo = StockMove.search(self._prepare_stock_moves_domain())
        lines = moves_todo.mapped('move_line_ids').filtered(
            lambda l: (l.picking_id == self.picking_id and
                       l.product_id == self.product_id and
                       l.lot_id == self.lot_id))
        available_qty = self.product_qty
        move_lines_dic = {}
        for line in lines:
            if line.product_uom_qty:
                assigned_qty = min(
                    max(line.product_uom_qty - line.qty_done, 0.0),
                    available_qty)
            else:
                assigned_qty = available_qty
            line.write({'qty_done': line.qty_done + assigned_qty})
            available_qty -= assigned_qty
            if assigned_qty:
                move_lines_dic[line.id] = assigned_qty
            if float_compare(
                    available_qty, 0.0,
                    precision_rounding=line.product_id.uom_id.rounding) < 1:
                break
        if float_compare(
                available_qty, 0,
                precision_rounding=self.product_id.uom_id.rounding) > 0:
            # Create an extra stock move line if this product has an
            # initial demand.

            print("picking_id **********************************", self.picking_id)

            line = StockMoveLine.create(
                self._prepare_move_line_values(available_qty))
            move_lines_dic[line.id] = available_qty
        self.picking_product_qty = sum(moves_todo.mapped('quantity_done'))
        return move_lines_dic

    def check_done_conditions(self):
        res = super().check_done_conditions()
        if self.product_id.tracking != 'none' and not self.lot_id:
            self._set_messagge_info('info', _('Waiting for input lot'))
            return False
        if not self.picking_id:
            self._set_messagge_info(
                'info', _('Not picking selected'))
            return False
        return res

    def _prepare_scan_log_values(self, log_detail=False):
        # Store in read log line each line added with the quantities assigned
        vals = super()._prepare_scan_log_values(log_detail=log_detail)
        vals['picking_id'] = self.picking_id.id
        if log_detail:
            vals['log_line_ids'] = [(0, 0, {
                'move_line_id': x[0],
                'product_qty': x[1],
            }) for x in log_detail.items()]
        return vals

    def remove_scanning_log(self, scanning_log):
        for log in scanning_log:
            log.unlink()

    def action_save_product_scaned(self):
        print("picking_id*************************", self.picking_id)
        for log in self.scan_log_ids:
            print("log***********", log)

    def action_undo_last_scan(self):
        res = super().action_undo_last_scan()
        log_scan = first(self.scan_log_ids.filtered(
            lambda x: x.create_uid == self.env.user))
        self.remove_scanning_log(log_scan)
        return res
