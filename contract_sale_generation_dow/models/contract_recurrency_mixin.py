# Copyright 2023 Jaime Millan (<https://xtendoo.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

class ContractRecurrencyBasicMixin(models.AbstractModel):
    _inherit = "contract.recurrency.basic.mixin"

    monday = fields.Boolean(string='Monday')
    tuesday = fields.Boolean(string='Tuesday')
    wednesday = fields.Boolean(string='Wednesday')
    thursday = fields.Boolean(string='Thursday')
    friday = fields.Boolean(string='Friday')
    saturday = fields.Boolean(string='Saturday')
    sunday = fields.Boolean(string='Sunday')
