from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        for so in self:
            for line in so.order_line:
                if not line.lot_id and line.product_id.tracking == 'lot':
                    raise UserError(
                        _('You can\'t store this line %s with empty lot') %
                        line.product_id.name
                        )

                product_lot_qty = self._product_lot_qty(so, line)
                if product_lot_qty < line.product_uom_qty:
                    raise UserError(
                        _('Not enough stock in lot %s, only %.2f for product : %s') %
                        (line.lot_id.name, product_lot_qty, line.product_id.name )
                    )
        return res

    def _product_lot_qty(self, so, line):
        if so.warehouse_id and line.product_id:
            quants = self.env['stock.quant'].search([
                ('location_id', 'child_of', so.warehouse_id.lot_stock_id.id),
                ('product_id', '=', line.product_id.id),
                ('lot_id', '=', line.lot_id.id),
            ])
            if quants:
                return sum(quants.mapped('quantity'))
        return 0


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot', copy=False)
    # first_selection = fields.Boolean(
    #     comodel_name='sale.order.line',
    #     string="firstSelection",
    #     default=False
    # )
    #
    # @api.multi
    # @api.onchange('product_id')
    # def product_id_change(self):
    #     self.first_selection=True
    #     super(SaleOrderLine, self).product_id_change()
    #     self.lot_id = False

    @api.onchange('product_uom_qty','lot_id','product_uom')
    def _onchage_quantity_or_lot(self):
    #     if self.first_selection != True:
        if not self.product_id:
            return
        if self.product_id.tracking != 'lot':
            return
        if not self.lot_id:
            return
            #raise UserError(_("Please select a lot"))
        product_lot_qty = self._product_lot_qty()
        product_uom_qty = self.product_uom_qty * self.product_uom.factor_inv
        if product_lot_qty < product_uom_qty:
            raise UserError(
                _('Not enough stock in lot %s, only %.2f for product : %s') %
                (self.lot_id.name, product_lot_qty, self.product_id.name )
                )

    def _product_lot_qty(self):
        if self.order_id.warehouse_id and self.product_id:
            quants = self.env['stock.quant'].search([
                ('location_id', 'child_of', self.order_id.warehouse_id.lot_stock_id.id),
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id),
            ])
            if quants:
                return sum(quants.mapped('quantity'))
        return 0
