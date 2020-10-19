# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from base64 import b64decode
from io import StringIO

import logging

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class InfortisaProductImport(models.TransientModel):
    _name = 'infortisa.product.import'
    _description = 'Infortisa Product Import'

    data_file = fields.Binary(
        string='File to Import',
        required=True,
        help='Get you data from Infortisa.'
    )
    filename = fields.Char()
    category = fields.Char()

    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()

        data_file = b64decode(self.data_file)

        if not data_file:
            return

        self._parse_file(data_file)

    def parse_categories(self, row, parent_id):
        # if self.category != row[5]:

        category = self.env['product.category'].search([
            ('name', '=', row[5]),
        ])
        if category:
            print('Existe categoria')
        else:
            print('Creando categoria')
            self.env['product.category'].create({
                'name': row[5],
                'parent_id': parent_id,
            })
        #    self.category = row[5]

    def parse_product(self, row):
        print("*" * 80)
        #           print(list(row))
        print(row[2])
        price = float(row[10].replace(',', '.'))

        category = self.env['product.category'].search([
            ('name', '=', row[5]),
        ])

        if category:
            category_id = category.id
        else:
            category_id = 0

        product = self.env['product.product'].search([
            ('default_code', '=', row[2]),
        ])

        if product:
            print('Existe')
            product.write({'name': row[1],
                           # 'barcode': row[8],
                           'categ_id': category_id,
                           'list_price': price,
                           })
        else:
            print('No Existe')
            self.env['product.template'].create({
                'name': row[1],
                'default_code': row[2],
                'categ_id': category_id,
                'list_price': price,
            })

    def get_parent_id(self):
        category_parent_id = self.env['product.category'].search([
            ('name', '=', 'Todos'),
        ])
        if category_parent_id:
            return category_parent_id.id
        return 0

    def _parse_file(self, data_file):
        data = StringIO(data_file.decode('utf-8'))
        print(data)
        csv_data = reader(data)
        print(list(next(csv_data)))

        parent_id = self.get_parent_id()

        for row in csv_data:
            self.parse_categories(row, parent_id)
            self.parse_product(row)

        return

        # for row in csv_data:
        #     print("*"*80)
        #     print(list(row))
