# Copyright 2023 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_volume_volume_in_cubic_feet = fields.Selection(
        selection_add=[('2', 'Litros')],
        ondelete={'2': 'set default'}
    )
