from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def default_get(self, fields_list):
        """Establecer valores por defecto al crear un pedido"""
        res = super().default_get(fields_list)

        # Si no hay compañía, usar la del usuario actual
        if 'company_id' not in res or not res.get('company_id'):
            res['company_id'] = self.env.company.id

        # Inicializar amount_return si no está presente
        if 'amount_return' not in res:
            res['amount_return'] = 0.0

        # Buscar sesión abierta del usuario
        session = self.env['pos.session'].search([
            ('user_id', '=', self.env.user.id),
            ('state', '=', 'opened')
        ], limit=1)

        if session:
            if 'session_id' not in res:
                res['session_id'] = session.id
            if 'config_id' not in res:
                res['config_id'] = session.config_id.id
            if 'pricelist_id' not in res:
                res['pricelist_id'] = session.config_id.pricelist_id.id
            if 'currency_id' not in res:
                res['currency_id'] = session.currency_id.id
        else:
            # Si no hay sesión, usar valores por defecto de la compañía
            company = self.env.company
            if 'currency_id' not in res:
                res['currency_id'] = company.currency_id.id
            if 'pricelist_id' not in res:
                # Buscar la lista de precios por defecto
                pricelist = self.env['product.pricelist'].search([
                    ('company_id', '=', company.id)
                ], limit=1)
                if pricelist:
                    res['pricelist_id'] = pricelist.id

        return res

    @api.onchange('session_id')
    def _onchange_session_id(self):
        """Establece datos básicos cuando se selecciona una sesión"""
        if self.session_id:
            if not self.company_id:
                self.company_id = self.session_id.config_id.company_id or self.env.company
            if not self.pricelist_id:
                self.pricelist_id = self.session_id.config_id.pricelist_id
            if not self.currency_id:
                self.currency_id = self.session_id.currency_id or self.pricelist_id.currency_id or self.company_id.currency_id

    def _compute_prices(self):
        """Sobrescribir para asegurar que la moneda esté configurada antes de calcular"""
        for order in self:
            # Asegurar que la moneda esté configurada antes de cualquier cálculo
            if not order.currency_id:
                if order.session_id and order.session_id.currency_id:
                    order.currency_id = order.session_id.currency_id
                elif order.pricelist_id and order.pricelist_id.currency_id:
                    order.currency_id = order.pricelist_id.currency_id
                elif order.company_id and order.company_id.currency_id:
                    order.currency_id = order.company_id.currency_id
                else:
                    order.currency_id = self.env.company.currency_id

        # Llamar al método padre que hace los cálculos reales
        return super()._compute_prices()


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

