# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    cash_drawer_printer_name = fields.Char(
        string="Nombre de la impresora",
        help=(
            "Nombre exacto de la impresora conectada al cajón portamonedas. "
            "Debe coincidir con el nombre del dispositivo tal como aparece en el sistema "
            "operativo o en el servidor de impresión."
        ),
    )

    cash_drawer_open_url = fields.Char(
        string="URL de apertura del cajón",
        help=(
            "URL a la que se realiza la petición para enviar la orden de apertura "
            "del cajón portamonedas. "
            "Ejemplo: http://127.0.0.1:3210/open-drawer?printer=POS-80C"
        ),
    )

    cash_drawer_api_key = fields.Char(
        string="API Key del cajón",
        help=(
            "Clave de autenticación que se envía como cabecera 'x-api-key' "
            "y como parámetro '?x-api-key=...' al llamar a la URL de apertura."
        ),
    )

    cash_drawer_auto_open = fields.Boolean(
        string="Abrir cajón automáticamente en pagos en efectivo",
        default=True,
        help=(
            "Si está activo, el cajón se abrirá automáticamente cuando se valide "
            "un pedido con pago en efectivo en el TPV, siempre que haya una URL "
            "de apertura configurada."
        ),
    )

    def action_test_cash_drawer(self):
        """Devuelve una acción cliente que prueba la apertura del cajón
        ejecutando el fetch() desde el NAVEGADOR.

        Esto evita los problemas de red de Docker: cuando la URL apunta a
        127.0.0.1, el navegador la resuelve correctamente en el host,
        igual que el botón del TPV.
        """
        self.ensure_one()
        url = self.cash_drawer_open_url
        if not url:
            raise UserError(_("No hay URL configurada para el cajón portamonedas."))

        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_cash_drawer_open_test",
            "params": {
                "url": url,
                "api_key": self.cash_drawer_api_key or "",
            },
        }
