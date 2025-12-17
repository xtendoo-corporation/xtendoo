# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Campos relacionados con pos.config para la balanza serie
    pos_xtendoo_serial_scale_enabled = fields.Boolean(
        related="pos_config_id.xtendoo_serial_scale_enabled",
        readonly=False,
        string="Balanza Serie Habilitada",
    )

    pos_xtendoo_serial_port_hint = fields.Char(
        related="pos_config_id.xtendoo_serial_port_hint",
        readonly=False,
        string="Puerto (orientativo)",
    )

    pos_xtendoo_serial_baudrate = fields.Integer(
        related="pos_config_id.xtendoo_serial_baudrate",
        readonly=False,
        string="Baud Rate",
    )

    pos_xtendoo_serial_databits = fields.Selection(
        related="pos_config_id.xtendoo_serial_databits",
        readonly=False,
        string="Bits de Datos",
    )

    pos_xtendoo_serial_stopbits = fields.Selection(
        related="pos_config_id.xtendoo_serial_stopbits",
        readonly=False,
        string="Bits de Parada",
    )

    pos_xtendoo_serial_parity = fields.Selection(
        related="pos_config_id.xtendoo_serial_parity",
        readonly=False,
        string="Paridad",
    )

    pos_xtendoo_serial_flowcontrol = fields.Selection(
        related="pos_config_id.xtendoo_serial_flowcontrol",
        readonly=False,
        string="Control de Flujo",
    )

    pos_xtendoo_serial_weight_regex = fields.Char(
        related="pos_config_id.xtendoo_serial_weight_regex",
        readonly=False,
        string="Regex para Peso",
    )

