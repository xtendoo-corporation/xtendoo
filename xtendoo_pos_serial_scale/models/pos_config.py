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
        help="Expresión regular para extraer el peso del texto recibido de la balanza.\n\n"
             "IMPORTANTE: Usa paréntesis de captura () para el número del peso.\n\n"
             "Patrones comunes:\n"
             "• (-?\\d+(?:[.,]\\d+)?) - Cualquier número decimal (defecto)\n"
             "• ST,([-?\\d.,]+),kg - Formato: ST,12.345,kg\n"
             "• (\\d+\\.\\d+)\\s*kg - Formato: 12.345 kg\n"
             "• W\\s+(\\d+\\.\\d+) - Formato: W 12.345\n"
             "• NET\\s+(\\d+,\\d+) - Formato: NET 12,345\n\n"
             "DEPURACIÓN:\n"
             "Si la balanza conecta pero no lee el peso:\n"
             "1. Abrir la consola del navegador (F12)\n"
             "2. Conectar la balanza y colocar peso\n"
             "3. Buscar '[SerialScaleService] Línea recibida:' en los logs\n"
             "4. Ajustar esta regex según el formato mostrado\n"
             "5. Consultar TROUBLESHOOTING.md para ejemplos detallados",
    )

    xtendoo_serial_weight_unit = fields.Selection(
        selection=[
            ("kg", "Kilogramos (kg)"),
            ("g", "Gramos (g)"),
            ("lb", "Libras (lb)"),
        ],
        string="Unidad de Peso",
        default="kg",
        help="Unidad de medida del peso recibido de la balanza",
    )


