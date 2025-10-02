# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ..services.scale_client import MatrixScaleClient

class StockPicking(models.Model):
    _inherit = "stock.picking"

    weight_from_scale = fields.Float(string="Peso (báscula)", digits="Stock Weight")

    def action_xtd_read_weight(self):
        params = self.env["ir.config_parameter"].sudo()
        mode = params.get_param("xtendoo_matrix_weight.mode", "tcp")
        command = params.get_param("xtendoo_matrix_weight.command", "PF16")
        terminator = params.get_param("xtendoo_matrix_weight.terminator", "\r")
        timeout = float(params.get_param("xtendoo_matrix_weight.timeout", "2.0"))
        retries = int(params.get_param("xtendoo_matrix_weight.retries", "1"))

        if mode == "tcp":
            host = params.get_param("xtendoo_matrix_weight.tcp_host", "192.168.1.50")
            port = int(params.get_param("xtendoo_matrix_weight.tcp_port", "4001"))
            client = MatrixScaleClient(
                mode="tcp", host=host, port=port, terminator=terminator,
                command=command, timeout=timeout, retries=retries
            )
        else:
            serial_port = params.get_param("xtendoo_matrix_weight.serial_port", "/dev/ttyUSB0")
            baud = int(params.get_param("xtendoo_matrix_weight.baud", "9600"))
            parity = params.get_param("xtendoo_matrix_weight.parity", "N")
            stopbits = int(params.get_param("xtendoo_matrix_weight.stopbits", "1"))
            client = MatrixScaleClient(
                mode="serial", serial_port=serial_port, baudrate=baud,
                parity=parity, stopbits=stopbits, terminator=terminator,
                command=command, timeout=timeout, retries=retries
            )

        for picking in self:
            try:
                data = client.read_weight()
                if data.get("value") is None:
                    raise UserError(_("No se pudo interpretar la respuesta de la báscula: %s") % (data.get("raw"),))
                picking.weight_from_scale = data["value"]
            except Exception as e:
                raise UserError(_("Error leyendo báscula: %s") % (str(e),))
        return True
