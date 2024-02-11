from odoo import _, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    return_voucher_validity = fields.Integer(
        default=30,
        help="If you leave this option empty, the vouchers will have an "
        "indefinite date, i.e., they will never expire.",
    )
