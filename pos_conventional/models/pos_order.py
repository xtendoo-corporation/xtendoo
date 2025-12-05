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

        # Buscar sesión abierta del usuario o usar la del contexto
        session_id = self.env.context.get('default_session_id')
        if session_id:
            session = self.env['pos.session'].browse(session_id)
        else:
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

            # Establecer cliente por defecto si está configurado y no hay uno ya establecido
            if 'partner_id' in fields_list and not res.get('partner_id'):
                if session.config_id.default_partner_id:
                    res['partner_id'] = session.config_id.default_partner_id.id
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

    def write(self, vals):
        """
        Override write para asegurar que los impuestos persistan correctamente.

        Cuando se guarda un pedido POS desde el backend, se asegura que tax_ids
        esté sincronizado con tax_ids_after_fiscal_position antes del guardado.
        """
        # Sincronizar tax_ids antes del guardado para líneas que lo necesiten
        for order in self:
            for line in order.lines:
                if line.tax_ids_after_fiscal_position and not line.tax_ids:
                    line.with_context(skip_inverse=True).write({
                        'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids)]
                    })

        return super().write(vals)

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

    def add_product_by_barcode(self, barcode):
        """
        Añade un producto al pedido POS mediante lectura de código de barras.

        Este método es llamado desde el frontend cuando se escanea un código de barras
        en el formulario del pedido POS (backend).

        :param barcode: Código de barras escaneado
        :return: Dict con resultado de la operación
        """
        self.ensure_one()

        # Validar que el pedido esté en borrador
        if self.state != 'draft':
            return {
                'success': False,
                'message': _('Cannot add products to a validated order')
            }

        # Buscar producto por código de barras
        product = self.env['product.product'].search([
            ('barcode', '=', barcode),
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)
        ], limit=1)

        # Fallback: buscar por referencia interna
        if not product:
            product = self.env['product.product'].search([
                ('default_code', '=', barcode),
                '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)
            ], limit=1)

        if not product:
            return {
                'success': False,
                'message': _('Product not found with barcode: %s', barcode)
            }

        # Verificar que el producto pueda venderse
        if not product.sale_ok:
            return {
                'success': False,
                'message': _('Product "%s" cannot be sold', product.name)
            }

        # Obtener precio del producto según la tarifa del pedido
        pricelist = self.pricelist_id
        if pricelist:
            price = pricelist._get_product_price(
                product,
                1.0,
                uom=product.uom_id
            )
        else:
            price = product.lst_price

        # Obtener impuestos del producto
        taxes = product.taxes_id.filtered(
            lambda t: t.company_id == self.company_id
        )

        # Aplicar posición fiscal si existe
        if self.fiscal_position_id:
            taxes = self.fiscal_position_id.map_tax(taxes)

        # Buscar si ya existe una línea con este producto
        existing_line = self.lines.filtered(
            lambda l: l.product_id == product and not l.refunded_orderline_id
        )

        if existing_line:
            # Si existe, incrementar cantidad
            existing_line = existing_line[0]
            existing_line.qty += 1
            action = _('Quantity increased')
        else:
            # Si no existe, crear nueva línea
            self.env['pos.order.line'].create({
                'order_id': self.id,
                'product_id': product.id,
                'qty': 1,
                'price_unit': price,
                'tax_ids': [(6, 0, taxes.ids)],
                'full_product_name': product.display_name,
            })
            action = _('Product added')

        return {
            'success': True,
            'product_name': product.name,
            'action': action,
        }

