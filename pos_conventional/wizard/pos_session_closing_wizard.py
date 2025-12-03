from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSessionClosingWizard(models.TransientModel):
    _name = 'pos.session.closing.wizard'
    _description = 'Wizard para cierre de sesión POS no táctil'

    session_id = fields.Many2one('pos.session', string='Sesión', required=True, readonly=True)
    cash_register_balance_end_real = fields.Monetary(
        string='Dinero contado en caja',
        currency_field='currency_id',
        help='Cantidad total de dinero en efectivo contado al cerrar la caja',
        required=True
    )
    currency_id = fields.Many2one('res.currency', related='session_id.currency_id', readonly=True)
    cash_control = fields.Boolean(related='session_id.cash_control', readonly=True)
    cash_register_balance_start = fields.Monetary(
        string='Dinero inicial',
        related='session_id.cash_register_balance_start',
        readonly=True
    )
    cash_register_balance_end = fields.Monetary(
        string='Dinero teórico',
        related='session_id.cash_register_balance_end',
        readonly=True,
        help='Dinero inicial + ventas en efectivo - devoluciones'
    )
    cash_register_difference = fields.Monetary(
        string='Diferencia',
        compute='_compute_difference',
        store=True,
        help='Diferencia entre dinero contado y dinero teórico'
    )
    closing_note = fields.Text(
        string='Motivo del cierre',
        help='Nota opcional explicando el motivo del cierre de la sesión'
    )

    @api.depends('cash_register_balance_end_real', 'cash_register_balance_end')
    def _compute_difference(self):
        for wizard in self:
            wizard.cash_register_difference = wizard.cash_register_balance_end_real - wizard.cash_register_balance_end

    def action_close_session(self):
        """
        Cierra la sesión POS usando los métodos estándares de Odoo.
        Reutiliza completamente la lógica del core.
        """
        self.ensure_one()

        # Validar que la sesión esté en estado abierto
        if self.session_id.state not in ['opened', 'closing_control']:
            raise UserError(_(
                'Solo puedes cerrar sesiones en estado abierto o en proceso de cierre.'
            ))

        # Si hay control de efectivo, guardar el dinero contado
        if self.session_id.cash_control:
            # Usar el método estándar de Odoo para registrar el efectivo contado
            result = self.session_id.post_closing_cash_details(self.cash_register_balance_end_real)
            if not result.get('successful'):
                raise UserError(result.get('message', _('Error al registrar el efectivo.')))

        # Guardar la nota de cierre si existe
        if self.closing_note:
            self.session_id.message_post(
                body=_('Motivo de cierre: %s') % self.closing_note,
                subject=_('Nota de cierre de sesión')
            )

        # Llamar al método estándar de cierre de sesión
        # Este método hace toda la lógica: asientos contables, validaciones, etc.
        try:
            result = self.session_id.action_pos_session_closing_control()

            # Si el resultado es un diccionario, puede ser un wizard de desbalance
            if isinstance(result, dict):
                # Retornar el wizard de desbalance si es necesario
                return result

        except UserError as e:
            raise UserError(_(
                'Error al cerrar la sesión: %s'
            ) % str(e))

        # Retornar a la vista kanban de configuraciones POS
        return {
            'type': 'ir.actions.act_window',
            'name': _('Punto de Venta'),
            'res_model': 'pos.config',
            'view_mode': 'kanban,form',
            'target': 'main',
            'domain': [],
            'context': {
                'search_default_group_by_company': True,
            },
        }
