# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_limited_product_count = fields.Integer(
        string="Productos cargados al iniciar el POS",
        config_parameter="point_of_sale.limited_product_count",
        default=500,
        help="Número máximo de productos que se cargarán en el primer batch "
             "al iniciar una sesión del TPV. Esto reduce el tiempo de arranque "
             "en bases de datos con catálogos grandes.\n\n"
             "Valores recomendados:\n"
             "• Para catálogos pequeños (< 5.000 productos): 0 (sin límite)\n"
             "• Para catálogos medianos (5.000-15.000): 500-1.000\n"
             "• Para catálogos grandes (15.000-50.000): 300-500\n"
             "• Para catálogos muy grandes (> 50.000): 200-300\n\n"
             "El valor 0 utiliza el comportamiento por defecto de Odoo "
             "(carga todos los productos).",
    )

    pos_limited_customer_count = fields.Integer(
        string="Clientes cargados al iniciar el POS",
        config_parameter="point_of_sale.limited_customer_count",
        default=500,
        help="Número máximo de clientes que se cargarán en el primer batch "
             "al iniciar una sesión del TPV. Esto reduce el tiempo de arranque "
             "en bases de datos con muchos clientes.\n\n"
             "Valores recomendados:\n"
             "• Para bases pequeñas (< 5.000 clientes): 0 (sin límite)\n"
             "• Para bases medianas (5.000-15.000): 500-1.000\n"
             "• Para bases grandes (15.000-50.000): 300-500\n"
             "• Para bases muy grandes (> 50.000): 200-300\n\n"
             "El valor 0 utiliza el comportamiento por defecto de Odoo "
             "(carga todos los clientes).",
    )

