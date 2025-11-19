# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Se ejecuta tras instalar el módulo.

    Configura valores por defecto y muestra información útil.
    """
    _logger.info("=" * 70)
    _logger.info("XTENDOO POS ORDER BACKEND: Módulo instalado correctamente")
    _logger.info("=" * 70)
    _logger.info("")
    _logger.info("CONFIGURACIÓN:")
    _logger.info("  1. Vaya a: Punto de Venta → Configuración → Puntos de Venta")
    _logger.info("  2. Seleccione un Punto de Venta")
    _logger.info("  3. En 'Interface Configuration', elija:")
    _logger.info("     • Backend Orders Interface (para gestión desde backend)")
    _logger.info("     • Standard POS Frontend (para interfaz JS tradicional)")
    _logger.info("")
    _logger.info("USO:")
    _logger.info("  • Modo Backend: Permite crear órdenes POS manualmente")
    _logger.info("  • Modo Frontend: Usa la interfaz JavaScript estándar")
    _logger.info("")
    _logger.info("DOCUMENTACIÓN:")
    _logger.info("  • README.md: Descripción general del módulo")
    _logger.info("  • INSTALL.md: Guía completa de instalación y uso")
    _logger.info("")
    _logger.info("=" * 70)


def uninstall_hook(env):
    """
    Se ejecuta al desinstalar el módulo.

    Informa al usuario sobre los datos que permanecen.
    """
    _logger.info("=" * 70)
    _logger.info("XTENDOO POS ORDER BACKEND: Módulo desinstalado")
    _logger.info("=" * 70)
    _logger.info("")
    _logger.info("NOTA:")
    _logger.info("  • Las órdenes POS creadas se mantienen en el sistema")
    _logger.info("  • La configuración 'interface_type' se mantiene en pos.config")
    _logger.info("  • Los datos no se pierden al desinstalar el módulo")
    _logger.info("")
    _logger.info("=" * 70)

