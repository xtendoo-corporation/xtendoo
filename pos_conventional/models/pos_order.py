from odoo import models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_close_pos_session_wizard(self):
        """
        Abre el wizard para cerrar la sesión POS actual del usuario.
        Este método se llama desde el botón en la vista de pedidos.
        """
        # Buscar la sesión abierta del usuario actual
        session = self.env['pos.session'].search([
            ('user_id', '=', self.env.user.id),
            ('state', 'in', ['opened', 'closing_control'])
        ], limit=1)

        if not session:
            raise UserError(_('No tienes ninguna sesión abierta.'))

        # Validar que sea caja no táctil
        if not session.config_id.pos_non_touch:
            raise UserError(_('Esta función solo está disponible para cajas en modo no táctil.'))

        # Crear el wizard de cierre
        wizard = self.env['pos.session.closing.wizard'].create({
            'session_id': session.id,
            'cash_register_balance_end_real': session.cash_register_balance_end,
        })

        # Retornar la acción para mostrar el wizard
        return {
            'name': _('Cerrar caja - Modo no táctil'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.session.closing.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
            'context': dict(self.env.context),
        }

