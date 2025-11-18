# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Xtendoo POS Performance",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Mejora el rendimiento del POS limitando la carga inicial de productos y clientes",
    "description": """
        Módulo de Rendimiento para Punto de Venta
        ==========================================

        Este módulo mejora el rendimiento del TPV en bases de datos con muchos productos
        (por ejemplo, 35.000 productos).

        Se apoya en los parámetros de sistema internos de Odoo para limitar la carga
        inicial de productos y clientes en el POS:

        - point_of_sale.limited_product_count
        - point_of_sale.limited_customer_count

        La idea es que el POS cargue solo un número limitado de productos/clientes
        en el primer batch al abrir la sesión, y el resto se vaya cargando en segundo
        plano o bajo demanda, reduciendo así el tiempo de arranque del POS.

        Características:
        ----------------
        * Configuración desde Ajustes → Punto de venta
        * Valores por defecto razonables (500 productos y 500 clientes)
        * Interfaz en español
        * Compatible con Odoo 19.0 Community y Enterprise
    """,
    "author": "Xtendoo Software S.L.U.",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "data/ir_config_parameter_data.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

