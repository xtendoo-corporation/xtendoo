from odoo import fields, models, _


class PosConfig(models.Model):
    _inherit = "pos.config"

    pos_non_touch = fields.Boolean(
        string="POS no táctil",
        default=False,
        help="Activa un modo de punto de venta optimizado para equipos sin pantalla táctil.",
    )

    default_partner_id = fields.Many2one(
        "res.partner",
        string="Cliente por Defecto",
        help="Cliente que se asignará automáticamente a los nuevos pedidos POS creados desde el backend.",
        domain="[('customer_rank', '>', 0)]",
    )

    pos_enable_albaran = fields.Boolean(
        string="Albarán desde el POS",
        default=False,
        help="Permite crear albaranes desde el POS.",
    )

    pos_force_employee_login_after_order = fields.Boolean(
        string="Pedir PIN tras venta",
        default=False,
        help="Si está activo, pedirá el PIN del empleado después de cada venta y cambiará el usuario de la sesión.",
    )

    def open_ui(self):
        """
        Override del método open_ui para interceptar la apertura
        cuando pos_non_touch está activo.
        """
        self.ensure_one()

        # Si es modo no táctil, abrir wizard en lugar de la UI
        if self.pos_non_touch:
            # Si no hay sesión actual, crear una
            if not self.current_session_id:
                # Verificar antes de crear
                res = self._check_before_creating_new_session()
                if res:
                    return res

                # Crear la sesión con contexto especial para evitar que se abra automáticamente
                session = (
                    self.env["pos.session"]
                    .with_context(skip_auto_open=True)
                    .create({"user_id": self.env.uid, "config_id": self.id})
                )
            else:
                session = self.current_session_id

            # Verificar que session sea un recordset, no un dict
            if isinstance(session, dict):
                # Si es un dict, es una acción que debemos retornar
                return session

            # Si la sesión está en opening_control, abrir el wizard de PIN primero
            if session.state == "opening_control":
                return {
                    "type": "ir.actions.act_window",
                    "res_model": "pos.session.pin.wizard",
                    "view_mode": "form",
                    "target": "new",
                    "context": {
                        "default_session_id": session.id,
                        "default_user_id": self.env.uid,
                    },
                }

            # Si la sesión ya está abierta (Continue Selling),
            # redirigir a la vista de pedidos POS
            if session.state in ["opened", "closing_control"]:
                return self._redirect_to_pos_orders(session)

        # Para modo táctil normal, usar el comportamiento estándar
        return super(PosConfig, self).open_ui()

    def _redirect_to_pos_orders(self, session):

        self.ensure_one()

        # Obtener todas las sesiones de este config
        config_sessions = self.env["pos.session"].search(
            [("config_id", "=", session.config_id.id)]
        )

        # Obtener la acción estándar de pedidos POS de Odoo
        action = self.env.ref("point_of_sale.action_pos_pos_form").read()[0]

        # Filtrar por session_id para mostrar solo pedidos de sesiones de esta caja
        action["domain"] = [("session_id", "in", config_sessions.ids)]

        action["context"] = {
            "default_session_id": session.id,
        }

        return action
