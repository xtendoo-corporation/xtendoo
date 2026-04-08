# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    # Campos relacionados con pos.config — bridge local (nuevos)
    # ------------------------------------------------------------------

    pos_cash_drawer_use_bridge = fields.Boolean(
        related="pos_config_id.cash_drawer_use_bridge",
        readonly=False,
        string="Usar bridge local para el cajón",
    )

    pos_cash_drawer_bridge_url = fields.Char(
        related="pos_config_id.cash_drawer_bridge_url",
        readonly=False,
        string="URL del bridge local",
    )

    pos_cash_drawer_printer_name = fields.Char(
        related="pos_config_id.cash_drawer_printer_name",
        readonly=False,
        string="Nombre de la impresora",
    )

    pos_cash_drawer_api_key = fields.Char(
        related="pos_config_id.cash_drawer_api_key",
        readonly=False,
        string="API Key del cajón",
    )

    pos_cash_drawer_auto_open = fields.Boolean(
        related="pos_config_id.cash_drawer_auto_open",
        readonly=False,
        string="Abrir cajón automáticamente en pagos en efectivo",
    )

    # ------------------------------------------------------------------
    # Campo legacy — mantenido por compatibilidad con instalaciones
    # anteriores que guardaban datos en cash_drawer_open_url
    # ------------------------------------------------------------------

    pos_cash_drawer_open_url = fields.Char(
        related="pos_config_id.cash_drawer_open_url",
        readonly=False,
        string="URL de apertura del cajón (legado)",
    )

    # ------------------------------------------------------------------
    # Acción de prueba
    # ------------------------------------------------------------------

    def action_test_cash_drawer(self):
        """Guarda los ajustes actuales y delega la prueba a pos.config."""
        self.execute()
        return self.pos_config_id.action_test_cash_drawer()
