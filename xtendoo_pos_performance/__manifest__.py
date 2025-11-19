# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Xtendoo POS Performance",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Optimización completa del rendimiento del POS: límites de carga, índices PostgreSQL y autovacuum",
    "description": """
        Módulo de Optimización Completa del Rendimiento del POS
        ========================================================

        Este módulo mejora significativamente el rendimiento del TPV en bases de datos
        con muchos productos (por ejemplo, 35.000+ productos) mediante múltiples estrategias:

        **1. Límites de Carga Inicial**
        --------------------------------
        * Configuración de límites para productos y clientes cargados al iniciar el POS
        * Parámetros ajustables desde Ajustes → Punto de venta
        * Valores por defecto: 500 productos y 500 clientes
        * Carga incremental bajo demanda para el resto

        **2. Optimizaciones PostgreSQL**
        --------------------------------
        * **Extensiones:**
          - pg_trgm: Búsquedas aproximadas de texto
          - unaccent: Búsquedas sin acentos

        * **Índices optimizados:**
          - Campos de productos (código de barras, referencia, nombre)
          - Filtros del POS (disponible en POS, activo, compañía)
          - Índice GIN trigram para búsquedas de texto en español
          - Nota: Solo en product_template (product_product hereda el nombre)

        * **Autovacuum personalizado:**
          - Mantenimiento automático optimizado de tablas de productos
          - Umbrales ajustados para mejor rendimiento
          - Menor impacto en operaciones en caliente

        **Beneficios:**
        ---------------
        * Arranque del POS hasta 10x más rápido en catálogos grandes
        * Búsquedas instantáneas por código de barras y referencia
        * Búsquedas de texto más rápidas (incluso sin acentos)
        * Mejor rendimiento general en todas las operaciones del POS
        * Mantenimiento automático de la base de datos

        **Características:**
        --------------------
        * Interfaz en español
        * Instalación automática de índices al instalar el módulo
        * Limpieza automática de índices al desinstalar
        * Compatible con Odoo 19.0 Community y Enterprise
        * Sin impacto en el código del POS (solo optimizaciones de BD)
    """,
    "author": "Xtendoo Software S.L.U.",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "product",
    ],
    "data": [
        # "data/ir_config_parameter_data.xml",  # Los parámetros se crean desde hooks.py
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}

