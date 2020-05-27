from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"


    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        for so in self:
            for line in so.order_line:
                if not line.lot_id and line.product_id.tracking == 'lot':
                    raise UserError(
                        _('You can\'t store this line %s with empty lot') %
                        line.product_id.name
                        )
        return res
