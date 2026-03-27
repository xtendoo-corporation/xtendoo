# -*- coding: utf-8 -*-
{
    "name": "Cash Drawer Settings",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Apertura del cajón portamonedas desde el menú de Ajustes",
    "description": """
        Añade una sección en Ajustes para configurar y abrir el cajón portamonedas.
        Características:
        * Configuración de la ruta del dispositivo o nombre de impresora CUPS.
        * Botón de apertura que envía el comando ESC/POS (bytes 27, 105) directamente
          al dispositivo (/dev/usb/lp0, etc.) o mediante el comando ``lpr``.
        * Notificación de éxito / error en pantalla.
    """,
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["base_setup"],
    "data": [
        "views/cash_drawer_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
