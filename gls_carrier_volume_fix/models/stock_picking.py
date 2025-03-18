from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _compute_volume_uom_name(self):
        self.volume_uom_name = self.env[
            "product.template"
        ]._get_volume_uom_name_from_ir_config_parameter()

    volume_uom_name = fields.Char(
        string="Volume unit of measure label",
        compute="_compute_volume_uom_name",
        readonly=True,
        default=_compute_volume_uom_name,
    )

    def _compute_volume(self):
        for record in self:
            record.volume = sum(
                move.product_id.volume * move.quantity_done
                for move in record.move_ids_without_package
            )

    volume = fields.Float(compute="_compute_volume", default=_compute_volume)
