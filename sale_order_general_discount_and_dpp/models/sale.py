
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from lxml import etree
import logging


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    discount_dpp = fields.Float(
        digits=dp.get_precision('Discount'),
        string='Descuento PP',
    )

    client_discount = fields.Float(
        digits=dp.get_precision('Discount'),
        string='Descuento Cliente',
    )

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super().onchange_partner_id()
        self.discount_dpp = self.partner_id.discount_dpp
        self.client_discount = self.partner_id.client_discount

        self.mapped('order_line').update({
            'discount3': self.discount_dpp,
        })

        self.mapped('order_line').update({
            'discount2': self.partner_id.client_discount,
        })
        return

    @api.onchange('discount_dpp')
    def onchange_general_discount(self):
        self.mapped('order_line').update({
            'discount3': self.discount_dpp,
        })

    @api.onchange('client_discount')
    def onchange_client_discount(self):
            self.mapped('order_line').update({
                'discount2': self.client_discount,
            })

    @api.onchange('order_line')
    def onchange_client_discount_line(self):

        logging.info(self.mapped('order_line'))
        self.mapped('order_line').update({
            'discount3': self.discount_dpp,
        })

        self.mapped('order_line').update({
            'discount2': self.client_discount,
        })

    @api.multi
    def _action_confirm(self):


        for order_line in self.mapped('order_line'):

            if (order_line.product_id.default_code == 'ENT30' or order_line.product_id.default_code == 'ENT0'):
                order_line.update({
                    'discount3': '0.00',
                })

                order_line.update({
                    'discount2': '0.00',
                })

            if( order_line.product_id.default_code !='ENT30' and order_line.product_id.default_code != 'ENT0'):

                if(order_line.discount2 != self.partner_id.client_discount and order_line.discount2 != 0.00):

                    order_line.update({
                        'discount3': self.discount_dpp,
                    })

                    order_line.update({
                        'discount2': self.client_discount,
                    })

        super().onchange_partner_id()

        return True

