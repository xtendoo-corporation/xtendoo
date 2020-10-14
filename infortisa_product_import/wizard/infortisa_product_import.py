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

    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()

        data_file = b64decode(self.data_file)

        if not data_file:
            return

        self._parse_file(data_file)

    def _parse_file(self, data_file):
        data = StringIO(data_file.decode('utf-8'))
        print(data)
        csv_data = reader(data)
        print(list(next(csv_data)))

        for row in csv_data:
            print("*"*80)
            print(list(row))




