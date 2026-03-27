import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    state = fields.Selection(
        selection_add=[("linked", "Vinculado a Venta")],
        ondelete={"linked": "set default"},
    )

    linked_sale_order_id = fields.Many2one(
        "sale.order",
        string="Pedido de venta vinculado",
        readonly=True,
        copy=False,
        help="Pedido de venta tradicional creado desde este pedido POS",
    )

    is_linked_to_sale = fields.Boolean(
        string="Vinculado a venta",
        compute="_compute_is_linked_to_sale",
        store=True,
        help="Indica si este pedido POS está vinculado a un pedido de venta tradicional",
    )

    show_albaran_button = fields.Boolean(
        string="Mostrar botón albarán",
        compute="_compute_show_albaran_button",
        store=False,
    )

    has_order_lines = fields.Boolean(
        string="Tiene líneas de pedido", compute="_compute_has_order_lines", store=False
    )

    payment_method_ribbon = fields.Char(
        string="Cinta de método de pago",
        compute="_compute_payment_method_ribbon",
        store=False,
    )

    @api.depends("payment_ids", "state")
    def _compute_payment_method_ribbon(self):
        for order in self:
            if order.state not in ("paid", "done"):
                order.payment_method_ribbon = False
                continue
            
            # Filtrar pagos con importe positivo (evitar el cambio que es negativo)
            # o simplemente tomar los métodos únicos presentes.
            methods = order.payment_ids.filtered(lambda p: p.amount > 0).mapped("payment_method_id")
            if not methods:
                order.payment_method_ribbon = False
            elif len(methods) > 1:
                order.payment_method_ribbon = "PAGO MÚLTIPLE"
            else:
                order.payment_method_ribbon = methods[0].name.upper()

    amount_untaxed = fields.Monetary(
        string="Importe base",
        compute="_compute_amount_untaxed",
        store=False,
        help="Subtotal sin impuestos calculado desde las líneas del pedido",
    )

    @api.depends("lines.price_subtotal", "is_refund")
    def _compute_amount_untaxed(self):
        """Calcula el subtotal sin impuestos sumando price_subtotal de todas las líneas"""
        for order in self:
            sign = -1 if order.is_refund else 1
            amount_untaxed = sum(line.price_subtotal for line in order.lines)
            if order.currency_id:
                amount_untaxed = order.currency_id.round(amount_untaxed)
            order.amount_untaxed = amount_untaxed * sign

    @api.depends("linked_sale_order_id")
    def _compute_is_linked_to_sale(self):
        """Calcula si el pedido está vinculado a un sale.order"""
        for order in self:
            order.is_linked_to_sale = bool(order.linked_sale_order_id)

    @api.depends(
        "session_id", "session_id.config_id", "session_id.config_id.pos_enable_albaran"
    )
    def _compute_show_albaran_button(self):
        for order in self:
            order.show_albaran_button = bool(
                order.session_id
                and order.session_id.config_id
                and order.session_id.config_id.pos_enable_albaran
            )

    @api.depends("lines")
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
                "type": "ir.actions.act_window",
                "res_model": "sale.order",
                "res_id": self.linked_sale_order_id.id,
                "view_mode": "form",
                "view_type": "form",
                "target": "current",
            }
        # Si no tiene sale.order vinculado, abrir el pos.order normalmente
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "res_id": self.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "current",
        }

    @api.model
    def get_product_line_data_by_barcode(
        self, barcode, pricelist_id=False, fiscal_position_id=False, partner_id=False
    ):
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
        Product = self.env["product.product"]
        product = Product.search([("barcode", "=", barcode)], limit=1)

        # Fallback: buscar por referencia interna (default_code)
        if not product:
            product = Product.search([("default_code", "=", barcode)], limit=1)

        if not product:
            return {
                "success": False,
                "message": _("No se encontró ningún producto con el código: %s")
                % barcode,
            }

        # Obtener precio desde la lista de precios
        public_price = product.lst_price
        price_unit = public_price
        discount = 0.0

        if pricelist_id:
            pricelist = self.env["product.pricelist"].browse(pricelist_id)
            partner = (
                self.env["res.partner"].browse(partner_id) if partner_id else False
            )
            price_unit = pricelist._get_product_price(
                product, 1.0, partner=partner, uom=product.uom_id
            )
            
            if public_price > price_unit and public_price > 0:
                discount = (public_price - price_unit) / public_price * 100
                price_unit = public_price

        # Obtener impuestos aplicables
        taxes = product.taxes_id.filtered(lambda t: t.company_id == self.env.company)

        # Aplicar posición fiscal si existe
        if fiscal_position_id:
            fiscal_position = self.env["account.fiscal.position"].browse(
                fiscal_position_id
            )
            taxes = fiscal_position.map_tax(taxes)

        return {
            "success": True,
            "product": {
                "id": product.id,
                "display_name": product.display_name,
            },
            "line_vals": {
                "full_product_name": product.display_name,
                "qty": 1.0,
                "price_unit": price_unit,
                "discount": discount,
                "tax_ids": taxes.ids,
            },
        }

    @api.model
    def default_get(self, fields_list):
        """Establecer valores por defecto al crear un pedido"""
        res = super().default_get(fields_list)

        # Si no hay compañía, usar la del usuario actual
        if "company_id" not in res or not res.get("company_id"):
            res["company_id"] = self.env.company.id

        # Inicializar montos si no están presentes
        if "amount_return" not in res:
            res["amount_return"] = 0.0
        if "amount_paid" not in res:
            res["amount_paid"] = 0.0

        # SOLO usar la sesión si viene explícitamente en el contexto
        session_id = self.env.context.get("default_session_id")
        if not session_id:
            # Reintentar con session_id plano si default_ no está
            session_id = self.env.context.get("session_id")

        if session_id:
            session = self.env["pos.session"].browse(session_id).exists()
            if session:
                res["session_id"] = session.id
                
                # Inicializar otros campos desde la sesión
                if "pricelist_id" not in res:
                    res["pricelist_id"] = session.config_id.pricelist_id.id
                if "currency_id" not in res:
                    res["currency_id"] = session.currency_id.id
                if "partner_id" in fields_list and not res.get("partner_id"):
                    if session.config_id.default_partner_id:
                        res["partner_id"] = session.config_id.default_partner_id.id
        
        # Si no se encontró sesión, intentar buscar la activa para el usuario (fallback agresivo)
        if not res.get("session_id"):
             active_session = self.env["pos.session"].search([
                 ("state", "=", "opened"),
                 ("config_id.pos_non_touch", "=", True)
             ], limit=1, order="id desc")
             if active_session:
                 res["session_id"] = active_session.id

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override de create para asegurar que cada pedido tenga una sesión asignada.
        Si no viene session_id, intenta buscar una sesión abierta para el usuario actual.
        """
        _logger.info("POS DEBUG: Entering create with vals_list: %s", vals_list)
        _logger.info("POS DEBUG: Context: %s", self.env.context)

        for vals in vals_list:
            if not vals.get("session_id"):
                # Buscar sesión abierta del usuario en un POS no táctil
                session = self.env["pos.session"].search(
                    [
                        ("user_id", "=", self.env.user.id),
                        ("state", "=", "opened"),
                        ("config_id.pos_non_touch", "=", True),
                    ],
                    limit=1,
                    order="id desc",
                )

                # Fallback: buscar cualquier sesión abierta en POS no táctil
                if not session:
                    session = self.env["pos.session"].search(
                        [
                            ("state", "=", "opened"),
                            ("config_id.pos_non_touch", "=", True),
                        ],
                        limit=1,
                        order="id desc",
                    )

                if session:
                    vals["session_id"] = session.id
                    # Asegurar otros campos relacionados si faltan
                    if not vals.get("pricelist_id"):
                        vals["pricelist_id"] = session.config_id.pricelist_id.id
                    if not vals.get("currency_id"):
                        vals["currency_id"] = session.currency_id.id
            
            # Asegurar que amount_paid esté inicializado para evitar error de constraint
            if "amount_paid" not in vals:
                vals["amount_paid"] = 0.0

        vals_list = super().create(vals_list)
        return vals_list

    @api.onchange("session_id")
    def _onchange_session_id(self):
        """Establece datos básicos cuando se selecciona una sesión"""
        if self.session_id:
            if not self.company_id:
                self.company_id = (
                    self.session_id.config_id.company_id or self.env.company
                )
            if not self.pricelist_id:
                self.pricelist_id = self.session_id.config_id.pricelist_id
            if not self.currency_id:
                self.currency_id = (
                    self.session_id.currency_id
                    or self.pricelist_id.currency_id
                    or self.company_id.currency_id
                )

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
                    line.with_context(skip_inverse=True).write(
                        {"tax_ids": [(6, 0, line.tax_ids_after_fiscal_position.ids)]}
                    )

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
        print(f"POS DEBUG: Entering action_validate_and_invoice for {self.name}")

        # Validaciones previas
        if self.state not in ["draft", "paid"]:
            raise UserError(
                _("Solo se pueden validar pedidos en estado borrador o pagado.")
            )

        if not self.lines:
            raise UserError(_("No se puede validar un pedido sin líneas de producto."))

        if not self.payment_ids:
            raise UserError(_("No se puede validar un pedido sin pagos registrados."))

        if not self.config_id.invoice_journal_id:
            raise UserError(
                _(
                    "No hay un diario de facturación configurado para este punto de venta."
                )
            )

        # Verificar que el pedido esté pagado
        if not self._is_pos_order_paid():
            raise UserError(
                _("El pedido no está completamente pagado. Faltan %.2f %s")
                % (self.amount_total - self.amount_paid, self.currency_id.symbol)
            )

        # Si ya tiene factura, no crear otra
        if self.account_move:
            raise UserError(
                _("Este pedido ya tiene una factura asociada: %s")
                % self.account_move.name
            )

        # Marcar para facturar
        self.write({"to_invoice": True})

        # Si el pedido está en draft, marcarlo como pagado
        if self.state == "draft":
            try:
                self.action_pos_order_paid()
            except Exception as e:
                _logger.exception("Error al marcar pedido como pagado: %s", str(e))
                raise UserError(_("Error al validar el pedido: %s") % str(e))

        # Crear picking si es necesario (para contabilidad anglosajona)
        if (
            self.company_id.anglo_saxon_accounting
            and self.session_id.update_stock_at_closing
            and self.session_id.state != "closed"
        ):
            self._create_order_picking()

        # Generar la factura usando el método oficial de Odoo POS
        try:
            invoice = self._generate_pos_order_invoice()
            _logger.info(
                "POS Order %s: Factura %s creada correctamente desde backend",
                self.name,
                invoice.name,
            )
        except Exception as e:
            _logger.exception("Error al generar factura: %s", str(e))
            raise UserError(_("Error al generar la factura: %s") % str(e))

        if self.config_id.iface_print_auto and not self.env.context.get("pos_skip_printing"):
            # Construir la URL del informe HTML y devolver una acción cliente
            report_xmlid = "pos_conventional.report_factura_simplificada_80mm"
            url = f"/report/html/{report_xmlid}/{invoice.id}"
            return {
                "type": "ir.actions.client",
                "tag": "pos_conventional.print_iframe",
                "params": {
                    "url": url,
                    "next_action": self._get_post_validation_action(),
                },
            }

        post_action = self._get_post_validation_action()
        if post_action:
            return post_action

        return True

    def _get_post_validation_action(self):
        print(
            f"POS DEBUG: Calling _get_post_validation_action. Config Force Login: {self.config_id.pos_force_employee_login_after_order}"
        )

        return {
            "type": "ir.actions.client",
            "tag": "pos_conventional_new_order",
            "params": {
                "default_session_id": self.session_id.id,
                "force_login_after_order": self.config_id.pos_force_employee_login_after_order,
            },
        }

    def action_close_pos_session_wizard(self):
        """
        Abre el popup de cierre de sesión POS estilo Odoo.
        Este método se llama desde el botón en la vista de pedidos.

        La sesión se determina en este orden de prioridad:
        1. session_id del contexto (pasado desde la vista)
        2. session_id del pedido actual (si se llama desde un pedido específico)
        3. Buscar sesión abierta del usuario en un POS no táctil
        """
        session = None

        # 1. Intentar obtener la sesión del contexto
        session_id = self.env.context.get("default_session_id") or self.env.context.get(
            "session_id"
        )
        if session_id:
            session = self.env["pos.session"].browse(session_id)
            if not session.exists() or session.state not in [
                "opened",
                "closing_control",
            ]:
                session = None

        # 2. Si no hay contexto, intentar obtener del pedido actual
        if not session and self:
            order = self[0] if len(self) > 0 else None
            if (
                order
                and order.session_id
                and order.session_id.state in ["opened", "closing_control"]
            ):
                session = order.session_id

        # 3. Si aún no hay sesión, buscar una sesión de POS no táctil del usuario
        if not session:
            session = self.env["pos.session"].search(
                [
                    ("user_id", "=", self.env.user.id),
                    ("state", "in", ["opened", "closing_control"]),
                    ("config_id.pos_non_touch", "=", True),  # Solo POS no táctil
                ],
                limit=1,
                order="id desc",
            )

            # Fallback: Si no encuentro sesión del usuario, busco cualquiera abierta en POS no táctil
            if not session:
                session = self.env["pos.session"].search(
                    [
                        ("state", "in", ["opened", "closing_control"]),
                        ("config_id.pos_non_touch", "=", True),
                    ],
                    limit=1,
                    order="id desc",
                )

        if not session:
            raise UserError(
                _("No tienes ninguna sesión abierta en un punto de venta no táctil.")
            )

        # Abrir el popup de cierre usando la acción cliente
        return {
            "type": "ir.actions.client",
            "tag": "pos_conventional_closing_popup",
            "name": _("Cerrar caja registradora"),
            "target": "current",
            "context": {
                "session_id": session.id,
                "default_session_id": session.id,
            },
        }

    def action_cash_in_out_wizard(self):
        """
        Abre el popup de entrada/salida de efectivo estilo Odoo.
        Este método se llama desde el botón en la vista de pedidos.

        La sesión se determina en este orden de prioridad:
        1. session_id del contexto (pasado desde la vista)
        2. session_id del pedido actual (si se llama desde un pedido específico)
        3. Buscar sesión abierta del usuario en un POS no táctil
        """
        session = None

        # 1. Intentar obtener la sesión del contexto
        session_id = self.env.context.get("default_session_id") or self.env.context.get(
            "session_id"
        )
        if session_id:
            session = self.env["pos.session"].browse(session_id)
            if not session.exists() or session.state != "opened":
                session = None

        # 2. Si no hay contexto, intentar obtener del pedido actual
        if not session and self:
            order = self[0] if len(self) > 0 else None
            if order and order.session_id and order.session_id.state == "opened":
                session = order.session_id

        # 3. Si aún no hay sesión, buscar una sesión de POS no táctil del usuario
        if not session:
            session = self.env["pos.session"].search(
                [
                    ("user_id", "=", self.env.user.id),
                    ("state", "=", "opened"),
                    ("config_id.pos_non_touch", "=", True),  # Solo POS no táctil
                ],
                limit=1,
                order="id desc",
            )

            # Fallback: Si no encuentro sesión del usuario, busco cualquiera abierta en POS no táctil
            if not session:
                session = self.env["pos.session"].search(
                    [
                        ("state", "=", "opened"),
                        ("config_id.pos_non_touch", "=", True),
                    ],
                    limit=1,
                    order="id desc",
                )

        if not session:
            raise UserError(
                _("No tienes ninguna sesión abierta en un punto de venta no táctil.")
            )

        # Abrir el popup de entrada/salida de efectivo usando la acción cliente
        return {
            "type": "ir.actions.client",
            "tag": "pos_conventional_cash_move_popup",
            "name": _("Entrada / Salida de efectivo"),
            "target": "current",
            "context": {
                "session_id": session.id,
                "default_session_id": session.id,
            },
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

        if self.state != "draft":
            return {
                "success": False,
                "message": _(
                    "No se pueden añadir productos a un pedido que no está en borrador."
                ),
            }

        Product = self.env["product.product"]

        # Obtener el producto por ID o por código de barras
        if product_id:
            product = Product.browse(product_id)
            if not product.exists():
                return {
                    "success": False,
                    "message": _("Producto no encontrado con ID: %s") % product_id,
                }
        elif barcode:
            # Buscar producto por código de barras
            product = Product.search([("barcode", "=", barcode)], limit=1)
            # Fallback: buscar por referencia interna (default_code)
            if not product:
                product = Product.search([("default_code", "=", barcode)], limit=1)
            if not product:
                return {
                    "success": False,
                    "message": _("No se encontró ningún producto con el código: %s")
                    % barcode,
                }
        else:
            return {
                "success": False,
                "message": _("Debe proporcionar un código de barras o ID de producto."),
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
                price_subtotal = tax_results["total_excluded"]
                price_subtotal_incl = tax_results["total_included"]

            line.write(
                {
                    "qty": new_qty,
                    "price_subtotal": price_subtotal,
                    "price_subtotal_incl": price_subtotal_incl,
                    "discount": discount,
                }
            )

            # Forzar recálculo de totales del pedido (ejecuta el compute)
            self._compute_prices()

            _logger.info(
                "POS Order %s: Incrementada cantidad del producto %s a %s",
                self.name,
                product.display_name,
                new_qty,
            )
            return {
                "success": True,
                "message": _("Cantidad actualizada: %s x %s")
                % (new_qty, product.display_name),
            }

        # Crear nueva línea de pedido
        try:
            line_vals = self._prepare_order_line_vals(product)
            new_line = self.env["pos.order.line"].create(line_vals)

            # Ejecutar onchange de la línea para calcular subtotales
            new_line._onchange_qty()

            # Forzar recálculo de totales del pedido (ejecuta el compute)
            self._compute_prices()

            _logger.info(
                "POS Order %s: Añadido producto %s mediante escaneo de código de barras",
                self.name,
                product.display_name,
            )

            return {"success": True, "message": _("Añadido: %s") % product.display_name}

        except Exception as e:
            _logger.exception(
                "Error al añadir producto por código de barras: %s", str(e)
            )
            return {
                "success": False,
                "message": _("Error al añadir el producto: %s") % str(e),
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
        public_price = product.lst_price
        pricelist = self.pricelist_id or self.config_id.pricelist_id
        discount = 0.0
        if pricelist:
            price_unit = pricelist._get_product_price(
                product, qty, partner=self.partner_id, uom=product.uom_id
            )
            if public_price > price_unit and public_price > 0:
                discount = (public_price - price_unit) / public_price * 100
                price_unit = public_price
        else:
            price_unit = public_price

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
            price_subtotal = tax_results["total_excluded"]
            price_subtotal_incl = tax_results["total_included"]

        return {
            "order_id": self.id,
            "product_id": product.id,
            "full_product_name": product.display_name,
            "qty": qty,
            "price_unit": price_unit,
            "discount": discount,
            "price_subtotal": price_subtotal,
            "price_subtotal_incl": price_subtotal_incl,
            # Guardar los impuestos base del producto; la posición fiscal
            # calculará tax_ids_after_fiscal_position si aplica
            "tax_ids": [(6, 0, product_taxes.ids)],
        }

    def action_print_factura_simplificada(self):
        self.ensure_one()
        if not self.account_move:
            return

        return self.env.ref(
            "pos_conventional.action_factura_simplificada_80mm"
        ).report_action(self.account_move)

    def action_send_email(self):
        """
        Envía el ticket de compra por correo electrónico al cliente.
        Abre el wizard de composición de email con la plantilla precargada.
        """
        self.ensure_one()
        if not self.account_move:
            raise UserError(_("Este pedido no tiene una factura asociada para enviar."))

        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente para enviar el correo."))

        if not self.partner_id.email:
            raise UserError(
                _("El cliente '%s' no tiene email configurado.") % self.partner_id.name
            )

        # Obtener la plantilla de email
        template = self.env.ref(
            "pos_conventional.email_template_pos_receipt", raise_if_not_found=False
        )

        if not template:
            raise UserError(
                _("No se encontró la plantilla de email para el ticket POS.")
            )

        # Abrir el wizard de composición de email con la plantilla
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": "account.move",
                "default_res_ids": [self.account_move.id],
                "default_template_id": template.id,
                "default_composition_mode": "comment",
                "force_email": True,
            },
        }

    def get_factura_report_url(self, order_id=None):

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
        base = "/report/html"
        report_xmlid = "pos_conventional.report_factura_simplificada_80mm"
        url = f"{base}/{report_xmlid}/{order.account_move.id}"
        return url

    # --- Nuevas acciones para botones de pago (invocadas desde la vista)
    def action_pay_cash(self):
        self.ensure_one()
        cash_method = self.config_id.payment_method_ids.filtered('is_cash_count')[:1]
        if not cash_method:
             cash_method = self.config_id.payment_method_ids.filtered(lambda p: p.journal_id.type == 'cash')[:1]

        if not cash_method:
            raise UserError(_("No se encontró método de pago en efectivo en la caja."))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.make.payment.wizard',
            'name': _('Pago en Efectivo'),
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'default_payment_method_id': cash_method.id,
                'cash_only': True,
            }
        }

    def action_pay_card(self):
        self.ensure_one()
        card_method = self.config_id.payment_method_ids.filtered(lambda p: p.journal_id.type == 'bank')[:1]
        
        if not card_method:
            raise UserError(_("No se encontró método de pago con tarjeta en la caja."))

        wizard = (
            self.env["pos.make.payment"]
            .with_context(active_id=self.id)
            .create(
                {
                    "amount": self.amount_total - self.amount_paid,
                    "payment_method_id": card_method.id,
                }
            )
        )
        return wizard.action_pay_card()

    def action_open_payment_popup(self):
        """
        Abre el asistente de pago (Wizard Python/XML) para este pedido.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.make.payment.wizard',
            'name': _('Realizar Pago'),
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            }
        }

    def get_payment_popup_data(self):
        """
        Devuelve los datos necesarios para el popup de pago combinado.
        """
        self.ensure_one()
        # Forzar recomputo de totales por si acaso
        # En Odoo 19 el método estándar es _compute_prices o se hace vía tax_totals
        try:
            self._compute_prices()
        except Exception:
            # Fallback a un cálculo simple si fallara el estándar
            self.amount_total = sum(self.lines.mapped('price_subtotal_incl'))

        self.flush_recordset()


        _logger.info("POS DEBUG: get_payment_popup_data for order %s (ID %s)", self.name, self.id)
        _logger.info("POS DEBUG: amount_total: %s, amount_paid: %s", self.amount_total, self.amount_paid)

        available_methods = []
        for pm in self.config_id.payment_method_ids:
            icon = "fa-money"
            if pm.journal_id.type == "cash":
                icon = "fa-money"
            elif pm.journal_id.type == "bank":
                icon = "fa-credit-card"

            available_methods.append({
                'id': pm.id,
                'name': pm.name,
                'type': pm.type,
                'use_payment_terminal': pm.use_payment_terminal,
                'icon': icon,
            })

        payments = []
        for p in self.payment_ids:
            p_icon = "fa-money"
            if p.payment_method_id.journal_id.type == "cash":
                p_icon = "fa-money"
            elif p.payment_method_id.journal_id.type == "bank":
                p_icon = "fa-credit-card"

            payments.append({
                'id': p.id,
                'payment_method_id': p.payment_method_id.id,
                'payment_method_name': p.payment_method_id.name,
                'amount': p.amount,
                'icon': p_icon,
            })

        amount_due = self.amount_total - self.amount_paid
        # Redondear para evitar problemas de coma flotante
        amount_due = round(amount_due, self.currency_id.decimal_places)

        _logger.info("POS DEBUG: amount_due: %s, currency: %s", amount_due, self.currency_id.symbol)

        return {
            'order_id': self.id,
            'amount_total': self.amount_total,
            'amount_paid': self.amount_paid,
            'amount_due': amount_due,
            'currency_symbol': self.currency_id.symbol or "€",
            'available_methods': available_methods,
            'payments': payments,
        }



    def add_payment_from_ui(self, payment_method_id, amount):
        """
        Añade un pago desde la interfaz Owl.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se pueden añadir pagos a pedidos en borrador."))

        payment_method = self.env['pos.payment.method'].browse(payment_method_id)
        if not payment_method.exists():
            raise UserError(_("Método de pago no encontrado."))

        self.add_payment({
            'pos_order_id': self.id,
            'amount': float(amount),
            'payment_method_id': payment_method_id,
        })

        return self.get_payment_popup_data()

    def remove_payment_from_ui(self, payment_id):
        """
        Elimina un pago desde la interfaz Owl.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se pueden eliminar pagos de pedidos en borrador."))

        payment = self.env['pos.payment'].browse(payment_id)
        if payment.exists() and payment.pos_order_id.id == self.id:
            payment.unlink()

        return self.get_payment_popup_data()

    def update_payment_from_ui(self, payment_id, amount):
        """
        Actualiza el importe de un pago desde la interfaz Owl.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se pueden modificar pagos de pedidos en borrador."))

        payment = self.env['pos.payment'].browse(payment_id)
        if payment.exists() and payment.pos_order_id.id == self.id:
            payment.write({'amount': float(amount)})

        return self.get_payment_popup_data()

    def action_register_payments_and_validate(self, payments, print_invoice=False):
        """
        Reemplaza los pagos existentes con la lista proporcionada y valida el pedido.
        """
        self.ensure_one()
        if self.state != 'draft':
            return {'success': False, 'message': _("El pedido ya está validado.")}

        # 1. Eliminar pagos existentes
        self.payment_ids.unlink()

        # 2. Crear nuevos pagos
        for pay in payments:
            amount = float(pay.get('amount', 0))
            if amount != 0:
                self.add_payment({
                    'pos_order_id': self.id,
                    'payment_method_id': int(pay.get('payment_method_id')),
                    'amount': amount,
                })

        # 2.5. Gestión del cambio (Devolución de importe excedente)
        amount_paid = sum(self.payment_ids.mapped('amount'))
        amount_total = self._get_rounded_amount(self.amount_total)

        if self.currency_id.compare_amounts(amount_paid, amount_total) > 0:
            change_amount = amount_paid - amount_total
            cash_payment_method = self.session_id.payment_method_ids.filtered('is_cash_count')[:1]
            if not cash_payment_method:
                return {'success': False, 'message': _("No hay método de efectivo en esta sesión para devolver el cambio.")}
            
            self.add_payment({
                'name': _('return'),
                'pos_order_id': self.id,
                'amount': -change_amount,
                'payment_method_id': cash_payment_method.id,
                'is_change': True,
            })


        # 3. Validar
        # Comprobar si está pagado completamente?
        # El frontend debería haber validado esto, pero el backend es la autoridad.
        if self._is_pos_order_paid():
            # Siempre facturar al validar desde el popup
            _logger.info("POS VALIDATION: Order %s is paid. Setting to_invoice=True", self.name)
            self.write({'to_invoice': True})

            self.action_pos_order_paid()

            # Acción de redirección a la vista de un nuevo pedido en blanco (igual que pago directo)
            next_action = {
                "type": "ir.actions.client",
                "tag": "pos_conventional_new_order",
                "params": {
                    "config_id": self.config_id.id,
                    "default_session_id": self.session_id.id,
                },
            }

            final_action = next_action

            # Si hay factura, usar la acción cliente de impresión que luego llama a next_action
            if self.to_invoice:
                _logger.info("POS VALIDATION: Generating invoice for %s", self.name)
                invoice = self._generate_pos_order_invoice()
                _logger.info("POS VALIDATION: Invoice %s generated for order %s", invoice.name, self.name)
                # Client action for native-like printing
                final_action = {
                    "type": "ir.actions.client",
                    "tag": "pos_conventional.print_receipt_client",
                    "params": {
                        "order_id": self.id,
                        "next_action": next_action,
                    },
                }

            return {
                'success': True,
                'action': final_action,
            }
        else:
            # Si falta dinero, devolvemos datos actualizados
             return self.get_payment_popup_data()

    def action_pay_account(self):

        self.ensure_one()
        print(f"POS DEBUG: Entering action_pay_account for {self.name}")
        if self.state != "draft":
            raise UserError(
                _("Solo se pueden convertir a albarán pedidos en estado borrador.")
            )

        if not self.lines:
            raise UserError(
                _("No se puede crear un albarán de un pedido sin líneas de producto.")
            )

        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente para crear el albarán."))

        sale_order_lines = []
        for pos_line in self.lines:
            taxes = pos_line.tax_ids_after_fiscal_position or pos_line.tax_ids
            line_vals = {
                "product_id": pos_line.product_id.id,
                "name": pos_line.full_product_name or pos_line.product_id.display_name,
                "product_uom_qty": pos_line.qty,
                "product_uom_id": pos_line.product_id.uom_id.id,
                "price_unit": pos_line.price_unit,
                "discount": pos_line.discount or 0.0,
                "tax_ids": [(6, 0, taxes.ids)] if taxes else False,
            }
            sale_order_lines.append((0, 0, line_vals))

        sale_order_vals = {
            "partner_id": self.partner_id.id,
            "partner_invoice_id": self.partner_id.id,
            "partner_shipping_id": self.partner_id.id,
            "pricelist_id": self.pricelist_id.id if self.pricelist_id else False,
            "fiscal_position_id": (
                self.fiscal_position_id.id if self.fiscal_position_id else False
            ),
            "order_line": sale_order_lines,
            "origin": self.name,
            "note": _("Creado desde pedido POS: %s") % self.name,
        }

        if self.company_id:
            sale_order_vals["company_id"] = self.company_id.id

        created_picking = False

        try:
            sale_order = self.env["sale.order"].create(sale_order_vals)
            _logger.info(
                "POS Order %s: Creado sale.order %s", self.name, sale_order.name
            )

            self.write(
                {
                    "linked_sale_order_id": sale_order.id,
                    "name": sale_order.name,
                    "state": "linked",
                }
            )

            sale_order.action_confirm()

            for picking in sale_order.picking_ids:
                created_picking = picking
                if picking.state == "draft":
                    picking.action_confirm()
                if picking.state != "done":
                    picking.action_assign()
                    for move in picking.move_ids:
                        move.quantity = move.product_uom_qty
                    picking.button_validate()
                    _logger.info(
                        "POS Order %s: Picking %s validado", self.name, picking.name
                    )

        except Exception as e:
            _logger.exception("Error al crear sale.order desde POS: %s", str(e))
            raise UserError(_("Error al crear el albarán: %s") % str(e))

        if created_picking:
            report_url = (
                "/report/html/pos_conventional.report_albaran_80mm/%s"
                % created_picking.id
            )
            return {
                "type": "ir.actions.client",
                "tag": "pos_conventional_print_iframe",
                "params": {
                    "url": report_url,
                    "next_action": self._get_post_validation_action()
                    or {
                        "type": "ir.actions.act_window",
                        "res_model": "pos.order",
                        "res_id": self.id,
                        "view_mode": "form",
                        "views": [[False, "form"]],
                        "target": "current",
                    },
                },
            }

        next_action = self._get_post_validation_action()
        if next_action:
            return next_action

        return {
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "res_id": self.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "current",
        }

    @api.model
    def get_order_receipt_data(self, order_id):
        order = self.browse(order_id)
        if not order:
            return {}

        return {
            'pos_reference': order.pos_reference,
            'ticket_code': order.ticket_code,
            'date_order': order.date_order.strftime('%Y-%m-%d %H:%M:%S') if order.date_order else '',
            'amount_total': order.amount_total,
            'amount_return': order.amount_return,
            'amount_tax': order.amount_tax,
            'currency_id': [order.currency_id.id, order.currency_id.symbol, order.currency_id.position, order.currency_id.decimal_places],
            'currency_code': order.currency_id.name,
            'currency_rounding': order.currency_id.rounding,
            'receipt_header': order.session_id.config_id.receipt_header or '',
            'receipt_footer': order.session_id.config_id.receipt_footer or '',
            'partner': {
                'id': order.partner_id.id,
                'name': order.partner_id.name,
                'vat': order.partner_id.vat,
                'email': order.partner_id.email,
                'phone': order.partner_id.phone,
                'address': order.partner_id._display_address(without_company=True),
            } if order.partner_id else False,
            'user_id': [order.user_id.id, order.user_id.name] if order.user_id else False,
            'company': {
                'id': order.company_id.id,
                'name': order.company_id.name,
                'logo': bool(order.company_id.logo),
                'contact_address': order.company_id.partner_id._display_address(without_company=True),
                'phone': order.company_id.phone,
                'vat': order.company_id.vat,
                'email': order.company_id.email,
                'website': order.company_id.website,
                'country_id': {'vat_label': order.company_id.country_id.vat_label or 'VAT'} if order.company_id.country_id else False,
            },
            'access_token': order.access_token,
            'amount_paid': sum(order.payment_ids.mapped('amount')),
            'tax_details': {
                'has_tax_groups': bool(order.lines.tax_ids_after_fiscal_position),
                'subtotals': [{
                    'name': 'Untaxed Amount',
                    'tax_groups': [{
                        'id': tax.tax_group_id.id,
                        'group_name': tax.tax_group_id.name,
                        'group_label': tax.tax_group_id.pos_receipt_label or tax.tax_group_id.name,
                        'tax_amount_currency': sum(line.price_subtotal_incl - line.price_subtotal for line in order.lines if tax in line.tax_ids_after_fiscal_position),
                        'base_amount_currency': sum(line.price_subtotal for line in order.lines if tax in line.tax_ids_after_fiscal_position),
                    } for tax in order.lines.tax_ids_after_fiscal_position]
                }],
                'same_tax_base': True,
                'total_amount_currency': order.amount_total,
                'base_amount': order.amount_total - order.amount_tax,
                'tax_amount_currency': order.amount_tax,
                'order_sign': 1,
                'total_amount_no_rounding': order.amount_total,
            },
            'lines': [{
                'id': line.id,
                'product_id': [line.product_id.id, line.product_id.display_name],
                'qty': line.qty,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'price_subtotal_incl': line.price_subtotal_incl,
                'discount': line.discount,
                'customer_note': line.customer_note,
            } for line in order.lines],
            'payment_ids': [{
                'id': p.id,
                'payment_method_id': [p.payment_method_id.id, p.payment_method_id.name],
                'amount': p.amount,
            } for p in order.payment_ids],
        }




class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    @api.depends('price_subtotal', 'total_cost')
    def _compute_margin(self):
        for line in self:
            sign = -1 if line.order_id.is_refund else 1
            if line.product_id.type == 'combo':
                line.margin = 0
                line.margin_percent = 0
            else:
                line.margin = (line.price_subtotal * sign) - line.total_cost
                if line.currency_id and line.currency_id.rounding > 0:
                     line.margin_percent = not float_is_zero(line.price_subtotal, precision_rounding=line.currency_id.rounding) \
                                        and line.margin / (line.price_subtotal * sign) \
                                        or 0
                else:
                    line.margin_percent = 0

    @api.onchange('product_id', 'qty')
    def _onchange_product_id(self):
        """Calcula el precio y descuento según la tarifa del pedido al cambiar producto o cantidad."""
        for line in self:
            if not line.product_id:
                continue
            
            # Obtener datos del pedido
            order = line.order_id
            pricelist = order.pricelist_id or order.config_id.pricelist_id
            
            # Obtener precio público y precio de tarifa
            public_price = line.product_id.lst_price
            if pricelist:
                price_unit = pricelist._get_product_price(
                    line.product_id, line.qty or 1.0, partner=order.partner_id, uom=line.product_id.uom_id
                )
                
                # Si hay descuento (precio de tarifa menor al público), mostrarlo
                if public_price > price_unit and public_price > 0:
                    line.discount = (public_price - price_unit) / public_price * 100
                    line.price_unit = public_price
                else:
                    line.price_unit = price_unit
                    line.discount = 0.0
            else:
                line.price_unit = public_price
                line.discount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            # Trabajar con una copia para no mutar la entrada original inesperadamente
            v = dict(vals)
            order = None
            if v.get("order_id"):
                order = self.env["pos.order"].browse(v.get("order_id"))
            if order and order.exists():
                if v.get("product_id"):
                    product = self.env["product.product"].browse(v.get("product_id"))
                    product_taxes = product.taxes_id.filtered(
                        lambda t: t.company_id == order.company_id
                    )
                    if order.fiscal_position_id:
                        taxes_after_fp = order.fiscal_position_id.map_tax(product_taxes)
                    else:
                        taxes_after_fp = product_taxes
                    # Si no vienen taxes en vals, asignarlas
                    if not v.get("tax_ids"):
                        v["tax_ids"] = [(6, 0, taxes_after_fp.ids)]
            normalized.append(v)
        return super(PosOrderLine, self).create(normalized)

    def write(self, vals):
        # Si se está guardando y no vienen tax_ids pero existe tax_ids_after_fiscal_position en el registro,
        # copiar esos impuestos a tax_ids para evitar que se pierdan.
        res = super(PosOrderLine, self).write(vals)
        for line in self:
            try:
                if not line.tax_ids and line.tax_ids_after_fiscal_position:
                    line.with_context(skip_inverse=True).write(
                        {"tax_ids": [(6, 0, line.tax_ids_after_fiscal_position.ids)]}
                    )
            except Exception:
                # No queremos romper el flujo de guardado si algo falla aquí
                _logger.exception("No se pudo sincronizar tax_ids en pos.order.line")
        return res
