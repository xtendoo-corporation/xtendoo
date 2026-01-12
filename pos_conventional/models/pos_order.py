import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    state = fields.Selection(
        selection_add=[('linked', 'Vinculado a Venta')],
        ondelete={'linked': 'set default'}
    )

    linked_sale_order_id = fields.Many2one(
        'sale.order',
        string="Pedido de venta vinculado",
        readonly=True,
        copy=False,
        help="Pedido de venta tradicional creado desde este pedido POS"
    )

    is_linked_to_sale = fields.Boolean(
        string="Vinculado a venta",
        compute="_compute_is_linked_to_sale",
        store=True,
        help="Indica si este pedido POS está vinculado a un pedido de venta tradicional"
    )

    show_albaran_button = fields.Boolean(
        string="Mostrar botón albarán",
        compute="_compute_show_albaran_button",
        store=False
    )

    has_order_lines = fields.Boolean(
        string="Tiene líneas de pedido",
        compute="_compute_has_order_lines",
        store=False
    )

    amount_untaxed = fields.Monetary(
        string="Importe base",
        compute="_compute_amount_untaxed",
        store=False,
        help="Subtotal sin impuestos calculado desde las líneas del pedido"
    )

    @api.depends('lines.price_subtotal', 'is_refund')
    def _compute_amount_untaxed(self):
        """Calcula el subtotal sin impuestos sumando price_subtotal de todas las líneas"""
        for order in self:
            sign = -1 if order.is_refund else 1
            amount_untaxed = sum(line.price_subtotal for line in order.lines)
            if order.currency_id:
                amount_untaxed = order.currency_id.round(amount_untaxed)
            order.amount_untaxed = amount_untaxed * sign

    @api.depends('linked_sale_order_id')
    def _compute_is_linked_to_sale(self):
        """Calcula si el pedido está vinculado a un sale.order"""
        for order in self:
            order.is_linked_to_sale = bool(order.linked_sale_order_id)

    @api.depends('session_id', 'session_id.config_id', 'session_id.config_id.pos_enable_albaran')
    def _compute_show_albaran_button(self):
        for order in self:
            order.show_albaran_button = bool(
                order.session_id
                and order.session_id.config_id
                and order.session_id.config_id.pos_enable_albaran
            )

    @api.depends('lines')
    def _compute_has_order_lines(self):
        """Verifica si el pedido tiene líneas"""
        for order in self:
            order.has_order_lines = bool(order.lines)

    def open_linked_sale_order(self):
        """
        Abre el sale.order vinculado en lugar del pos.order.
        Este método se usa cuando se hace clic en una fila de la lista.
        """
        self.ensure_one()
        if self.linked_sale_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.linked_sale_order_id.id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
            }
        # Si no tiene sale.order vinculado, abrir el pos.order normalmente
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }


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

        # SOLO usar la sesión si viene explícitamente en el contexto
        # NO buscar automáticamente sesiones porque puede causar que pedidos
        # de cajas táctiles se asignen incorrectamente a cajas no táctiles
        session_id = self.env.context.get('default_session_id')
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            if session.exists():
                if 'session_id' not in res:
                    res['session_id'] = session.id
                # NO asignar config_id aquí, dejar que se compute desde session_id
                if 'pricelist_id' not in res:
                    res['pricelist_id'] = session.config_id.pricelist_id.id
                if 'currency_id' not in res:
                    res['currency_id'] = session.currency_id.id

                # Establecer cliente por defecto si está configurado y no hay uno ya establecido
                if 'partner_id' in fields_list and not res.get('partner_id'):
                    if session.config_id.default_partner_id:
                        res['partner_id'] = session.config_id.default_partner_id.id
        else:
            # Si no hay sesión en el contexto, usar valores por defecto de la compañía
            # pero NO buscar sesiones automáticamente para evitar asignaciones incorrectas
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

        if self.config_id.iface_print_auto:
            # Construir la URL del informe HTML y devolver una acción cliente
            report_xmlid = 'pos_conventional.report_factura_simplificada_80mm'
            url = f"/report/html/{report_xmlid}/{invoice.id}"
            return {
                'type': 'ir.actions.client',
                'tag': 'pos_conventional.print_iframe',
                'params': {'url': url},
            }

        return True

    def action_close_pos_session_wizard(self):
        """
        Abre el wizard para cerrar la sesión POS actual del usuario.
        Este método se llama desde el botón en la vista de pedidos.

        La sesión se determina en este orden de prioridad:
        1. session_id del contexto (pasado desde la vista)
        2. session_id del pedido actual (si se llama desde un pedido específico)
        3. Buscar sesión abierta del usuario en un POS no táctil
        """
        session = None

        # 1. Intentar obtener la sesión del contexto
        session_id = self.env.context.get('default_session_id') or self.env.context.get('session_id')
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            if not session.exists() or session.state not in ['opened', 'closing_control']:
                session = None

        # 2. Si no hay contexto, intentar obtener del pedido actual
        if not session and self:
            order = self[0] if len(self) > 0 else None
            if order and order.session_id and order.session_id.state in ['opened', 'closing_control']:
                session = order.session_id

        # 3. Si aún no hay sesión, buscar una sesión de POS no táctil del usuario
        if not session:
            session = self.env['pos.session'].search([
                ('user_id', '=', self.env.user.id),
                ('state', 'in', ['opened', 'closing_control']),
                ('config_id.pos_non_touch', '=', True),  # Solo POS no táctil
            ], limit=1, order='id desc')

        if not session:
            raise UserError(_('No tienes ninguna sesión abierta en un punto de venta no táctil.'))

        # Validar que sea caja no táctil (por seguridad)
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

    def action_cash_in_out_wizard(self):
        """
        Abre un wizard o formulario para registrar una entrada/salida de efectivo
        en la sesión POS actual del usuario.

        La sesión se determina en este orden de prioridad:
        1. session_id del contexto (pasado desde la vista)
        2. session_id del pedido actual (si se llama desde un pedido específico)
        3. Buscar sesión abierta del usuario en un POS no táctil
        """
        session = None

        # 1. Intentar obtener la sesión del contexto
        session_id = self.env.context.get('default_session_id') or self.env.context.get('session_id')
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            if not session.exists() or session.state != 'opened':
                session = None

        # 2. Si no hay contexto, intentar obtener del pedido actual
        if not session and self:
            order = self[0] if len(self) > 0 else None
            if order and order.session_id and order.session_id.state == 'opened':
                session = order.session_id

        # 3. Si aún no hay sesión, buscar una sesión de POS no táctil del usuario
        if not session:
            session = self.env['pos.session'].search([
                ('user_id', '=', self.env.user.id),
                ('state', '=', 'opened'),
                ('config_id.pos_non_touch', '=', True),  # Solo POS no táctil
            ], limit=1, order='id desc')

        if not session:
            raise UserError(_('No tienes ninguna sesión abierta en un punto de venta no táctil.'))

        # Crear el wizard transient para la sesión encontrada
        wizard = self.env['pos.session.cash_move.wizard'].create({
            'session_id': session.id,
            'currency_id': session.currency_id.id if session.currency_id else False,
            'amount': 0.0,
        })

        # Obtener referencia a la vista del wizard de forma segura
        view_ref = self.env.ref('pos_conventional.view_pos_session_cash_move_wizard_form', raise_if_not_found=False)
        view_id = view_ref.id if view_ref else False

        action = {
            'name': _('Entrada / Salida de efectivo'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.session.cash_move.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': dict(self.env.context),
        }
        return action

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
            # Guardar los impuestos base del producto; la posición fiscal
            # calculará tax_ids_after_fiscal_position si aplica
            'tax_ids': [(6, 0, product_taxes.ids)],
        }

    def action_print_factura_simplificada(self):
        self.ensure_one()
        if not self.account_move:
            return

        return self.env.ref(
            "pos_conventional.action_factura_simplificada_80mm"
        ).report_action(self.account_move)

    def get_factura_report_url(self, order_id=None):
        """
        Devuelve la URL del informe HTML del account.move asociado para este pedido.
        Será llamada por JS en el backend para abrir el informe en un iframe y lanzar print().
        Acepta opcionalmente order_id (por compatibilidad con RPC que pasa posicionamente el id).
        """
        # Si nos pasan order_id (llamada desde RPC con [order_id]), usar ese registro
        if order_id:
            order = self.browse(order_id)
        else:
            order = self
        if not order or not order.exists():
            return False
        order = order.ensure_one()
        if not order.account_move:
            return False
        # Construir URL relativa al endpoint de report HTML
        base = '/report/html'
        report_xmlid = 'pos_conventional.report_factura_simplificada_80mm'
        url = f"{base}/{report_xmlid}/{order.account_move.id}"
        return url

    # --- Nuevas acciones para botones de pago (invocadas desde la vista)
    def action_pay_cash(self):
        self.ensure_one()
        cash_method = self.env['pos.payment.method'].search([('is_cash_count', '=', True)], limit=1)
        if not cash_method:
            raise UserError(_('No se encontró método de pago en efectivo.'))
        wizard = self.env['pos.make.payment'].with_context(active_id=self.id).create({
            'amount': self.amount_total - self.amount_paid,
            'payment_method_id': cash_method.id,
        })
        return wizard.action_pay_cash()

    def action_pay_card(self):
        self.ensure_one()
        # Cambia 'tarjeta' por el nombre exacto si es diferente
        card_method = self.env['pos.payment.method'].search([('name', 'ilike', 'tarjeta')], limit=1)
        if not card_method:
            raise UserError(_('No se encontró método de pago con tarjeta.'))
        wizard = self.env['pos.make.payment'].with_context(active_id=self.id).create({
            'amount': self.amount_total - self.amount_paid,
            'payment_method_id': card_method.id,
        })
        return wizard.action_pay_card()

    def action_pay_account(self):
        """
        Crea un sale.order tradicional a partir del pos.order actual.

        Este método transforma una venta POS en una venta tradicional de backoffice,
        copiando toda la información del pedido: cliente, líneas de productos,
        cantidades, precios, impuestos y descuentos.

        El pos.order original permanece en estado 'draft' sin afectar al flujo
        de caja ni al stock.

        Returns:
            dict: Acción para abrir el nuevo sale.order creado
        """
        self.ensure_one()

        # Validaciones previas
        if self.state != 'draft':
            raise UserError(_('Solo se pueden convertir a albarán pedidos en estado borrador.'))

        if not self.lines:
            raise UserError(_('No se puede crear un albarán de un pedido sin líneas de producto.'))

        if not self.partner_id:
            raise UserError(_('Debe seleccionar un cliente para crear el albarán.'))

        # Preparar las líneas del sale.order
        sale_order_lines = []
        for pos_line in self.lines:
            # Obtener los impuestos aplicables
            taxes = pos_line.tax_ids_after_fiscal_position or pos_line.tax_ids

            line_vals = {
                'product_id': pos_line.product_id.id,
                'name': pos_line.full_product_name or pos_line.product_id.display_name,
                'product_uom_qty': pos_line.qty,
                'product_uom_id': pos_line.product_id.uom_id.id,
                'price_unit': pos_line.price_unit,
                'discount': pos_line.discount or 0.0,
                'tax_ids': [(6, 0, taxes.ids)] if taxes else False,
            }
            sale_order_lines.append((0, 0, line_vals))

        # Crear el sale.order
        sale_order_vals = {
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'pricelist_id': self.pricelist_id.id if self.pricelist_id else False,
            'fiscal_position_id': self.fiscal_position_id.id if self.fiscal_position_id else False,
            'order_line': sale_order_lines,
            'origin': self.name,  # Referencia al pedido POS original
            'note': _('Creado desde pedido POS: %s') % self.name,
        }

        # Si hay una compañía específica, asignarla
        if self.company_id:
            sale_order_vals['company_id'] = self.company_id.id

        try:
            sale_order = self.env['sale.order'].create(sale_order_vals)
            _logger.info(
                "POS Order %s: Creado sale.order %s desde pedido POS",
                self.name, sale_order.name
            )

            # Vincular el pos.order con el sale.order creado y actualizar el nombre
            self.write({
                'linked_sale_order_id': sale_order.id,
                'name': sale_order.name,
                'state': 'linked'  # <--- AQUÍ ESTÁ EL CAMBIO MAESTRO
            })

            # Confirmar el pedido de venta automáticamente
            sale_order.action_confirm()
            _logger.info(
                "POS Order %s: sale.order %s confirmado automáticamente",
                self.name, sale_order.name
            )

            # Validar los pickings (entregas) generados
            for picking in sale_order.picking_ids:
                if picking.state == 'draft':
                    picking.action_confirm()
                if picking.state != 'done':
                    # Asignar cantidades automáticamente
                    picking.action_assign()
                    # Establecer cantidades hechas = cantidades demandadas
                    for move in picking.move_ids:
                        move.quantity = move.product_uom_qty
                    # Validar el picking
                    picking.button_validate()
                    _logger.info(
                        "POS Order %s: Picking %s validado automáticamente",
                        self.name, picking.name
                    )
        except Exception as e:
            _logger.exception("Error al crear sale.order desde POS: %s", str(e))
            raise UserError(_('Error al crear el albarán: %s') % str(e))



        # Recargar la vista del formulario para mostrar el estado vinculado
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Soporta creación en lote (vals_list es una lista de dicts).
        Para cada dict, si viene order_id y product_id, asegura que tax_ids
        contenga los impuestos del producto (mapeados por posición fiscal si aplica).
        """
        normalized = []
        for vals in vals_list:
            # Trabajar con una copia para no mutar la entrada original inesperadamente
            v = dict(vals)
            order = None
            if v.get('order_id'):
                order = self.env['pos.order'].browse(v.get('order_id'))
            if order and order.exists():
                if v.get('product_id'):
                    product = self.env['product.product'].browse(v.get('product_id'))
                    product_taxes = product.taxes_id.filtered(lambda t: t.company_id == order.company_id)
                    if order.fiscal_position_id:
                        taxes_after_fp = order.fiscal_position_id.map_tax(product_taxes)
                    else:
                        taxes_after_fp = product_taxes
                    # Si no vienen taxes en vals, asignarlas
                    if not v.get('tax_ids'):
                        v['tax_ids'] = [(6, 0, taxes_after_fp.ids)]
            normalized.append(v)
        return super(PosOrderLine, self).create(normalized)

    def write(self, vals):
        # Si se está guardando y no vienen tax_ids pero existe tax_ids_after_fiscal_position en el registro,
        # copiar esos impuestos a tax_ids para evitar que se pierdan.
        res = super(PosOrderLine, self).write(vals)
        for line in self:
            try:
                if not line.tax_ids and line.tax_ids_after_fiscal_position:
                    line.with_context(skip_inverse=True).write({'tax_ids': [(6, 0, line.tax_ids_after_fiscal_position.ids)]})
            except Exception:
                # No queremos romper el flujo de guardado si algo falla aquí
                _logger.exception('No se pudo sincronizar tax_ids en pos.order.line')
        return res

