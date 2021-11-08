# Copyright 2021 Xtendoo (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    pic_name = fields.Char('Pic Name', compute="_compute_pic_name")

    def _compute_pic_name(self):
        for picking in self:
            picking.pic_name = picking.name
            alb_ids = self.env['stock.picking'].search([('sale_id', '=', picking.sale_id.id), ('name', 'like', 'ALB%')],order='date_done desc')
            pic_ids = self.env['stock.picking'].search([('sale_id', '=', picking.sale_id.id), ('name', 'like', 'PIC%')],order='date_done desc')
            print(len(alb_ids))
            if "PIC" in picking.name:
                i = 0
                for pic_id in pic_ids:
                    if pic_id.name == picking.name:
                        if len(alb_ids) > 1:
                            picking.pic_name = alb_ids[i].name
                        else:
                            picking.pic_name = alb_ids.name
                    i += 1




