# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_uom_selection = fields.Boolean(
        string="Permitir selección de UdM",
        default=True,
        help="Permite cambiar la unidad de medición de los productos en el POS"
    )
