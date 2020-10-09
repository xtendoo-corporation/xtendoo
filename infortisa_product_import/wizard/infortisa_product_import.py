# -*- coding: utf-8 -*-

import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)



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
        raise UserError(_('Import file'))

