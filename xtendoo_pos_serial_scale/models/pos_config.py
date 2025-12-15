# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = "pos.config"

    # Activar/desactivar la integración de balanza serie
    xtendoo_serial_scale_enabled = fields.Boolean(
        string="Balanza Serie Habilitada",
        default=False,
        help="Habilitar la integración con balanza por puerto serie (Web Serial API)",
    )

    # Puerto orientativo (solo informativo, el usuario selecciona en el navegador)
    xtendoo_serial_port_hint = fields.Char(
        string="Puerto (orientativo)",
        default="COM7",
        help="Puerto serie orientativo (ej: COM7 en Windows, /dev/ttyUSB0 en Linux). "
             "El usuario seleccionará el puerto real en el diálogo del navegador.",
    )

    # Parámetros de conexión serie
    xtendoo_serial_baudrate = fields.Integer(
        string="Baud Rate",
        default=9600,
        help="Velocidad de transmisión en baudios (típico: 9600, 19200, 38400, 115200)",
    )

    xtendoo_serial_databits = fields.Selection(
        selection=[
            ("7", "7 bits"),
            ("8", "8 bits"),
        ],
        string="Bits de Datos",
        default="8",
        help="Número de bits de datos por carácter",
    )

    xtendoo_serial_stopbits = fields.Selection(
        selection=[
            ("1", "1 bit"),
            ("2", "2 bits"),
        ],
        string="Bits de Parada",
        default="1",
        help="Número de bits de parada",
    )

    xtendoo_serial_parity = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("even", "Par (Even)"),
            ("odd", "Impar (Odd)"),
        ],
        string="Paridad",
        default="none",
        help="Tipo de paridad para la verificación de errores",
    )

    xtendoo_serial_flowcontrol = fields.Selection(
        selection=[
            ("none", "Ninguno"),
            ("hardware", "Hardware (RTS/CTS)"),
        ],
        string="Control de Flujo",
        default="none",
        help="Tipo de control de flujo",
    )

    # Regex para extraer el peso del stream de la balanza
    xtendoo_serial_weight_regex = fields.Char(
        string="Regex para Peso",
        default=r"(-?\d+(?:[.,]\d+)?)",
        help="Expresión regular para extraer el peso del texto recibido de la balanza. "
             "Por defecto busca números decimales con punto o coma.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        """Añadir campos de balanza serie a los datos cargados en el POS."""
        result = super()._load_pos_data_fields(config)
        result += [
            "xtendoo_serial_scale_enabled",
            "xtendoo_serial_port_hint",
            "xtendoo_serial_baudrate",
            "xtendoo_serial_databits",
            "xtendoo_serial_stopbits",
            "xtendoo_serial_parity",
            "xtendoo_serial_flowcontrol",
            "xtendoo_serial_weight_regex",
        ]
        return result

