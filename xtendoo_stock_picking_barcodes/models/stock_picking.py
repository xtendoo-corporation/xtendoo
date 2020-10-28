# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _name = 'stock.picking'

    # line_picking_ids = fields.One2many(
    #     comodel_name='trn.line.picking',
    #     inverse_name='picking_id',
    #     string='Line pickings',
    #     readonly=True,
    # )

    def action_barcode_scan(self):
        out_picking = self.picking_type_code == 'outgoing'
        location = self.location_id if out_picking else self.location_dest_id
        action = self.env.ref(
            'xtendoo_stock_picking_barcodes.action_stock_barcodes_read_picking').read()[0]
        action['context'] = {
            'default_location_id': location.id,
            'default_partner_id': self.partner_id.id,
            'default_picking_id': self.id,
            'default_res_model_id':
                self.env.ref('stock.model_stock_picking').id,
            'default_res_id': self.id,
            'default_picking_type_code': self.picking_type_code,
        }
        return action

    # @api.multi
    # def read(self, fields=None, load='_classic_read'):
    #     result = super().read(fields, load)
    #     self._set_line_picking_ids()
    #     return result
    #
    # def _set_line_picking_ids(self):
    #     lines = [(5, 0, 0)]
    #     for l in self.move_ids_without_package:
    #         lines.extend([(0, 0, {
    #             'picking_id': self.id,
    #             'product_id': l.product_id,
    #             'reserved_availability': l.reserved_availability,
    #             'product_uom_qty': l.product_uom_qty,
    #             'quantity_done': l.quantity_done,
    #         })])
    #     self.line_picking_ids = lines
    #
    # def _prepare_lot_values(self, barcode_decoded):
    #     lot_barcode = barcode_decoded.get('10', False)
    #     return {
    #         'name': lot_barcode,
    #         'product_id': self.product_id.id,
    #     }
    #
    # def _create_lot(self, barcode_decoded):
    #     return self.env['stock.production.lot'].create(
    #         self._prepare_lot_values(barcode_decoded))
    #
    # def process_lot(self, barcode_decoded):
    #     lot_barcode = barcode_decoded.get('10', False)
    #     lot = self.env['stock.production.lot'].search([
    #         ('name', '=', lot_barcode),
    #         ('product_id', '=', self.product_id.id),
    #     ])
    #     if not lot:
    #         lot = self._create_lot(barcode_decoded)
    #     self.lot_id = lot
    #
    # def action_product_scaned_post(self, product):
    #     if self.product_id != product:
    #         self.lot_id = False
    #     self.product_id = product
    #     self.product_qty = 1.0
    #
    # def action_packaging_scaned_post(self, packaging):
    #     self.packaging_id = packaging
    #     if self.product_id != packaging.product_id:
    #         self.lot_id = False
    #     self.product_id = packaging.product_id
    #     self.packaging_qty = 1.0
    #     self.product_qty = packaging.qty * self.packaging_qty
    #
    # def _prepare_move_line_values(self, candidate_move, available_qty, product, lot):
    #     """When we've got an out picking, the logical workflow is that
    #        the scanned location is the location we're getting the stock
    #        from"""
    #     picking = self._origin
    #     out_move = picking.picking_type_id.code == 'outgoing'
    #     location_dest_id = (
    #         self.location_dest_id if out_move else self.location_id)
    #     return {
    #         'picking_id': picking.id,
    #         'move_id': candidate_move.id,
    #         'qty_done': available_qty,
    #         'product_id': product.id,
    #         'product_uom_id': product.uom_po_id.id,
    #         'location_id': self.location_id.id,
    #         'location_dest_id': location_dest_id.id,
    #         'lot_id': lot.id,
    #         'lot_name': lot.name,
    #     }
    #
    # def _prepare_stock_moves_domain(self, product):
    #     domain = [
    #         ('product_id', '=', product.id),
    #         ('picking_id', '=', self._origin.id),
    #     ]
    #     print("domain::::", domain)
    #     return domain
    #
    # def _process_stock_move_line(self, product, lot):
    #     available_qty = 1.0
    #     moves = self.env['stock.move'].search(
    #         self._prepare_stock_moves_domain(product)
    #     )
    #     lines = moves.filtered(
    #         lambda l: l.product_id == product and l.product_uom_qty >= l.quantity_done + available_qty
    #     )
    #     if not lines:
    #         self.env.user.notify_danger(
    #             message="There are no lines to assign that quantity")
    #         return False
    #
    #     lines = moves.mapped('move_line_ids').filtered(
    #         lambda l: (l.product_id == product and l.lot_id == lot)
    #     )
    #     for line in lines:
    #         if line.product_uom_qty:
    #             assigned_qty = min(
    #                 max(line.product_uom_qty - line.qty_done, 0.0),
    #                 available_qty)
    #         else:
    #             assigned_qty = available_qty
    #         line.write(
    #             {'qty_done': line.qty_done + assigned_qty}
    #         )
    #         available_qty -= assigned_qty
    #         if float_compare(
    #             available_qty, 0.0,
    #             precision_rounding=line.product_id.uom_id.rounding) < 1:
    #             break
    #     if float_compare(
    #         available_qty, 0,
    #         precision_rounding=product.uom_id.rounding) > 0:
    #         # Create an extra stock move line if this product has an
    #         # initial demand.
    #         moves = moves.mapped('move_line_ids').filtered(
    #             lambda l: (l.product_id == product)
    #         )
    #         if not moves:
    #             self.env.user.notify_danger(
    #                 message='There are no stock moves to assign this operation')
    #             return False
    #         else:
    #             self.env['stock.move.line'].create(
    #                 self._prepare_move_line_values(moves[0], available_qty, product, lot)
    #             )
    #     return True
    #
    # def _update_line_picking(self, product):
    #     for line in self.line_picking_ids.filtered(
    #         lambda l: l.product_id == product and l.product_uom_qty >= l.quantity_done + 1.0
    #     ):
    #         line.quantity_done = line.quantity_done + 1.0
    #         break
    #
    # def process_done(self, product, lot):
    #     if self._process_stock_move_line(product, lot):
    #         self._update_line_picking(product)
    #
    # def process_barcode_gs1(self, barcode):
    #     """ Only has been implemented AI (01, 02, 10, 37), so is possible that
    #     scanner reads a barcode ok but this one is not precessed.
    #     """
    #     barcode="02084800007201911099999"
    #     try:
    #         barcode_decoded = self.env['gs1_barcode'].decode(barcode)
    #     except Exception:
    #         return self.process_barcode(barcode)
    #     processed = False
    #
    #     product_barcode = barcode_decoded.get('02', False)
    #     lot_barcode = barcode_decoded.get('10', False)
    #     if not product_barcode:
    #         # Sometimes the product does not yet have a GTIN. In this case
    #         # try the AI 240 'Additional product identification assigned
    #         # by the manufacturer'.
    #         product_barcode = barcode_decoded.get('240', False)
    #     if product_barcode:
    #         product = self.env['product.product'].search(
    #             self._barcode_domain(product_barcode))
    #         if not product:
    #             self.env.user.notify_danger(
    #                 message='Barcode for product not found')
    #             return False
    #         else:
    #             if lot_barcode and product.tracking != 'none':
    #                 lot = self.env['stock.production.lot'].search([
    #                     ('name', '=', lot_barcode),
    #                     ('product_id', '=', product.id),
    #                 ])
    #                 if not lot:
    #                     self.env.user.notify_danger(
    #                         message='Lot for product not found')
    #                     return False
    #             processed = True
    #     if processed:
    #         self.process_done(product, lot)
    #         return True
    #     return self.process_barcode(barcode)
    #
    # def process_barcode(self, barcode):
    #     print("barcode en parent:::::::::",barcode)
    #     domain = self._barcode_domain(barcode)
    #     product = self.env['product.product'].search(domain)
    #     if not product:
    #         self.env.user.notify_danger(
    #             message='Product not found')
    #         return
    #     if product:
    #         if len(product) > 1:
    #             self.env.user.notify_danger(
    #                 message='More than one product found')
    #             # self._set_messagge_info(
    #             #     'more_match', _('More than one product found'))
    #             return
    #         self.action_product_scaned_post(product)
    #         self.process_done()
    #         return
    #
    #     if self.env.user.has_group('product.group_stock_packaging'):
    #         packaging = self.env['product.packaging'].search(domain)
    #         if packaging:
    #             if len(packaging) > 1:
    #                 self.env.user.notify_danger(
    #                     message='More than one package found')
    #                 return
    #             self.action_packaging_scaned_post(packaging)
    #             self.process_done()
    #             return
    #
    #     if self.env.user.has_group('stock.group_production_lot'):
    #         lot_domain = [('name', '=', barcode)]
    #         if self.product_id:
    #             lot_domain.append(('product_id', '=', self.product_id.id))
    #         lot = self.env['stock.production.lot'].search(lot_domain)
    #         if len(lot) == 1:
    #             self.product_id = lot.product_id
    #         if lot:
    #             self.action_lot_scaned_post(lot)
    #             self.process_done()
    #             return
    #     location = self.env['stock.location'].search(domain)
    #     if location:
    #         self.location_id = location
    #         self.env.user.notify_danger(
    #             message='Waiting product')
    #         return
    #     self.env.user.notify_danger(
    #         message='Barcode not found')
    #
    # def _barcode_domain(self, barcode):
    #     return [('barcode', '=', barcode)]
    #
    # def on_barcode_scanned(self, barcode):
    #     self.process_barcode_gs1(barcode)


class TrnLinePicking(models.TransientModel):
    _name = 'trn.line.picking'
    _description = 'Line pickings for barcode interface'
    _transient_max_hours = 48

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string='Product',
        required=True,
    )
    reserved_availability = fields.Float(
        string='Reserved',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
    )
    product_uom_qty = fields.Float(
        string='Demand',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
    )
    quantity_done = fields.Float(
        string='Done',
        digits=dp.get_precision('Product Unit of Measure'),
        readonly=True,
    )
    # For reload kanban view
    scan_count = fields.Integer()

    @api.depends('scan_count')
    def _compute_picking_quantity(self):
        for candidate in self:
            qty_reserved = 0
            qty_demand = 0
            qty_done = 0
            candidate.product_qty_reserved = sum(candidate.picking_id.mapped(
                'move_lines.reserved_availability'))
            for move in candidate.picking_id.move_lines:
                qty_reserved += move.reserved_availability
                qty_demand += move.product_uom_qty
                qty_done += move.quantity_done
            candidate.update({
                'product_qty_reserved': qty_reserved,
                'product_uom_qty': qty_demand,
                'product_qty_done': qty_done,
            })

    def _get_wizard_barcode_read(self):
        return self.env['wiz.stock.barcodes.read.picking'].browse(
            self.env.context['wiz_barcode_id'])
