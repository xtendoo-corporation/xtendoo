from odoo import fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_non_touch = fields.Boolean(
        string='POS no táctil',
        default=False,
        help='Activa un modo de punto de venta optimizado para equipos sin pantalla táctil.'
    )

    default_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente por Defecto',
        help='Cliente que se asignará automáticamente a los nuevos pedidos POS creados desde el backend.',
        domain="[('customer_rank', '>', 0)]",
    )

    pos_enable_albaran = fields.Boolean(
        string='Albarán desde el POS',
        default=False,
        help='Permite crear albaranes desde el POS.'
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
                session = self.env['pos.session'].with_context(skip_auto_open=True).create({
                    'user_id': self.env.uid,
                    'config_id': self.id
                })
            else:
                session = self.current_session_id

            # Verificar que session sea un recordset, no un dict
            if isinstance(session, dict):
                # Si es un dict, es una acción que debemos retornar
                return session

            # Si la sesión está en opening_control, abrir el wizard de PIN primero
            if session.state == 'opening_control':
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'pos.session.pin.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_session_id': session.id,
                        'default_user_id': self.env.uid,
                    }
                }

            # Si la sesión ya está abierta (Continue Selling),
            # redirigir a la vista de pedidos POS
            if session.state in ['opened', 'closing_control']:
                return self._redirect_to_pos_orders(session)

        # Para modo táctil normal, usar el comportamiento estándar
        return super(PosConfig, self).open_ui()

    def _redirect_to_pos_orders(self, session):
        """
        Redirige a la vista de pedidos POS para la caja (config_id).
        Muestra TODOS los pedidos de esta caja, no solo de la sesión actual,
        para permitir devoluciones de pedidos anteriores.
        Reutiliza la acción estándar de Odoo.
        """
        self.ensure_one()

        # Obtener la acción estándar de pedidos POS de Odoo
        action = self.env.ref('point_of_sale.action_pos_pos_form').read()[0]

        # Filtrar por config_id para mostrar TODOS los pedidos de esta caja
        # (no solo de la sesión actual, para permitir devoluciones)
        action['domain'] = [('config_id', '=', session.config_id.id)]
        action['context'] = {
            'default_session_id': session.id,
            'default_config_id': session.config_id.id,
        }

        return action
