from odoo import models, fields, api

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    qty_int = fields.Integer(string='Cantidad (entera)', compute='_compute_qty_int', store=True)

    @api.depends('qty')
    def _compute_qty_int(self):
        for record in self:
            record.qty_int = int(record.qty)
            print(f"Computed qty_int for record {record.id}: {record.qty_int}")
            print(f"Original qty: {record.qty}")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'qty_int', 'qty', 'attribute_value_ids', 'custom_attribute_value_ids', 'price_unit', 'skip_change', 'uuid', 'price_subtotal', 'price_subtotal_incl', 'order_id', 'note', 'price_type', 'write_date',
            'product_id', 'discount', 'tax_ids', 'pack_lot_ids', 'customer_note', 'refunded_qty', 'price_extra', 'full_product_name', 'refunded_orderline_id', 'combo_parent_id', 'combo_line_ids', 'combo_item_id', 'refund_orderline_ids'
        ]

    def export_as_json(self):
        res = super().export_as_json()
        res['qty_int'] = int(self.qty)
        return res
