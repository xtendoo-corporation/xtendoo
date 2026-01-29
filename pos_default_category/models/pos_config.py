from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    default_pos_category_id = fields.Many2one(
        "pos.category",
        string="Categoría TPV predeterminada",
        help="Categoría seleccionada al abrir el TPV",
    )


