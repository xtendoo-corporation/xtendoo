# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_transportista = fields.Boolean(
        string='Transportista efectivo',
        help='Marque esta casilla para que este contacto pueda '
             'seleccionarse como transportista efectivo al generar un DeCA '
             '(art. 6.b Orden FOM/2861/2012).')
