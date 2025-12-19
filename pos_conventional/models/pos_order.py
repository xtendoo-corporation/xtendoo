import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def get_product_line_data_by_barcode(self, barcode, pricelist_id=False, fiscal_position_id=False, partner_id=False):
        """
        Busca un producto por código de barras y devuelve los datos necesarios
        para crear una línea de pedido POS.

        Este método es llamado desde JavaScript para obtener todos los datos
        necesarios antes de crear la línea en el cliente.

        Args:
            barcode: Código de barras a buscar
            pricelist_id: ID de la lista de precios del pedido
            fiscal_position_id: ID de la posición fiscal del pedido
            partner_id: ID del cliente del pedido

        Returns:
            dict: Datos del producto y valores para la línea
        """
        # Buscar producto por código de barras
        Product = self.env['product.product']
        product = Product.search([('barcode', '=', barcode)], limit=1)

        # Fallback: buscar por referencia interna (default_code)
        if not product:
            product = Product.search([('default_code', '=', barcode)], limit=1)

        if not product:
            return {
                'success': False,
                'message': _("No se encontró ningún producto con el código: %s") % barcode
            }

        # Obtener precio desde la lista de precios
        price_unit = product.lst_price
        if pricelist_id:
            pricelist = self.env['product.pricelist'].browse(pricelist_id)
            partner = self.env['res.partner'].browse(partner_id) if partner_id else False
            price_unit = pricelist._get_product_price(
                product,
                1.0,
                partner=partner,
                uom=product.uom_id
            )

        # Obtener impuestos aplicables
        taxes = product.taxes_id.filtered(
            lambda t: t.company_id == self.env.company
        )

        # Aplicar posición fiscal si existe
        if fiscal_position_id:
            fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position_id)
            taxes = fiscal_position.map_tax(taxes)

        return {
            'success': True,
            'product': {
                'id': product.id,
                'display_name': product.display_name,
            },
            'line_vals': {
                'full_product_name': product.display_name,
                'qty': 1.0,
                'price_unit': price_unit,
                'tax_ids': taxes.ids,
            }
        }

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

    def action_validate_and_invoice(self):
        """
        Valida el pedido POS y crea la factura desde el backend (no táctil).
        Retorna una acción especial que el JavaScript interceptará para imprimir el ticket.
        """
        self.ensure_one()

        # Validaciones previas
        if self.state not in ['draft', 'paid']:
            raise UserError(_('Solo se pueden validar pedidos en estado borrador o pagado.'))

        if not self.lines:
            raise UserError(_('No se puede validar un pedido sin líneas de producto.'))

        if not self.payment_ids:
            raise UserError(_('No se puede validar un pedido sin pagos registrados.'))

        if not self.config_id.invoice_journal_id:
            raise UserError(_('No hay un diario de facturación configurado para este punto de venta.'))

        # Verificar que el pedido esté pagado
        if not self._is_pos_order_paid():
            raise UserError(_('El pedido no está completamente pagado. Faltan %.2f %s') % (
                self.amount_total - self.amount_paid,
                self.currency_id.symbol
            ))

        # Si ya tiene factura, no crear otra
        if self.account_move:
            raise UserError(_('Este pedido ya tiene una factura asociada: %s') % self.account_move.name)

        # Marcar para facturar
        self.write({'to_invoice': True})

        # Si el pedido está en draft, marcarlo como pagado
        if self.state == 'draft':
            try:
                self.action_pos_order_paid()
            except Exception as e:
                _logger.exception("Error al marcar pedido como pagado: %s", str(e))
                raise UserError(_('Error al validar el pedido: %s') % str(e))

        # Crear picking si es necesario (para contabilidad anglosajona)
        if self.company_id.anglo_saxon_accounting and self.session_id.update_stock_at_closing and self.session_id.state != 'closed':
            self._create_order_picking()

        # Generar la factura usando el método oficial de Odoo POS
        try:
            invoice = self._generate_pos_order_invoice()
            _logger.info(
                "POS Order %s: Factura %s creada correctamente desde backend",
                self.name, invoice.name
            )
        except Exception as e:
            _logger.exception("Error al generar factura: %s", str(e))
            raise UserError(_('Error al generar la factura: %s') % str(e))

        # Retornar acción especial para que JS imprima el ticket POS
        return True


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

    def add_product_by_barcode(self, barcode=None, product_id=None, line_vals=None):
        """
        Añade un producto al pedido POS mediante código de barras o product_id.

        Este método es llamado desde el controlador JavaScript cuando
        se detecta un escaneo de código de barras.

        Args:
            barcode: Código de barras escaneado (opcional si se pasa product_id)
            product_id: ID del producto a añadir (opcional si se pasa barcode)
            line_vals: Valores precalculados para la línea (opcional)

        Returns:
            dict: Resultado de la operación con 'success' y 'message'
        """
        self.ensure_one()

        if self.state != 'draft':
            return {
                'success': False,
                'message': _("No se pueden añadir productos a un pedido que no está en borrador.")
            }

        Product = self.env['product.product']

        # Obtener el producto por ID o por código de barras
        if product_id:
            product = Product.browse(product_id)
            if not product.exists():
                return {
                    'success': False,
                    'message': _("Producto no encontrado con ID: %s") % product_id
                }
        elif barcode:
            # Buscar producto por código de barras
            product = Product.search([('barcode', '=', barcode)], limit=1)
            # Fallback: buscar por referencia interna (default_code)
            if not product:
                product = Product.search([('default_code', '=', barcode)], limit=1)
            if not product:
                return {
                    'success': False,
                    'message': _("No se encontró ningún producto con el código: %s") % barcode
                }
        else:
            return {
                'success': False,
                'message': _("Debe proporcionar un código de barras o ID de producto.")
            }


        # Buscar si ya existe una línea con este producto para incrementar cantidad
        existing_line = self.lines.filtered(lambda l: l.product_id.id == product.id)

        if existing_line:
            # Incrementar cantidad en la línea existente
            line = existing_line[0]
            new_qty = line.qty + 1

            # Obtener precio con descuento
            price_unit = line.price_unit
            discount = line.discount or 0.0
            price = price_unit * (1 - discount / 100.0)

            # Usar tax_ids_after_fiscal_position si existe, sino tax_ids
            taxes = line.tax_ids_after_fiscal_position or line.tax_ids

            # Calcular subtotales
            price_subtotal = price * new_qty
            price_subtotal_incl = price * new_qty

            if taxes:
                tax_results = taxes.compute_all(
                    price,
                    currency=self.currency_id,
                    quantity=new_qty,
                    product=product,
                    partner=self.partner_id,
                )
                price_subtotal = tax_results['total_excluded']
                price_subtotal_incl = tax_results['total_included']

            line.write({
                'qty': new_qty,
                'price_subtotal': price_subtotal,
                'price_subtotal_incl': price_subtotal_incl,
            })

            # Forzar recálculo de totales del pedido (ejecuta el compute)
            self._compute_prices()

            _logger.info(
                "POS Order %s: Incrementada cantidad del producto %s a %s",
                self.name, product.display_name, new_qty
            )
            return {
                'success': True,
                'message': _("Cantidad actualizada: %s x %s") % (new_qty, product.display_name)
            }

        # Crear nueva línea de pedido
        try:
            line_vals = self._prepare_order_line_vals(product)
            new_line = self.env['pos.order.line'].create(line_vals)

            # Ejecutar onchange de la línea para calcular subtotales
            new_line._onchange_qty()

            # Forzar recálculo de totales del pedido (ejecuta el compute)
            self._compute_prices()

            _logger.info(
                "POS Order %s: Añadido producto %s mediante escaneo de código de barras",
                self.name, product.display_name
            )

            return {
                'success': True,
                'message': _("Añadido: %s") % product.display_name
            }

        except Exception as e:
            _logger.exception("Error al añadir producto por código de barras: %s", str(e))
            return {
                'success': False,
                'message': _("Error al añadir el producto: %s") % str(e)
            }

    def _prepare_order_line_vals(self, product, qty=1.0):
        """
        Prepara los valores para crear una línea de pedido POS.

        Reutiliza la lógica de precios y taxes del sistema.

        Args:
            product: Producto a añadir
            qty: Cantidad (por defecto 1.0)

        Returns:
            dict: Valores para crear la línea
        """
        self.ensure_one()

        # Obtener precio desde la lista de precios
        pricelist = self.pricelist_id or self.config_id.pricelist_id
        if pricelist:
            price_unit = pricelist._get_product_price(
                product,
                qty,
                partner=self.partner_id,
                uom=product.uom_id
            )
        else:
            price_unit = product.lst_price

        # Obtener impuestos aplicables del producto
        product_taxes = product.taxes_id.filtered(
            lambda t: t.company_id == self.company_id
        )

        # Aplicar posición fiscal si existe
        taxes_after_fp = product_taxes
        if self.fiscal_position_id:
            taxes_after_fp = self.fiscal_position_id.map_tax(product_taxes)

        # Calcular subtotales (sin descuento por ahora)
        price = price_unit  # precio sin descuento
        price_subtotal = price * qty
        price_subtotal_incl = price * qty

        if taxes_after_fp:
            tax_results = taxes_after_fp.compute_all(
                price,
                currency=self.currency_id,
                quantity=qty,
                product=product,
                partner=self.partner_id,
            )
            price_subtotal = tax_results['total_excluded']
            price_subtotal_incl = tax_results['total_included']

        return {
            'order_id': self.id,
            'product_id': product.id,
            'full_product_name': product.display_name,
            'qty': qty,
            'price_unit': price_unit,
            'discount': 0.0,
            'price_subtotal': price_subtotal,
            'price_subtotal_incl': price_subtotal_incl,
            'tax_ids': [(6, 0, product_taxes.ids)],
        }

    def action_print_factura_simplificada(self):
        self.ensure_one()
        if not self.account_move:
            return

        return self.env.ref(
            "pos_conventional.action_factura_simplificada_80mm"
        ).report_action(self.account_move)


