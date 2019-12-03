# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from . import select_picking_price


@api.multi
@api.onchange('list_price')
def _compute_percent_list_price(self):
    for line in self:
        line.margin = line.list_price - line.move_id.purchase_line_id.price_unit
        if line.list_price != 0:
            line.percent_margin = 100 - ((line.purchase_price / line.list_price) * 100)
        else:
            line.percent_margin = 0


str(search.purchase_line_id.price_unit)