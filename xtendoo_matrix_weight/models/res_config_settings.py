# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xtd_scale_mode = fields.Selection([
        ("tcp", "TCP (conversor RS↔TCP)"),
        ("serial", "Serie local (USB-RS232)")
    ], string="Modo conexión báscula", default="tcp", config_parameter="xtendoo_matrix_weight.mode")

    xtd_scale_tcp_host = fields.Char(string="Host TCP", config_parameter="xtendoo_matrix_weight.tcp_host", default="192.168.1.50")
    xtd_scale_tcp_port = fields.Integer(string="Puerto TCP", config_parameter="xtendoo_matrix_weight.tcp_port", default=4001)

    xtd_scale_serial_port = fields.Char(string="Puerto serie", config_parameter="xtendoo_matrix_weight.serial_port", default="/dev/ttyUSB0")
    xtd_scale_serial_baud = fields.Integer(string="Baudrate", config_parameter="xtendoo_matrix_weight.baud", default=9600)
    xtd_scale_serial_parity = fields.Selection([
        ("N","None"),("E","Even"),("O","Odd")
    ], string="Paridad", default="N", config_parameter="xtendoo_matrix_weight.parity")
    xtd_scale_serial_stopbits = fields.Selection([
        ("1","1"),("2","2")
    ], string="Stop bits", default="1", config_parameter="xtendoo_matrix_weight.stopbits")
    xtd_scale_terminator = fields.Selection([
        ("\r","CR (\\r)"),
        ("\r\n","CRLF (\\r\\n)"),
    ], string="Terminador", default="\r", config_parameter="xtendoo_matrix_weight.terminator")

    xtd_scale_command = fields.Char(string="Comando (PF12/PF16/P)", default="PF16",
        config_parameter="xtendoo_matrix_weight.command")

    xtd_scale_timeout = fields.Float(string="Timeout (s)", default=2.0, config_parameter="xtendoo_matrix_weight.timeout")
    xtd_scale_retries = fields.Integer(string="Reintentos", default=1, config_parameter="xtendoo_matrix_weight.retries")

    @api.constrains("xtd_scale_mode")
    def _check_deps(self):
        if any(rec.xtd_scale_mode == "serial" for rec in self):
            try:
                import serial  # noqa: F401
            except Exception:
                raise UserError(_("Para modo serie necesitas instalar 'pyserial' en el servidor de Odoo."))
