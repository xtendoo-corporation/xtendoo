from odoo import models, fields, api
from odoo.exceptions import UserError


class ApplyPartnerDiscountsWizard(models.TransientModel):
    _name = 'apply.partner.discounts.wizard'
    _description = 'Wizard para aplicar descuentos del cliente'

    # Campos para pedidos de venta
    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta')

    # Campos para facturas
    account_move_id = fields.Many2one('account.move', string='Factura')

    # Campos comunes
    partner_id = fields.Many2one('res.partner', string='Cliente', compute='_compute_partner_id', store=True)
    discount_summary = fields.Html(string='Resumen de Descuentos', readonly=True)
    total_discount_amount = fields.Monetary(string='Total Descuento', readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id', store=True)
    base_amount = fields.Monetary(string='Importe Base', readonly=True, currency_field='currency_id')
    document_type = fields.Selection([
        ('sale_order', 'Pedido de Venta'),
        ('account_move', 'Factura')
    ], string='Tipo de Documento', compute='_compute_document_type', store=True)

    @api.depends('sale_order_id', 'account_move_id')
    def _compute_partner_id(self):
        for record in self:
            if record.sale_order_id:
                record.partner_id = record.sale_order_id.partner_id
            elif record.account_move_id:
                record.partner_id = record.account_move_id.partner_id
            else:
                record.partner_id = False

    @api.depends('sale_order_id', 'account_move_id')
    def _compute_currency_id(self):
        for record in self:
            if record.sale_order_id:
                record.currency_id = record.sale_order_id.currency_id
            elif record.account_move_id:
                record.currency_id = record.account_move_id.currency_id
            else:
                record.currency_id = False

    @api.depends('sale_order_id', 'account_move_id')
    def _compute_document_type(self):
        for record in self:
            if record.sale_order_id:
                record.document_type = 'sale_order'
            elif record.account_move_id:
                record.document_type = 'account_move'
            else:
                record.document_type = False

    @api.model
    def default_get(self, fields_list):
        """Cargar datos por defecto del documento activo"""
        defaults = super().default_get(fields_list)

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if not active_model or not active_id:
            return defaults

        # Manejar pedidos de venta
        if active_model == 'sale.order':
            sale_order = self.env['sale.order'].browse(active_id)
            defaults['sale_order_id'] = sale_order.id
            self._set_discount_defaults(defaults, sale_order, 'sale_order')

        # Manejar facturas
        elif active_model == 'account.move':
            account_move = self.env['account.move'].browse(active_id)
            defaults['account_move_id'] = account_move.id
            self._set_discount_defaults(defaults, account_move, 'account_move')

        return defaults

    def _set_discount_defaults(self, defaults, document, doc_type):
        """Establece los valores por defecto de descuentos para cualquier tipo de documento"""
        if document.partner_id and document.partner_id.has_global_discounts:
            base_amount = document._get_base_amount_for_partner_discounts()
            defaults['base_amount'] = base_amount

            if base_amount > 0:
                # Determinar el tipo de documento para los descuentos
                if doc_type == 'sale_order':
                    discount_doc_type = 'quotation' if document.state in ['draft', 'sent'] else 'sale_order'
                    doc_date = document.date_order.date() if document.date_order else None
                else:  # account_move
                    discount_doc_type = 'invoice'
                    doc_date = document.invoice_date or fields.Date.today()

                applicable_discounts = document.partner_id.get_applicable_discounts(
                    discount_doc_type, base_amount, doc_date
                )

                if applicable_discounts:
                    # Calcular resumen
                    total_discount = 0
                    discount_lines = []
                    temp_base = base_amount

                    for discount in applicable_discounts:
                        discount_amount = discount.calculate_discount_amount(temp_base)
                        total_discount += discount_amount
                        discount_lines.append({
                            'name': discount.name,
                            'type': 'Porcentaje' if discount.discount_type == 'percentage' else 'Importe Fijo',
                            'value': f"{discount.discount_value}%" if discount.discount_type == 'percentage' else f"{discount.discount_value} {document.currency_id.symbol}",
                            'amount': discount_amount,
                            'base': temp_base
                        })
                        temp_base -= discount_amount

                    defaults['total_discount_amount'] = total_discount

                    # Generar HTML del resumen
                    html_summary = self._generate_discount_summary_html(discount_lines, document.currency_id)
                    defaults['discount_summary'] = html_summary

    def _generate_discount_summary_html(self, discount_lines, currency):
        """Genera el HTML para mostrar el resumen de descuentos"""
        html = """
        <div style="margin: 10px 0;">
            <h4>Descuentos a aplicar:</h4>
            <table class="table table-sm table-striped">
                <thead>
                    <tr>
                        <th>Descuento</th>
                        <th>Tipo</th>
                        <th>Valor</th>
                        <th>Base</th>
                        <th>Importe</th>
                    </tr>
                </thead>
                <tbody>
        """

        for line in discount_lines:
            html += f"""
                <tr>
                    <td>{line['name']}</td>
                    <td>{line['type']}</td>
                    <td>{line['value']}</td>
                    <td>{line['base']:.2f} {currency.symbol}</td>
                    <td><strong>{line['amount']:.2f} {currency.symbol}</strong></td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """
        return html

    def action_apply_discounts(self):
        """Aplica los descuentos al pedido de venta o factura"""
        self.ensure_one()

        document = self.sale_order_id or self.account_move_id

        if not document:
            raise UserError('No se ha encontrado el pedido de venta o factura.')

        # Aplicar descuentos usando el método existente
        if not document.partner_id:
            raise UserError('Debe seleccionar un cliente antes de aplicar descuentos.')

        if not document.partner_id.has_global_discounts:
            raise UserError('Este cliente no tiene descuentos globales configurados.')

        # Calcular el subtotal base
        base_amount = document._get_base_amount_for_partner_discounts()

        if base_amount <= 0:
            raise UserError('No hay importe base para aplicar descuentos.')

        # Determinar el tipo de documento para los descuentos
        if self.sale_order_id:
            doc_type = 'quotation' if document.state in ['draft', 'sent'] else 'sale_order'
            doc_date = document.date_order.date() if document.date_order else None
        else:  # account_move_id
            doc_type = 'invoice'
            doc_date = document.invoice_date or fields.Date.today()

        # Obtener descuentos aplicables del cliente
        applicable_discounts = document.partner_id.get_applicable_discounts(
            doc_type, base_amount, doc_date
        )

        if not applicable_discounts:
            raise UserError('No hay descuentos aplicables para este documento.')

        # Limpiar descuentos anteriores del cliente
        document._remove_partner_discount_lines()

        # Aplicar cada descuento
        total_discount_applied = 0
        discount_details = []

        for discount in applicable_discounts:
            discount_amount = document._apply_partner_discount(discount, base_amount)
            total_discount_applied += discount_amount
            base_amount -= discount_amount

            discount_details.append({
                'name': discount.name,
                'amount': discount_amount,
                'type': discount.discount_type,
                'value': discount.discount_value
            })

        document.partner_global_discounts_applied = True

        # Registrar en el chatter
        self._log_discount_application(document, discount_details, total_discount_applied)

        # Retornar acción para recargar el formulario según el tipo de documento
        model_name = 'sale.order' if self.sale_order_id else 'account.move'

        return {
            'type': 'ir.actions.act_window',
            'res_model': model_name,
            'res_id': document.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_partner_global_discounts_applied': True,
            }
        }

    def _log_discount_application(self, document, discount_details, total_amount):
        """Registra la aplicación de descuentos en el chatter"""
        user_name = self.env.user.name
        currency_symbol = document.currency_id.symbol

        # Crear mensaje usando formato texto plano con saltos de línea
        message_parts = []
        message_parts.append(f"{user_name} ha aplicado descuentos del cliente por un total de {currency_symbol}{total_amount:.2f}")
        message_parts.append("")  # Línea vacía
        message_parts.append("Descuentos aplicados:")

        for discount in discount_details:
            discount_type_text = "Porcentaje" if discount['type'] == 'percentage' else "Importe Fijo"
            value_text = f"{discount['value']}%" if discount['type'] == 'percentage' else f"{currency_symbol}{discount['value']}"

            message_parts.append(f"• {discount['name']} ({discount_type_text}: {value_text}) - Descuento: {currency_symbol}{discount['amount']:.2f}")

        # Unir con saltos de línea
        message_body = "\n".join(message_parts)

        # Enviar mensaje al chatter
        document.message_post(
            body=message_body,
            subject="Descuentos del Cliente Aplicados",
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

    def action_cancel(self):
        """Cancela el wizard sin aplicar descuentos"""
        return {'type': 'ir.actions.act_window_close'}
