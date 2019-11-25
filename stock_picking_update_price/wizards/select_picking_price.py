# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from odoo.addons import decimal_precision as dp

import logging


class SelectPickingPrice(models.Model):
    _name = 'select.picking.price'
    _description = 'Select Picking Price Wizard'

    picking_id = fields.Many2one('stock.picking', 'Stock Picking')
    price_line_ids = fields.One2many('select.picking.price.line', 'select_picking_id')

    @api.model
    def default_get(self, default_fields):
        result = super(SelectPickingPrice, self).default_get(default_fields)
        if self._context.get('default_picking_id') is not None:
            result['picking_id'] = self._context.get('default_picking_id')
        return result

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        data = []
        product_pricelist_ids = self.env['product.pricelist'].search([('active', '=', True)])

        self.price_line_ids = [(6, 0, [])]

        for move_line in self.picking_id.move_line_ids:
            data.append((0, False, self.get_list_price(move_line)))

            for product_pricelist in product_pricelist_ids:

                for pricelist_item in move_line.product_id.pricelist_item_ids.search(
                        [('product_tmpl_id', '=', move_line.product_id.product_tmpl_id.id),
                         ('pricelist_id', '=', product_pricelist.id)]):
                    data.append((0, False, self.get_others_price(move_line, pricelist_item, product_pricelist)))

        self.price_line_ids = data

    def _deprecated_get_dict_line(self, line):
        sale_price_line = {'product_id': line.product_id,
                           'previous_cost_price': line.move_id.previous_cost_price,
                           'purchase_price': line.move_id.purchase_line_id.price_unit,
                           'cost_price': line.product_id.standard_price,
                           'list_price': line.product_id.list_price,
                           'eur_price': 0,
                           'usd_price': 0}

        search = self.get_search_last_purchase(line.product_id)
        if search:
            sale_price_line.update({'previous_purchase_date': search.create_date})
            sale_price_line.update({'previous_purchase_price': search.purchase_line_id.price_unit})

        for price_list_item in line.product_id.pricelist_item_ids:
            if price_list_item.pricelist_id.name == 'Tarifa pública':
                sale_price_line.update({'eur_price': price_list_item.fixed_price})

            if price_list_item.pricelist_id.name == 'Tarifa privada':
                sale_price_line.update({'usd_price': price_list_item.fixed_price})

        return sale_price_line

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

    selected = fields.Boolean(string='Selected', default=True, help='Indicate this line is coming to change')
    select_picking_id = fields.Many2one('select.picking.price')
    picking_id = fields.Many2one('stock.picking', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    move_id = fields.Many2one('stock.move', string='Operations')
    list_price = fields.Float('List Price', digits=dp.get_precision('Product Price'))
    pricelist_id = fields.Many2one('product.pricelist')

    product_text = fields.Text('Product Text', compute='_compute_product_text')

    @api.onchange('list_price')
    def _onchange_standard_price(self):
        self.selected = True

    @api.multi
    def _compute_product_text(self):
        stock_move = self.env['stock.move']

        for line in self:
            if line.pricelist_id.id == 0:
                line.product_text = line.product_id.name

                search = stock_move.get_search_last_purchase(line.product_id, line.picking_id)
                if search:
                    line.product_text += " última compra " + search.create_date.strftime('%d-%m-%Y') + ","
                    line.product_text += " por un importe de " + str(search.purchase_line_id.price_unit)
            else:
                line.product_text = ''

    @api.multi
    def _compute_current_cost_price(self):
        for line in self:
            self.current_cost_price = self.product_id.standard_price
            self.current_list_price = self.product_id.list_price
            self.current_percent_price = 100 - ((self.product_id.standard_price / self.product_id.list_price) * 100)

    @api.multi
    @api.onchange('list_price')
    def _compute_percent_list_price(self):
        for line in self:
            if self.list_price != 0:
                self.percent_list_price = 100 - ((self.product_id.standard_price / self.list_price) * 100)
            else:
                self.percent_list_price = 0
