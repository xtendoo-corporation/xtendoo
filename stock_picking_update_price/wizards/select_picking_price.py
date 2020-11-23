# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Copyright 2020 Xtendoo - Manuel Calero Solis

from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from datetime import datetime


class SelectPickingPrice(models.Model):
    _name = 'select.picking.price'
    _description = 'Select Picking Price Wizard'

    name = fields.Char(
        string="Select Picking Price",
        help="Name Select Picking Price",
        required=True,
        index=True,
        track_visibility="always",
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.picking.update.price'),
    )
    picking_id = fields.Many2one(
        'stock.picking',
        'Stock Picking',
    )
    price_line_ids = fields.One2many(
        'select.picking.price.line',
        'select_picking_id',
    )
    date = fields.Datetime(
        'Date',
        default=datetime.now(),
        readonly=True,
    )

    @api.model
    def default_get(self, default_fields):
        result = super(SelectPickingPrice, self).default_get(default_fields)
        if self._context.get('default_picking_id') is not None:
            result['picking_id'] = self._context.get('default_picking_id')
        return result

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        data = [(6, 0, [])]
        product_pricelist_ids = self.env['product.pricelist'].search([('active', '=', True)])
        for move_line in self.picking_id.move_line_ids:
            data.append((0, False, self.get_list_price(move_line)))
            for product_pricelist in product_pricelist_ids:
                pricelist_item_ids = move_line.product_id.pricelist_item_ids.search(
                    [('product_tmpl_id', '=', move_line.product_id.product_tmpl_id.id),
                     ('pricelist_id', '=', product_pricelist.id)])
                for pricelist_item in pricelist_item_ids:
                    data.append((0, False, self.get_others_price(move_line, pricelist_item, product_pricelist)))
        self.price_line_ids = data

    @staticmethod
    def get_list_price(move_line):
        return {'picking_id': move_line.picking_id,
                'product_id': move_line.product_id,
                'move_id': move_line.move_id,
                'list_price': move_line.product_id.list_price,
                'pricelist_id': 0}

    @staticmethod
    def get_others_price(move_line, pricelist_item, product_pricelist):
        return {'picking_id': move_line.picking_id,
                'product_id': move_line.product_id,
                'move_id': move_line.move_id,
                'list_price': pricelist_item.fixed_price,
                'pricelist_id': product_pricelist.id}

    @staticmethod
    def get_dict_line(line):
        return {'product_id': line.product_id, 'move_id': line.move_id}

    @api.multi
    def action_write_selected_picking_price(self):
        for line in self.price_line_ids.filtered(lambda r: r.selected):
            if line.pricelist_id.id == 0:
                line.product_id.list_price = line.list_price
            else:
                product_pricelist = line.product_id.mapped('pricelist_item_ids').filtered(
                    lambda l: l.pricelist_id == line.pricelist_id)
                if product_pricelist:
                    product_pricelist.fixed_price = line.list_price


class SelectPickingPriceLine(models.Model):
    _name = 'select.picking.price.line'
    _description = 'Select Picking Price Line Wizard'

    selected = fields.Boolean(
        string='Selected',
        default=True,
        help='Indicate this line is coming to change'
    )
    select_picking_id = fields.Many2one(
        'select.picking.price'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Operations',
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
    )
    list_price = fields.Float(
        'List Price',
        digits=dp.get_precision('Product Price'),
    )
    product_text = fields.Text(
        'Product Text',
        compute='_compute_price_line',
    )
    pricelist_text = fields.Text(
        'Price List Text',
        compute='_compute_price_line',
    )
    cost_price = fields.Float(
        'Cost Price',
        compute='_compute_price_line',
    )
    purchase_price = fields.Float(
        'Purchase Price',
        compute='_compute_price_line',
    )
    margin = fields.Float(
        'Margin',
        compute='_compute_price_line',
    )
    percent_margin = fields.Float(
        'Percent Margin %',
        compute='_compute_price_line',
    )
    percent_sale_category = fields.Float(
        'Sale Percent %',
        compute='_compute_price_line',
    )
    suggested_price = fields.Float(
        'Suggested Price',
        compute='_compute_price_line',
    )

    @api.onchange('list_price')
    def _onchange_standard_price(self):
        self.selected = True

    @api.multi
    def _compute_price_line(self):
        stock_move = self.env['stock.move']
        category_pricelist_item = self.env['category.pricelist.item']

        for line in self:
            if line.pricelist_id.id == 0:
                line.product_text = line.product_id.name
                line.pricelist_text = 'Sales Price'

                search = stock_move.get_search_last_purchase(line.product_id, line.picking_id)
                if search:
                    line.product_text += " última compra " + search.create_date.strftime('%d-%m-%Y') + ","
                    line.product_text += " por un importe de " + str(search.purchase_line_id.price_unit)
            else:
                line.product_text = ''
                line.pricelist_text = line.pricelist_id.name

            line.cost_price = line.product_id.standard_price

            if line.percent_sale_category > 0.00:
                line.suggested_price = line.cost_price + (line.cost_price * line.percent_sale_category / 100)
            else:
                line.suggested_price = line.cost_price

            line.margin = line.cost_price - line.suggested_price

            if line.suggested_price != 0:
                line.percent_margin = ( (line.suggested_price - line.cost_price) / line.suggested_price * 100 )
            else:
                line.percent_margin = 0

            line.purchase_price = line.move_id.purchase_line_id.price_unit

            line.percent_sale_category = category_pricelist_item.get_sale_percent(line.product_id, line.pricelist_id)

    @api.multi
    @api.onchange('list_price')
    def _compute_percent_list_price(self):
        for line in self:
            line.margin = line.list_price - line.move_id.purchase_line_id.price_unit
            if line.list_price != 0:
                line.percent_margin = 100 - (line.purchase_price / line.list_price * 100)
            else:
                line.percent_margin = 0
