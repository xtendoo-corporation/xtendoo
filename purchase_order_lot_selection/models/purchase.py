from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot', copy=False)

    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        super(PurchaseOrderLine, self).onchange_product_id()
        self.lot_id = False

    @api.onchange('product_id')
    def _onchange_product_id_set_lot_domain(self):
        available_lot_ids = []
        if self.product_id:
            quants = self.env['stock.quant'].read_group([
                ('product_id', '=', self.product_id.id),
                ('lot_id', '!=', False),
            ], ['lot_id'], 'lot_id')
            available_lot_ids = [quant['lot_id'][0] for quant in quants]
        self.lot_id = False
        return {
            'domain': {'lot_id': [('id', 'in', available_lot_ids)]}
        }



#class PurchaseOrder(models.Model):
#    _inherit = "purchase.order"
#
#    @api.model
#    def get_move_from_line(self, line):
#        move = self.env['stock.move']
#        # i create this counter to check lot's univocity on move line
#        lot_count = 0
#        for p in line.order_id.picking_ids:
#            for m in p.move_lines:
#                move_line_id = m.move_line_ids.filtered(
#                    lambda line: line.lot_id)
#                if move_line_id and line.lot_id == move_line_id[:1].lot_id:
#                    move = m
#                    lot_count += 1
#                    # if counter is 0 or > 1 means that something goes wrong
#                    if lot_count != 1:
#                        raise UserError(_('Can\'t retrieve lot on stock'))
#        return move
#
#    @api.model
#    def _check_move_state(self, line):
#        if line.lot_id:
#            move = self.get_move_from_line(line)
#            if move.state == 'confirmed':
#                move._action_assign()
#                move.refresh()
#            if move.state != 'assigned':
#                raise UserError(_('Can\'t reserve products for lot %s') %
#                                line.lot_id.name)
#        return True
#
#    @api.multi
#    def action_confirm(self):
#        res = super(PurchaseOrder, self.with_context(sol_lot_id=True))\
#            .action_confirm()
#        for line in self.order_line:
#            if line.lot_id:
#                unreserved_moves = line.move_ids.filtered(
#                    lambda move: move.product_uom_qty !=
#                    move.reserved_availability
#                )
#                if unreserved_moves:
#                    raise UserError(
#                        _('Can\'t reserve products for lot %s')
#                        % line.lot_id.name
#                    )
#            self._check_move_state(line)
#        return res
