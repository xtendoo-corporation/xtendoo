from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        result = True
        for order in self:
            if order.date_order:
                result = super(
                    SaleOrder,
                    order.with_context(preserve_existing_date_order=True),
                ).action_confirm()
            else:
                result = super(SaleOrder, order).action_confirm()
        return result

    def _prepare_confirmation_values(self):
        values = super()._prepare_confirmation_values()
        if self.env.context.get("preserve_existing_date_order"):
            values.pop("date_order", None)
        elif not values.get("date_order"):
            values["date_order"] = fields.Datetime.now()
        return values
