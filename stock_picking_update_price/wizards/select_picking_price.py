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
        index=True,
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
            # data.append((0, False, self._prepare_product_pricelist(move_line, move_line.product_id.list_price, 0)))
            for product_pricelist in product_pricelist_ids:
                pricelist_item_ids = move_line.product_id.pricelist_item_ids.search(
                    [('product_tmpl_id', '=', move_line.product_id.product_tmpl_id.id),
                     ('pricelist_id', '=', product_pricelist.id)])
                for pricelist_item in pricelist_item_ids:
                    data.append(
                        (0, False,
                         self._prepare_product_pricelist(move_line, pricelist_item, product_pricelist)))
        self.price_line_ids = data

    def _get_percent_sale_category(self, move_line, product_pricelist):
        category_pricelist_item = self.env['category.pricelist.item'].search_read(
            [('categ_id', '=', move_line.product_id.categ_id.id),('pricelist_id', '=', product_pricelist.id)],
            ['percentage'])
        if category_pricelist_item:
            return category_pricelist_item[0]['percentage']
        return 0.00

    def _get_purchase_price(self, move_line):
        stock_move = self.env['stock.move'].search_read(
            [('product_id', '=', move_line.product_id.id), ('picking_id', '<>', move_line.picking_id.id)],
            ['price_unit'],
            limit=1, order='date desc')
        if stock_move:
            return stock_move[0]['price_unit']
        return 0.00

    def _get_suggested_price(self, move_line, percent_sale_category):
        if percent_sale_category > 0.00:
            return move_line.product_id.standard_price + (
                move_line.product_id.standard_price * percent_sale_category / 100)
        return move_line.product_id.standard_price

    def _prepare_product_pricelist(self, move_line, pricelist_item, product_pricelist):
        percent_sale_category = self._get_percent_sale_category(move_line, product_pricelist)

        return ({
            'percent_sale_category': percent_sale_category,
            'product_text': move_line.product_id.name,
            'picking_id': move_line.picking_id,
            'product_id': move_line.product_id,
            'move_id': move_line.move_id,
            'cost_price': move_line.product_id.standard_price,
            'list_price': pricelist_item.fixed_price,
            'pricelist_id': product_pricelist.id,
            'pricelist_text': product_pricelist.name,
            'purchase_price': self._get_purchase_price(move_line),
            'suggested_price': self._get_suggested_price(move_line, percent_sale_category),
        })

    @api.multi
    def action_write_selected_picking_price(self):
        for line in self.price_line_ids.filtered(lambda r: r.selected):
            if line.pricelist_id.id == 0:
                line.product_id.list_price = line.suggested_price
            else:
                product_pricelist = line.product_id.mapped('pricelist_item_ids').filtered(
                    lambda l: l.pricelist_id == line.pricelist_id)
                if product_pricelist:
                    product_pricelist.fixed_price = line.suggested_price

class SelectPickingPriceLine(models.Model):
    _name = 'select.picking.price.line'
    _description = 'Select Picking Price Line Wizard'

    selected = fields.Boolean(
        string='Seleccionado',
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
        string='Producto',
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Operación',
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
    )
    list_price = fields.Float(
        'Precio Tarifa',
        digits=dp.get_precision('Product Price'),
    )
    suggested_price = fields.Float(
        'Precio Sugerido',
        digits=dp.get_precision('Product Price'),
    )
    product_text = fields.Text(
        'Nombre Producto',
    )
    pricelist_text = fields.Text(
        'Tarífa',
    )
    cost_price = fields.Float(
        'Precio Medio Costo',
    )
    purchase_price = fields.Float(
        'Precio Compra',
    )
    percent_sale_category = fields.Float(
        '% Margen Familia',
    )
    margin = fields.Float(
        'Margen',
        compute='_compute_margin_price',
    )
    percent_margin = fields.Float(
        '% Margen Real',
        compute='_compute_percent_margin',
    )
    reference_price = fields.Float(
        'Precio Referencia',
        compute='_compute_reference_price',
    )

    @api.onchange('suggested_price')
    def _onchange_standard_price(self):
        self.selected = True

    def _compute_reference_price(self):
        for line in self:
            if line.percent_sale_category > 0.00:
                line.reference_price = line.cost_price + ( line.cost_price * line.percent_sale_category / 100)
            else:
                line.reference_price = line.cost_price

    @api.depends('suggested_price')
    def _compute_margin_price(self):
        for line in self:
            line.margin = line.suggested_price - line.cost_price

    #    @api.onchange('suggested_price')
    @api.depends('suggested_price')
    def _compute_percent_margin(self):
        for line in self:
            if line.list_price != 0:
                line.percent_margin = (line.suggested_price - line.cost_price) / line.cost_price * 100
            else:
                line.percent_margin = 0
