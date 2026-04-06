# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_cash_drawer_printer_name = fields.Char(
        related="pos_config_id.cash_drawer_printer_name",
        readonly=False,
        string="Nombre de la impresora",
    )

    pos_cash_drawer_open_url = fields.Char(
        related="pos_config_id.cash_drawer_open_url",
        readonly=False,
        string="URL de apertura del cajón",
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

    def action_test_cash_drawer(self):
        """Guarda los ajustes actuales y devuelve la acción cliente de prueba."""
        self.execute()  # Persiste los valores antes de leer pos_config_id
        return self.pos_config_id.action_test_cash_drawer()
