# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from ..services.scale_client import MatrixScaleClient

class MatrixWeightController(http.Controller):

    @http.route("/xtd/matrix/weight", type="json", auth="user", methods=["POST"])
    def xtd_matrix_weight(self):
        ICP = request.env["ir.config_parameter"].sudo()
        mode = ICP.get_param("xtendoo_matrix_weight.mode", "tcp")
        command = ICP.get_param("xtendoo_matrix_weight.command", "PF16")
        terminator = ICP.get_param("xtendoo_matrix_weight.terminator", "\r")
        timeout = float(ICP.get_param("xtendoo_matrix_weight.timeout", "2.0"))
        retries = int(ICP.get_param("xtendoo_matrix_weight.retries", "1"))

        if mode == "tcp":
            host = ICP.get_param("xtendoo_matrix_weight.tcp_host", "192.168.1.50")
            port = int(ICP.get_param("xtendoo_matrix_weight.tcp_port", "4001"))
            client = MatrixScaleClient(mode="tcp", host=host, port=port, terminator=terminator,
                                       command=command, timeout=timeout, retries=retries)
        else:
            serial_port = ICP.get_param("xtendoo_matrix_weight.serial_port", "/dev/ttyUSB0")
            baud = int(ICP.get_param("xtendoo_matrix_weight.baud", "9600"))
            parity = ICP.get_param("xtendoo_matrix_weight.parity", "N")
            stopbits = int(ICP.get_param("xtendoo_matrix_weight.stopbits", "1"))
            client = MatrixScaleClient(mode="serial", serial_port=serial_port, baudrate=baud,
                                       parity=parity, stopbits=stopbits, terminator=terminator,
                                       command=command, timeout=timeout, retries=retries)

        data = client.read_weight()
        return data
