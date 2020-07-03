# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(SaleOrder, self).onchange_partner_id()
        partners_invoice = []
        partners_shipping = []
        domain = {}
        for record in self:
            if record.partner_id:
                if record.partner_id.child_ids:
                    for partner in record.partner_id.child_ids:
                        if partner.type == 'invoice':
                            partners_invoice.append(partner.id)
                        if partner.type == 'delivery':
                            partners_shipping.append(partner.id)
                if partners_invoice:
                    domain['partner_invoice_id'] =  [('id', 'in', partners_invoice)]
                else:
                    domain['partner_invoice_id'] =  []
                if partners_shipping:
                    domain['partner_shipping_id'] = [('id', 'in', partners_shipping)]
                else:
                    domain['partner_shipping_id'] =  []
            else:
                domain['partner_invoice_id'] =  [('type', '=', 'invoice')]
                domain['partner_shipping_id'] =  [('type', '=', 'delivery')]

        return {'domain': domain}
