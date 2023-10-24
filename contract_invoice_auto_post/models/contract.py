# Copyright 2019-2020 Akretion France (http://www.akretion.com/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Contract(models.Model):
    _inherit = "contract"

    auto_post = fields.Selection(
        string="Auto-post",
        selection=[
            ("no", "No"),
            ("at_date", "At Date"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("yearly", "Yearly"),
        ],
        default="no",
        required=True,
        copy=False,
        help="Specify whether this entry is posted automatically on its accounting date, and any similar recurring invoices.",
    )
