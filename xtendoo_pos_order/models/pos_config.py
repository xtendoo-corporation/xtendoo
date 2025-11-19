# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = "pos.config"

    interface_type = fields.Selection(
        selection=[
            ("frontend", "Standard POS Frontend"),
            ("backend", "Backend Orders Interface"),
        ],
        string="Interface Type",
        default="frontend",
        required=True,
        help="Determina cómo se gestionan las órdenes en este punto de venta:\n"
             "- Standard POS Frontend: Usa la interfaz JavaScript estándar del POS\n"
             "- Backend Orders Interface: Permite crear y gestionar órdenes desde el backend",
    )

    def open_ui(self):
        """
        Intercepta la apertura del POS para redirigir según el tipo de interfaz.

        Si interface_type == 'backend', en lugar de abrir el frontend JS del POS,
        abre una vista de árbol/formulario de pos.order filtrada por esta caja.

        Si interface_type == 'frontend', comportamiento estándar.
        """
        self.ensure_one()

        if self.interface_type == "backend":
            # Modo backend: abrir vista de órdenes POS
            return self._open_backend_orders_interface()

        # Modo frontend: comportamiento estándar
        return super().open_ui()

    def _open_backend_orders_interface(self):
        """
        Devuelve una acción que abre la vista de órdenes POS en modo backend.

        La vista permite:
        - Listar órdenes de POS de esta caja
        - Crear nuevas órdenes manualmente
        - Editar órdenes existentes
        """
        self.ensure_one()

        # Buscar sesión abierta para esta caja
        current_session = self.env["pos.session"].search(
            [("config_id", "=", self.id), ("state", "=", "opened")],
            limit=1,
        )

        # Si no hay sesión abierta, informar al usuario
        if not current_session:
            # Opción: podríamos auto-abrir una sesión aquí si es necesario
            # current_session = self.env["pos.session"].create({"config_id": self.id})
            # current_session.action_pos_session_open()
            pass

        return {
            "type": "ir.actions.act_window",
            "name": f"Órdenes POS - {self.name}",
            "res_model": "pos.order",
            "view_mode": "tree,form",
            "views": [
                (self.env.ref("point_of_sale.view_pos_order_tree").id, "tree"),
                (False, "form"),
            ],
            "domain": [("config_id", "=", self.id)],
            "context": {
                "default_config_id": self.id,
                "default_session_id": current_session.id if current_session else False,
                "search_default_config_id": self.id,
            },
            "target": "current",
        }

    def open_existing_session_cb(self):
        """
        Sobrescribe el método para abrir sesión existente.
        Aplica la misma lógica de redirección según interface_type.
        """
        self.ensure_one()

        if self.interface_type == "backend":
            return self._open_backend_orders_interface()

        return super().open_existing_session_cb()

