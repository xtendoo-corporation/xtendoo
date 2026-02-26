import logging
from base64 import b64decode
from io import StringIO
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class GestoolImport(models.TransientModel):
    _name = "gestool.import"
    _description = "Importador desde Gestool"

    # data_file_agentes = fields.Binary(
    #     string="File to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename_agentes = fields.Char()

    data_file_partner = fields.Binary(
        string="Partners to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_partner = fields.Char()
    #
    # data_file_bank = fields.Binary(
    #     string="Banks to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename_bank = fields.Char()
    #
    # data_file_atypical = fields.Binary(
    #     string="Atypical to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename_atypical = fields.Char()
    #
    data_file_category = fields.Binary(
        string="Category to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_category = fields.Char()

    data_file_product = fields.Binary(
        string="Product to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_product = fields.Char()

    data_file_ticket = fields.Binary(
        string="Tickets header to import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_ticket = fields.Char()
    #
    # data_file_kits = fields.Binary(
    #     string="File to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename_kits = fields.Char()
    #
    # data_file_property = fields.Binary(
    #     string="File to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename_property = fields.Char()

    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()

        # if self.data_file_agentes:
        #     data_file_agentes = b64decode(self.data_file_agentes)
        #     if data_file_agentes:
        #         self._import_agentes(data_file_agentes)

        if self.data_file_partner:
            data_file_partner = b64decode(self.data_file_partner)
            if data_file_partner:
                self._import_partner(data_file_partner)

    #     if self.data_file_bank:
    #         data_file_bank = b64decode(self.data_file_bank)
    #         if data_file_bank:
    #             self._import_bank(data_file_bank)
    #
    #     if self.data_file_atypical:
    #         data_file_atypical = b64decode(self.data_file_atypical)
    #         if data_file_atypical:
    #             self._import_atypical(data_file_atypical)
    #
        if self.data_file_category:
            data_file_category = b64decode(self.data_file_category)
            if data_file_category:
                self._import_category(data_file_category)

        if self.data_file_product:
            data_file_product = b64decode(self.data_file_product)
            if data_file_product:
                self._import_product(data_file_product)

        if self.data_file_ticket:
            data_file_ticket = b64decode(self.data_file_ticket)
            if data_file_ticket:
                self._import_ticket(data_file_ticket)
    #
    #     if self.data_file_kits:
    #         data_file_kits = b64decode(self.data_file_kits)
    #         if data_file_kits:
    #             self._import_kits(data_file_kits)
    #
    #     if self.data_file_property:
    #         data_file_property = b64decode(self.data_file_property)
    #         if data_file_property:
    #             self._import_property(data_file_property)
    #
    # def _import_atypical(self, data_file_atypical):
    #     try:
    #         if data_file_atypical:
    #             csv_data = reader(StringIO(data_file_atypical.decode("utf-8")))
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #
    #     if csv_data:
    #         for row in csv_data:
    #             print("--------------------Atipicas de clientes--------------------------")
    #             self.parse_atypical(row)
    #         return
    #
    # def parse_atypical(self, row):
    #     partner = self.env["res.partner"].search([("ref", "=", row[0]), ])
    #     product = self.env["product.template"].search([("default_code", "=", row[1]), ])
    #
    #     print("Cliente", row[0])
    #     print("Articulo", row[1])
    #     print("Precio", row[2])
    #     # print("Descuento", row[3])
    #
    #     if product:
    #         if partner:
    #             # Comprobamos que no exista
    #             headpricelist = self.env["product.pricelist"].search([("name", "=", partner.name), ])
    #
    #             # Metemos las cabeceras de las tarifas
    #
    #             if not headpricelist:
    #                 headpricelist = self.env["product.pricelist"].sudo().create({
    #                     "name": partner.name,
    #                 })
    #
    #             if row[2] != "0.000":
    #                 # Metemos las lineas de las tarifas
    #                 self.env["product.pricelist.item"].sudo().create({
    #                     "pricelist_id": headpricelist.id,
    #                     "product_tmpl_id": product.id,
    #                     'applied_on': "1_product",
    #                     'compute_price': "fixed",
    #                     'fixed_price': row[2],
    #                 })
    #                 print("creado por precio")
    #
    #             if len(row) > 3 and row[3] != "0.000":
    #                 # Metemos las lineas de las tarifas
    #                 self.env["product.pricelist.item"].sudo().create({
    #                     "pricelist_id": headpricelist.id,
    #                     "product_tmpl_id": product.id,
    #                     'applied_on': "1_product",
    #                     'compute_price': "percentage",
    #                     'percent_price': row[3],
    #                 })
    #                 print("creado por descuento")
    #
    #             # La aplicamos al cliente
    #             partner.sudo().write({
    #                 "property_product_pricelist": headpricelist,
    #             })
    #
    #         else:
    #             print("No existe el partner con código:", row[0])
    #     else:
    #         print("No existe el producto con código:", row[1])
    #
    # def _import_kits(self, data_file_kits):
    #     try:
    #         if data_file_kits:
    #             csv_data = reader(StringIO(data_file_kits.decode("utf-8")))
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #
    #     if csv_data:
    #         for row in csv_data:
    #             print("--------------------Listas de materiales--------------------------")
    #             self.parse_kits(row)
    #         return
    #
    # def parse_kits(self, row):
    #
    #     print("Compuesto", row[0])
    #     print("Componente", row[1])
    #     print("Unidades", row[2])
    #
    #     # Busca el producto compuesto
    #     compound = self.env["product.template"].search([("default_code", "=", row[0])], )
    #     # Busca el producto componente
    #     component = self.env["product.template"].search([("default_code", "=", row[1])], )
    #
    #     if not compound:
    #         print(f"No existe el producto compuesto con código: {row[0]}")
    #         return
    #
    #     if not component:
    #         print(f"No existe el producto componente con código: {row[1]}")
    #         return
    #
    #     # Busca o crea la lista de materiales (BOM)
    #     bom = self.env["mrp.bom"].search([("product_tmpl_id", "=", compound.id)], limit=1)
    #     if not bom:
    #         bom = self.env["mrp.bom"].sudo().create({
    #             "product_tmpl_id": compound.id,
    #             "type": "normal",
    #         })
    #
    #     # Añade el componente a la lista de materiales
    #     self.env["mrp.bom.line"].sudo().create({
    #         "bom_id": bom.id,
    #         "product_id": component.id,
    #         "product_qty": row[2],
    #     })
    #     print(f"Componente añadido a la lista de materiales: {component.name}")
    #
    def _import_partner(self, data_file_partner):
        try:
            if data_file_partner:
                csv_data = reader(StringIO(data_file_partner.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            print("--------------------CLIENES--------------------------")
            self.parse_partner(row)
        return

    def parse_partner(self, row):
        partner = self.env["res.partner"].search([("ref", "=", row[0]), ])

        country_id = self.env["res.country"].search([("name", "=", "España", )] )
        if country_id:
            country_id = country_id.id

        state_id = self.env["res.country.state"].search([("name", "=", row[6].capitalize()), ("country_id.name", "=", "España")])
        if state_id:
            state_id = state_id.id

        company = self.env.company

        # agent_id = self.env[("res.users")].search([("name", "=", row[23]), ])
        # if agent_id:
        #     agent_id = agent_id.id
        # else:
        #     agent_id = ""

        # pago_id = self.env[("account.payment.term")].search([("name", "=", row[21]), ])
        # if pago_id:
        #     pago_id = pago_id.id
        # else:
        #     pago_id = ""

        # ruta_id = self.env[("partner.delivery.zone")].search([("name", "=", row[26]), ])
        # if ruta_id:
        #     ruta_id = ruta_id.id
        # else:
        #     ruta_id = ""

        print("/////////CLIENTE//////////")
        print("partner", row)
        print("partner", partner)
        print("nombre:", row[1])

        if partner:
            partner.sudo().write({
                "name": row[1],
                'street': row[3],
                'city': row[4],
                'zip': row[5],
                'phone': row[7],
                'website': row[9],
                'email': row[10],
                'display_name': row[14],
                'company_name': row[15],
                'is_company': 1,
                'active': 1,
                'comment': row[17],
                'lang': "es_ES",
                'state_id': state_id,
                'vat': row[2],
                'country_id': country_id,
                'company_id': company.id,
            })

        else:
            self.env["res.partner"].sudo().create({
                "ref": row[0],
                "name": row[1],
                'street': row[3],
                'city': row[4],
                'zip': row[5],
                'phone': row[7],
                'website': row[9],
                'email': row[10],
                'display_name': row[14],
                'company_name': row[15],
                'is_company': 1,
                'active': 1,
                'comment': row[17],
                'lang': "es_ES",
                'state_id': state_id,
                'vat': row[2],
                'country_id': country_id,
                'company_id': company.id,
            })
    #
    # def _import_bank(self, data_file_bank):
    #     try:
    #         if data_file_bank:
    #             csv_data = reader(StringIO(data_file_bank.decode("utf-8")))
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #
    #     for row in csv_data:
    #         print("--------------------Banco de cliente--------------------------")
    #         self.parse_bank(row)
    #     return
    #
    # def parse_bank(self, row):
    #     partner = self.env["res.partner"].search([("name", "=", row[5]), ])
    #     acc_bank = self.env["res.partner.bank"].search([("acc_number", "=", row[0]), ])
    #
    #     print("/////////Bancos//////////")
    #     print("acc_number", row[0])
    #     print("sanitized_acc_number:", row[1])
    #     print('partner', row[5])
    #
    #     if partner:
    #         if acc_bank:
    #             print("Cuenta de cliente ya existe")
    #         else:
    #             self.env["res.partner.bank"].sudo().create({
    #                 "acc_number": row[0],
    #                 "sanitized_acc_number": row[1],
    #                 'partner_id': partner.id,
    #             })
    #     else:
    #         print("Cliente no existe")
    #
    def _import_category(self, data_file_category):
        try:
            if data_file_category:
                csv_data = reader(StringIO(data_file_category.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            print("--------------------CATEGORY--------------------------")
            print(row)
            self.parse_categories(row)
        return

    def parse_categories(self, row):

        category = self.env["product.category"].search([("name", "=", row[0]),])
        if not category:
            self.env["product.category"].create({
                "name": row[0],
                "parent_id" : 1,
            })

        pos_category = self.env["pos.category"].search([("name", "=", row[0]),])
        if not pos_category:
            self.env["pos.category"].create({
                "name": row[0],
            })

    def _import_product(self, data_file_product):
        try:
            csv_data = reader(StringIO(data_file_product.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for index, row in enumerate(csv_data):
            if index >= 1:
                print("--------------------PRODUCT--------------------------")
                print(row)
                self.parse_products(row)
        return

    def parse_products(self, row):
        taxes_id = self.env["account.tax"].search([("description", "=", row[6]),])
        if taxes_id:
            taxes_id = [(6, 0, [taxes_id.id])]

        supplier_taxes_id = self.env["account.tax"].search([("description", "=", row[7]), ],)
        if supplier_taxes_id:
            supplier_taxes_id = [(6, 0, [supplier_taxes_id.id])]
        else:
            print("impuesto no encontrado", row[7])
            supplier_taxes_id = [(6, 0, [])]

        # company_id = self.env["res.company"].search([("name", "=", row[7])])
        # if company_id:
        #     company_id = company_id.id
        # else:
        #     company_id = self.env.company.id

        category_id = self.env["product.category"].search([("name", "=", row[8])], limit=1)
        if category_id:
            category_id = category_id.id
        else:
            print("categoria no encontrada", row[8])
            category_id = 1

        company = self.env.company

        pos_category = self.env["pos.category"].search([("name", "=", row[8])])
        if pos_category:
            pos_categ_ids = [(6, 0, [pos_category.id])]
        else:
            pos_categ_ids = [(6, 0, [])]

        print("taxes_id", taxes_id)
        print("supplier_taxes_id", supplier_taxes_id)
        print("category_id", category_id)
        # print("company_id", company_id)
        print("pos_categ_ids", pos_categ_ids)

        product = self.env["product.template"].search([("default_code", "=", row[0]), ])
        if not product:
            print("Producto No existe-------------------------------")
            self.env["product.template"].create({
                "default_code": row[0],
                "barcode": row[9],
                "name": row[2],
                "list_price": row[4],
                "standard_price": row[5],
                "type": 'consu',
                "is_storable": True,
                "categ_id": category_id,
                "available_in_pos": True,
                "pos_categ_ids": pos_categ_ids,
                "company_id": company.id,
            })
        else:
            print("Producto existe-------------------------------")
            product.sudo().write({
                "barcode": row[9],
                "name": row[2],
                "list_price": row[4],
                "standard_price": row[5],
                "type": 'consu',
                "is_storable": True,
                "categ_id": category_id,
                "available_in_pos": True,
                "pos_categ_ids": pos_categ_ids,
                "company_id": company.id,
            })
            # "company_id": company_id,
            # "taxes_id": taxes_id,
            # "supplier_taxes_id": supplier_taxes_id,


    def _get_or_create_import_session(self):
        """Obtiene o crea la sesión POS única de importación para la compañía activa.

        Usa un pos.config exclusivo llamado 'importación gestool' para evitar
        el error 'Otra sesión ya está abierta' al compartir config con otras sesiones.
        """
        company = self.env.company

        # 1. Buscar sesión de importación ya existente y activa (cualquier estado no cerrado)
        session = self.env['pos.session'].sudo().search([
            ('config_id.name', '=', 'importación gestool'),
            ('company_id', '=', company.id),
            ('state', 'in', ('opening_control', 'opened')),
        ], limit=1)

        if session:
            # Forzar estado 'opened' si hace falta y devolverla
            if session.state != 'opened':
                session.sudo().write({'state': 'opened'})
            return session

        # 2. Buscar o crear el pos.config exclusivo para importación
        config = self.env['pos.config'].sudo().search([
            ('name', '=', 'importación gestool'),
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], limit=1)

        if not config:
            _logger.info(
                "Creando pos.config 'importación gestool' para la compañía %s.",
                company.name,
            )
            config = self.env['pos.config'].sudo().create({
                'name': 'importación gestool',
                'company_id': company.id,
            })

        # 3. Cerrar cualquier sesión previa en estado cerrado/rescatado para este config
        #    (no hace falta, pero por si acaso aseguramos que no quede ninguna abierta)
        stale = self.env['pos.session'].sudo().search([
            ('config_id', '=', config.id),
            ('state', 'not in', ('closed',)),
        ])
        if stale:
            # Ya existe una sesión no cerrada para este config: reutilizarla
            session = stale[0]
            _logger.info(
                "Reutilizando sesión existente (id=%s, state=%s) para config 'importación gestool'.",
                session.id, session.state,
            )
        else:
            # 4. Crear la sesión nueva
            _logger.info(
                "Creando sesión POS 'importación gestool' para la compañía %s.",
                company.name,
            )
            session = self.env['pos.session'].sudo().create({
                'config_id': config.id,
                'user_id': self.env.uid,
            })

        # 5. Forzar estado 'opened'
        if session.state != 'opened':
            session.sudo().write({'state': 'opened'})

        return session

    def _get_tax_by_amount(self, amount):
        """Busca el impuesto de tipo 'sale' cuyo porcentaje coincide con amount,
        dentro de los impuestos válidos para la localización de la compañía activa."""
        try:
            tax_amount = float(amount)
        except (ValueError, TypeError):
            _logger.warning("Porcentaje de impuesto inválido: %s", amount)
            return self.env['account.tax'].browse()

        company = self.env.company

        # Buscar impuestos de venta con ese porcentaje en la compañía activa
        tax = self.env['account.tax'].sudo().search([
            ('type_tax_use', '=', 'sale'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', tax_amount),
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], limit=1)

        if not tax:
            _logger.warning(
                "No se encontró impuesto de venta con porcentaje %s%% para la compañía %s.",
                tax_amount, company.name,
            )
        else:
            _logger.info(
                "Impuesto encontrado: %s (%s%%) id=%s",
                tax.name, tax_amount, tax.id,
            )
        return tax

    def _import_ticket(self, data_file_ticket):
        try:
            csv_data = list(reader(StringIO(data_file_ticket.decode("utf-8"))))
        except Exception:
            raise UserError(_("Can not read the file"))

        session = self._get_or_create_import_session()
        processed_order_ids = set()

        for index, row in enumerate(csv_data):
            if index >= 1:
                order = self.parse_ticket(row, session)
                if order:
                    processed_order_ids.add(order.id)

        _logger.info("Total pedidos a confirmar/facturar: %d", len(processed_order_ids))

        # Una vez procesadas todas las líneas, confirmar, pagar y facturar cada pedido
        for order_id in processed_order_ids:
            pos_order = self.env['pos.order'].sudo().browse(order_id)
            if pos_order.exists() and pos_order.state == 'draft':
                self._confirm_and_invoice_order(pos_order)
        return

    def parse_ticket(self, row, session):

        _logger.info(
            "Ticket: partner=%s, pos_reference=%s, product=%s, qty=%s, price=%s, tax%%=%s",
            row[9], row[3], row[15], row[17], row[16], row[18] if len(row) > 18 else 'N/A',
        )

        company = self.env.company

        # Entorno con sudo y contexto de compañía correcta
        env = self.env(
            su=True,
            context=dict(self.env.context, allowed_company_ids=[company.id], force_company=company.id),
        )

        partner = env["res.partner"].search([("ref", "=", row[9])], limit=1)
        product = env['product.product'].search([('default_code', '=', row[15])], limit=1)

        if not product:
            _logger.warning("Producto no encontrado con código: %s (pos_reference: %s)", row[15], row[3])

        # Resolver impuesto por porcentaje desde row[18]
        tax_amount_raw = row[18] if len(row) > 18 else None
        tax = self._get_tax_by_amount(tax_amount_raw) if tax_amount_raw else env['account.tax'].browse()
        tax_cmd = [(6, 0, [tax.id])] if tax else [(6, 0, [])]

        qty = float(row[17]) if row[17] else 1.0
        price_unit = float(row[16]) if row[16] else 0.0
        tax_amount = float(tax.amount) if tax else 0.0

        amount_untaxed = qty * price_unit
        line_tax = round(amount_untaxed * tax_amount / 100, 2)
        amount_total = round(amount_untaxed + line_tax, 2)

        line_vals = (0, 0, {
            'product_id': product.id if product else False,
            'qty': qty,
            'price_unit': price_unit,
            'price_subtotal': amount_untaxed,
            'price_subtotal_incl': amount_total,
            'tax_ids': tax_cmd,
            'company_id': company.id,
        })

        pos_order = env["pos.order"].search([
            ("pos_reference", "=", row[3]),
            ("company_id", "=", company.id),
        ], limit=1)

        # Parsear fecha del ticket desde row[5]
        try:
            date_order = fields.Datetime.from_string(row[5]) if row[5] else fields.Datetime.now()
        except Exception:
            try:
                from datetime import datetime as dt
                date_order = dt.strptime(row[5], "%d/%m/%Y %H:%M:%S")
            except Exception:
                try:
                    from datetime import datetime as dt
                    date_order = dt.strptime(row[5], "%d/%m/%Y")
                except Exception:
                    _logger.warning("No se pudo parsear la fecha '%s', usando fecha actual.", row[5])
                    date_order = fields.Datetime.now()

        if not pos_order:
            pos_order = env["pos.order"].create({
                "pos_reference": row[3],
                "partner_id": partner.id if partner else False,
                "session_id": session.id,
                "company_id": company.id,
                "date_order": date_order,
                "amount_tax": line_tax,
                "amount_total": amount_total,
                "amount_paid": 0.0,
                "amount_return": 0.0,
                "lines": [line_vals],
            })
            _logger.info("Pedido creado: %s (id=%s)", row[3], pos_order.id)
        else:
            _logger.info("Pedido existe, añadiendo línea: %s", row[3])
            pos_order.write({
                "amount_tax": pos_order.amount_tax + line_tax,
                "amount_total": pos_order.amount_total + amount_total,
                "lines": [line_vals],
            })

        return pos_order

    def _confirm_and_invoice_order(self, pos_order):
        """Registra pago en efectivo, marca el pedido como pagado y genera factura."""
        company = pos_order.company_id

        # Entorno con sudo y contexto de compañía correcta
        env = self.env(
            su=True,
            context=dict(self.env.context, allowed_company_ids=[company.id], force_company=company.id),
        )

        # 1. Buscar método de pago en efectivo del config de la sesión
        # 'type' es computed no almacenado → filtrar por journal_id.type = 'cash'
        cash_pm = env['pos.payment.method'].search([
            ('config_ids', 'in', pos_order.config_id.id),
            ('journal_id.type', '=', 'cash'),
        ], limit=1)

        if not cash_pm:
            # Fallback: cualquier método de pago en efectivo de la compañía
            cash_pm = env['pos.payment.method'].search([
                ('company_id', '=', company.id),
                ('journal_id.type', '=', 'cash'),
            ], limit=1)

        if not cash_pm:
            _logger.error(
                "No se encontró método de pago en efectivo para el pedido %s. "
                "Asegúrate de que el pos.config 'importación gestool' tiene un método de pago en efectivo.",
                pos_order.pos_reference,
            )
            return

        _logger.info(
            "Usando método de pago '%s' (id=%s) para pedido %s",
            cash_pm.name, cash_pm.id, pos_order.pos_reference,
        )

        # 2. Crear el pago en efectivo por el importe total del pedido
        env['pos.payment'].create({
            'pos_order_id': pos_order.id,
            'payment_method_id': cash_pm.id,
            'amount': pos_order.amount_total,
            'payment_date': pos_order.date_order,
            'company_id': company.id,
        })

        # 3. Actualizar amount_paid en el pedido
        env['pos.order'].browse(pos_order.id).write({
            'amount_paid': pos_order.amount_total,
            'company_id': company.id,
        })

        # 4. Marcar el pedido como pagado
        env['pos.order'].browse(pos_order.id).action_pos_order_paid()
        _logger.info("Pedido %s marcado como pagado (state=%s).", pos_order.pos_reference, pos_order.state)

        # 5. Marcar para facturar y generar la factura
        env['pos.order'].browse(pos_order.id).write({'to_invoice': True})
        env['pos.order'].browse(pos_order.id).with_context(generate_pdf=False)._generate_pos_order_invoice()
        _logger.info("Factura generada para el pedido %s (factura=%s).", pos_order.pos_reference, pos_order.account_move)

    # def _import_property(self, data_file_property):
    #     try:
    #         csv_data = reader(StringIO(data_file_property.decode("utf-8")))
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #
    #     for index, row in enumerate(csv_data):
    #         if index >= 1:
    #             print("--------------------Propiedades--------------------------")
    #             print(row)
    #             self.parse_property(row)
    #     return
    #
    # def parse_property(self, row):
    #
    #     print("Propiedades-------------------------------")
    #
    #     # Crear o buscar el atributo
    #     attribute = self.env["product.attribute"].search([("name", "=", row[0])],)
    #     if not attribute:
    #         attribute = self.env["product.attribute"].create({"name": row[0]})
    #
    #     # Crear o buscar el valor del atributo
    #     value = self.env["product.attribute.value"].search([
    #         ("name", "=", row[2]),
    #         ("attribute_id", "=", attribute.id)
    #     ], )
    #     if not value:
    #         self.env["product.attribute.value"].create({
    #             "name": row[2],
    #             "attribute_id": attribute.id,
    #         })
    #
    # # # def _import_agentes(self, data_file_agentes):
    # # #     try:
    # # #         if data_file_agentes:
    # # #             csv_data = reader(StringIO(data_file_agentes.decode("utf-8")))
    # # #     except Exception:
    # # #         raise UserError(_("Can not read the file"))
    # # #
    # # #     for row in csv_data:
    # # #         print("--------------------AGENTES--------------------------")
    # # #         # self.parse_agentes(row)
    # # #     return
    # #
    # # # def parse_agentes(self, row):
    # # #     agente = self.env["res.partner"].search([("ref", "=", row[0]), ])
    # # #     if agente:
    # # #         agente.write({
    # # #             "name": row[1],
    # # #             'email': row[10],
    # # #             'display_name': row[1],
    # # #             'is_company': 0,
    # # #             'active': 1,
    # # #             'customer_rank': 0,
    # # #             'supplier_rank': 0,
    # # #             'agent':1,
    # # #         })
    # # #     else:
    # # #         self.env["res.partner"].create({
    # # #             "ref": row[0],
    # # #             "name": row[1],
    # # #             'email': row[10],
    # # #             'display_name': row[1],
    # # #             'is_company': 0,
    # # #             'active': 1,
    # # #             'customer_rank': 0,
    # # #             'supplier_rank': 0,
    # # #             'agent':1,
    # # #         })
