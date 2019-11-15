# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api
from odoo.addons import decimal_precision as dp

import logging


class SelectSalePrice(models.TransientModel):
    _name = 'select.sale.price'
    _description = 'Select Sale Price Wizard'

    picking_id = fields.Many2one('stock.picking', 'Stock Picking')
    price_line_ids = fields.One2many('select.sale.price.line', 'sale_id')

    @api.model
    def default_get(self, default_fields):
        result = super(SelectSalePrice, self).default_get(default_fields)
        if self._context.get('default_picking_id') is not None:
            result['picking_id'] = self._context.get('default_picking_id')
        return result

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        data = []
        self.price_line_ids = [(6, 0, [])]

        for move_line in self.picking_id.move_line_ids:
            data.append((0, False, self.get_list_price(move_line)))

            for product_pricelist in self.env['product.pricelist'].search([('active', '=', True)]):
                data.append((0, False, self.get_others_price(move_line, product_pricelist)))

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
    def get_dict_line(line):
        return {'product_id': line.product_id, 'move_id': line.move_id}

    def get_list_price(self, move_line):
        return {'product_id': move_line.product_id,
                'move_id': move_line.move_id,
                'list_price': move_line.product_id.list_price}

    @staticmethod
    def get_others_price(move_line, pricelist_item):
        fixed_price = 0
        search = move_line.product_id.pricelist_item_ids.search([('pricelist_id', '=', pricelist_item.id)])
        logging.info("*******************search****************")
        logging.info(search)

        # for price_list_item in move_line.product_id.pricelist_item_ids:
        #     if price_list_item.pricelist_id.name == name:
        #         fixed_price = price_list_item.fixed_price
        # dict_line = self.get_dict_line(move_line)
        # dict_line.update({'list_price': fixed_price})

        return {'product_id': move_line.product_id,
                'move_id': move_line.move_id,
                'list_price': fixed_price}

    def get_search_last_purchase(self, product_id):
        return self.env['stock.move'].search(
            [['product_id', '=', product_id.id], ['picking_id', '<>', self.picking_id.id]], limit=1,
            order='date desc')

    @api.multi
    def action_select_sale_price(self):
        # logging.info("+"*80)
        for line in self.price_line_ids.filtered(lambda r: r.selected):
            line.product_id.list_price = line.list_price

            for price_list_item in line.product_id.pricelist_item_ids:
                # logging.info(price_list_item.pricelist_id.name)
                if price_list_item.pricelist_id.name == 'Tarifa pública':
                    # logging.info("eur_price")
                    # logging.info(line.eur_price)
                    # logging.info(price_list_item.pricelist_id.id)
                    price_list_item.fixed_price = line.eur_price

                if price_list_item.pricelist_id.name == 'Tarifa privada':
                    # logging.info("usd_price")
                    # logging.info(line.usd_price)
                    # logging.info(price_list_item.pricelist_id.id)
                    price_list_item.fixed_price = line.usd_price


class SelectSalePriceLine(models.TransientModel):
    _name = 'select.sale.price.line'
    _description = 'Select Sale Price Line Wizard'

    selected = fields.Boolean(string='Selected', default=True, help='Indicate this line is coming to change')
    sale_id = fields.Many2one('select.sale.price')
    product_id = fields.Many2one('product.product', string='Product', required=True)

    previous_purchase_date = fields.Datetime('Previous Purchase Date', required=False)
    previous_purchase_price = fields.Float('Previous Purchase Price', digits=dp.get_precision('Product Price'))
    previous_cost_price = fields.Float('Previous Cost', digits=dp.get_precision('Product Price'))
    purchase_price = fields.Float('Purchase Price', digits=dp.get_precision('Product Price'))
    cost_price = fields.Float('Cost Price', digits=dp.get_precision('Product Price'))
    list_price = fields.Float('List Price', digits=dp.get_precision('Product Price'))
    eur_price = fields.Float('EUR Price', digits=dp.get_precision('Product Price'))
    usd_price = fields.Float('USD Price', digits=dp.get_precision('Product Price'))

    current_cost_price = fields.Float('Current Cost', digits=dp.get_precision('Product Price'), compute='_compute_current_cost_price')
    current_list_price = fields.Float('Current List Price', digits=dp.get_precision('Product Price'), compute='_compute_current_cost_price')
    current_percent_price = fields.Float('Current Percent Price', digits=dp.get_precision('Product Price'), compute='_compute_current_cost_price')

    percent_list_price = fields.Float('Percent List Price', digits=dp.get_precision('Product Price'), compute='_compute_percent_list_price')
    percent_eur_price = fields.Float('Percent Eur Price', digits=dp.get_precision('Product Price'), compute='_compute_percent_list_price')
    percent_usd_price = fields.Float('Percent Usd Price', digits=dp.get_precision('Product Price'), compute='_compute_percent_list_price')

    @api.onchange('standard_price', 'eur_price', 'usd_price')
    def _onchange_standard_price(self):
        self.selected = True

    @api.multi
    def _compute_current_cost_price(self):
        for line in self:
            self.current_cost_price = self.product_id.standard_price
            self.current_list_price = self.product_id.list_price
            self.current_percent_price = 100 - ((self.product_id.standard_price / self.product_id.list_price) * 100)

    @api.multi
    @api.onchange('list_price', 'eur_price', 'usd_price')
    def _compute_percent_list_price(self):
        for line in self:
            if self.list_price != 0:
                self.percent_list_price = 100 - ((self.product_id.standard_price / self.list_price) * 100)
            else:
                self.percent_list_price = 0
            if self.eur_price != 0:
                self.percent_eur_price = 100 - ((self.product_id.standard_price / self.eur_price) * 100)
            else:
                self.percent_eur_price = 0
            if self.usd_price != 0:
                self.percent_usd_price = 100 - ((self.product_id.standard_price / self.usd_price) * 100)
            else:
                self.percent_usd_price = 0