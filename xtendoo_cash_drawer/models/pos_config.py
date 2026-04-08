# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Modelo pos.config extendido para la configuración del cajón portamonedas.

Arquitectura: frontend POS → bridge local
-----------------------------------------
La apertura del cajón se realiza directamente desde el navegador del TPV
mediante fetch() al bridge local (por defecto http://127.0.0.1:3211).
Odoo no actúa como proxy: no se realizan peticiones Python al cajón.

Campos:
    cash_drawer_use_bridge     – Habilita la integración con el bridge local.
    cash_drawer_bridge_url     – URL base del bridge (p.ej. http://127.0.0.1:3211).
    cash_drawer_printer_name   – Nombre de la impresora pasado como parámetro al bridge.
    cash_drawer_api_key        – API key enviada como cabecera x-api-key al bridge.
    cash_drawer_auto_open      – Abre el cajón automáticamente en pagos en efectivo.

Campo legacy:
    cash_drawer_open_url       – Mantenido por compatibilidad con instalaciones
                                 anteriores. Si está relleno y cash_drawer_bridge_url
                                 está vacío, el JS del POS lo usará como fallback.
                                 Se recomienda migrar a cash_drawer_bridge_url.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    # ------------------------------------------------------------------
    # Configuración principal del bridge local
    # ------------------------------------------------------------------

    cash_drawer_use_bridge = fields.Boolean(
        string="Usar bridge local para el cajón",
        default=False,
        help=(
            "Activa la integración con el bridge local del cajón portamonedas. "
            "El bridge debe estar ejecutándose en el PC del cajero o en la LAN local."
        ),
    )

    cash_drawer_bridge_url = fields.Char(
        string="URL del bridge local",
        default="http://127.0.0.1:3211",
        help=(
            "URL base del bridge local del cajón portamonedas. "
            "Por defecto el bridge escucha en http://127.0.0.1:3211. "
            "Si el bridge está en otro equipo de la LAN, introduce su IP: "
            "por ejemplo http://192.168.1.50:3211. "
            "La petición de apertura se construirá añadiendo /open-drawer?printer=<nombre>."
        ),
    )

    cash_drawer_printer_name = fields.Char(
        string="Nombre de la impresora",
        help=(
            "Nombre exacto de la impresora conectada al cajón portamonedas. "
            "Se envía al bridge como parámetro printer= en la URL. "
            "Debe coincidir con el nombre de dispositivo reconocido por el bridge, "
            "por ejemplo: POS-80C, EPSON TM-T20III, STAR TSP100."
        ),
    )

    cash_drawer_api_key = fields.Char(
        string="API Key del cajón",
        help=(
            "Clave de autenticación enviada al bridge como cabecera HTTP 'x-api-key'. "
            "Déjalo en blanco si el bridge no requiere autenticación."
        ),
    )

    cash_drawer_auto_open = fields.Boolean(
        string="Abrir cajón automáticamente en pagos en efectivo",
        default=True,
        help=(
            "Si está activo, el cajón se abrirá automáticamente cuando se valide "
            "un pedido con pago en efectivo en el TPV, siempre que el bridge esté "
            "configurado y activo."
        ),
    )

    # ------------------------------------------------------------------
    # Campo legacy — mantenido por compatibilidad
    # ------------------------------------------------------------------

    cash_drawer_open_url = fields.Char(
        string="URL de apertura del cajón (legado)",
        help=(
            "[OBSOLETO] Campo mantenido por compatibilidad con instalaciones anteriores "
            "que usaban el proxy backend de Odoo. "
            "Usa 'URL del bridge local' (cash_drawer_bridge_url) en su lugar. "
            "Si cash_drawer_bridge_url está vacío y este campo tiene valor, "
            "el JS del POS lo utilizará como fallback automático."
        ),
    )

    # ------------------------------------------------------------------
    # Cómputo automático de la URL efectiva del bridge
    # ------------------------------------------------------------------

    @api.depends("cash_drawer_bridge_url", "cash_drawer_open_url")
    def _compute_effective_bridge_url(self):
        """Devuelve la URL activa: bridge_url si existe, open_url como fallback."""
        for rec in self:
            rec.cash_drawer_effective_url = (
                rec.cash_drawer_bridge_url or rec.cash_drawer_open_url or ""
            )

    cash_drawer_effective_url = fields.Char(
        string="URL efectiva del bridge (calculada)",
        compute="_compute_effective_bridge_url",
        store=False,
        help="URL que usará el JS del POS para abrir el cajón (bridge_url o open_url como fallback).",
    )

    # ------------------------------------------------------------------
    # Acción de prueba
    # ------------------------------------------------------------------

    def action_test_cash_drawer(self):
        """Devuelve una acción cliente que prueba la apertura del cajón
        ejecutando fetch() DESDE EL NAVEGADOR del usuario.

        La petición va directamente al bridge local configurado, sin pasar
        por el backend Python. Esto garantiza que la prueba usa el mismo
        canal de red que el TPV real.
        """
        self.ensure_one()
        effective_url = self.cash_drawer_effective_url
        if not effective_url:
            raise UserError(
                _(
                    "No hay URL del bridge local configurada para el cajón portamonedas. "
                    "Rellena el campo 'URL del bridge local' en la configuración de este TPV."
                )
            )

        return {
            "type": "ir.actions.client",
            "tag": "xtendoo_cash_drawer_open_test",
            "params": {
                "bridge_url": self.cash_drawer_bridge_url or "",
                "printer_name": self.cash_drawer_printer_name or "",
                "api_key": self.cash_drawer_api_key or "",
            },
        }
