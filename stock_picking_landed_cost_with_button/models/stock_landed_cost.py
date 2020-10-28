# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    @api.model
    def default_get(self, default_fields):
        """ Compute default partner_bank_id field for 'out_invoice' type,
        using the default values computed for the other fields.
        """
        res = super(LandedCost, self).default_get(default_fields)
        if self._context.get('default_picking_id') is not None:
            res['picking_ids'] = [self._context.get('default_picking_id')]
        return res

    def get_valuation_lines(self):
        """
        Override for allowing Average value inventory.
        :return: list of new line values
        """
        lines = []
        lines_number = 0

        for move in self.mapped('picking_ids').mapped('move_lines'):
            lines_number = lines_number + 1

        print("lines number******************", lines_number)
        print("self.amount_total*************", self.amount_total)

        landed_cost_per_line = self.amount_total / lines_number

        print("landed_cost_per_line**********", landed_cost_per_line)

        for move in self.mapped('picking_ids').mapped('move_lines'):
            # Only allow for real time valuated products with 'average' or 'fifo' cost
            if move.product_id.valuation != 'real_time' or move.product_id.cost_method not in ('fifo', 'average'):
                continue

            # Only allow positive
            if move.product_qty <= 0:
               move.product_qty = 1

            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': abs(move.value),
                'weight': move.product_id.weight * move.product_qty,
                'volume': move.product_id.volume * move.product_qty,
                'cost_variation': landed_cost_per_line / move.product_qty,
            }
            lines.append(vals)

        if not lines and self.mapped('picking_ids'):
            raise UserError(_(
                'The selected picking does not contain any move that would be impacted by landed costs. Landed costs '
                'are only possible for products configured in real time valuation with real price costing method. '
                'Please make sure it is the case, or you selected the correct picking'))
        return lines

    @api.multi
    def button_validate(self):
        """
        Override to directly set new standard_price on product if average costed.
        :return: True
        """
        if any(cost.state != 'draft' for cost in self):
            raise UserError(_('Only draft landed costs can be validated'))
        if any(not cost.valuation_adjustment_lines for cost in self):
            raise UserError(_('No valuation adjustments lines. You should maybe recompute the landed costs.'))
        if not self._check_sum():
            raise UserError(_('Cost and adjustments lines do not match. You should maybe recompute the landed costs.'))

        for cost in self:
            move = self.env['account.move']
            move_vals = {
                'journal_id': cost.account_journal_id.id,
                'date': cost.date,
                'ref': cost.name,
                'line_ids': [],
            }
            for line in cost.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                new_landed_cost_value = line.move_id.landed_cost_value + line.additional_landed_cost

                # Prorate the value at what's still in stock
                if line.move_id.product_qty:
                    cost_to_add = (line.move_id.remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
                    price_unit = (line.move_id.value + new_landed_cost_value) / line.move_id.product_qty
                else:
                    cost_to_add = 0
                    price_unit = 0

                line.move_id.write({
                    'landed_cost_value': new_landed_cost_value,
                    'value': line.move_id.value + line.additional_landed_cost,
                    'remaining_value': line.move_id.remaining_value + cost_to_add,
                    'price_unit': price_unit,
                    'cost_variation': line.move_id.product_qty,
                })

                # `remaining_qty` is negative if the move is out and delivered products that were not
                # in stock.
                qty_out = 0
                if line.move_id._is_in():
                    qty_out = line.move_id.product_qty - line.move_id.remaining_qty
                elif line.move_id._is_out():
                    qty_out = line.move_id.product_qty
                move_vals['line_ids'] += line._create_accounting_entries(move, qty_out)

                # Need to set the standard price directly on the product.
                if line.product_id.cost_method == 'average':
                    # From product.do_change_standard_price
                    quant_locs = self.env['stock.quant'].sudo().read_group(
                        [('product_id', '=', line.product_id.id)],
                        ['location_id'], ['location_id'])
                    quant_loc_ids = [loc['location_id'][0] for loc in quant_locs]
                    locations = self.env['stock.location'].search(
                        [('usage', '=', 'internal'),
                        ('company_id', '=', self.env.user.company_id.id),
                        ('id', 'in', quant_loc_ids)])
                    qty_available = line.product_id.with_context(location=locations.ids).qty_available
                    total_cost = (qty_available * line.product_id.standard_price) + cost_to_add
                    # Calculate standar_price avoid division by Zero
                    if qty_available != 0:
                        standard_price = total_cost / qty_available
                    else:
                        standard_price = 0
                    line.product_id.write({'standard_price': standard_price})

            move = move.create(move_vals)
            cost.write({'state': 'done', 'account_move_id': move.id})
            move.post()
        return True


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    def _compute_price_cost(self):
        for line in self:
            line.price_cost = line.former_cost_per_unit + line.cost_variation

    cost_variation = fields.Float(
        string='Cost Variation(Per Unit)',
        digits=dp.get_precision('Product Price'),
        store=True
    )
    price_cost = fields.Float(
        string='Subsequent Cost(Per Unit)',
        compute='_compute_price_cost',
        digits=dp.get_precision('Product Price'),
    )
