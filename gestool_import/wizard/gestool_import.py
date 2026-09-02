import logging
from base64 import b64decode
from decimal import Decimal, InvalidOperation
from io import StringIO
from math import isfinite
import re
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

    _IMPORT_FILE_SPECS = (
        ("partner_attachment_ids", "data_file_partner", "filename_partner", "_import_partner"),
        ("category_attachment_ids", "data_file_category", "filename_category", "_import_category"),
        ("product_attachment_ids", "data_file_product", "filename_product", "_import_product"),
        ("ticket_attachment_ids", "data_file_ticket", "filename_ticket", "_import_ticket"),
        (
            "supplier_info_attachment_ids",
            "data_file_supplier_info",
            "filename_supplier_info",
            "_import_supplier_info",
        ),
        (
            "multiple_barcodes_attachment_ids",
            "data_file_multiple_barcodes",
            "filename_multiple_barcodes",
            "_import_multiple_barcodes",
        ),
    )

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
    partner_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="gestool_import_partner_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Ficheros de clientes/proveedores",
        copy=False,
    )
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
    category_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="gestool_import_category_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Ficheros de categorías",
        copy=False,
    )

    data_file_product = fields.Binary(
        string="Product to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_product = fields.Char()
    product_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="gestool_import_product_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Ficheros de productos",
        copy=False,
    )

    data_file_ticket = fields.Binary(
        string="Tickets header to import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_ticket = fields.Char()
    ticket_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="gestool_import_ticket_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Ficheros de tickets",
        copy=False,
    )

    data_file_supplier_info = fields.Binary(
        string="Supplier Info to Import",
        required=False,
        help="CSV con dos columnas: código de producto (default_code) y referencia del proveedor (ref).",
    )
    filename_supplier_info = fields.Char()
    supplier_info_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="gestool_import_supplier_info_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Ficheros de proveedores de producto",
        copy=False,
    )

    data_file_multiple_barcodes = fields.Binary(
        string="Multiples códigos de barras para importar",
        required=False,
        help="CSV o XLS con dos columnas: referencia y código de barras.",
    )
    filename_multiple_barcodes = fields.Char()
    multiple_barcodes_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="gestool_import_multiple_barcodes_attachment_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Ficheros de códigos de barras",
        copy=False,
    )
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

    def _iter_import_files(self, attachment_field, legacy_field, filename_field):
        """Yield queued files in upload order, retaining the old binary API."""
        for attachment in self[attachment_field].sorted("id"):
            yield attachment.name, b64decode(attachment.datas or b"")

        if self[legacy_field]:
            yield self[filename_field] or _("Fichero sin nombre"), b64decode(
                self[legacy_field]
            )

    def import_file(self):
        """Import all selected files sequentially without stopping on errors."""
        self.ensure_one()
        processed = 0
        errors = []
        warnings = []

        for attachment_field, legacy_field, filename_field, method_name in (
            self._IMPORT_FILE_SPECS
        ):
            for filename, file_data in self._iter_import_files(
                attachment_field, legacy_field, filename_field
            ):
                if not file_data:
                    errors.append(_("%(file)s: el fichero está vacío", file=filename))
                    continue

                try:
                    with self.env.cr.savepoint():
                        result = getattr(self, method_name)(file_data)
                except Exception as error:
                    _logger.exception("Error importando el fichero Gestool %s", filename)
                    errors.append(_("%(file)s: %(error)s", file=filename, error=error))
                    continue

                # Confirmar cada fichero en cuanto termina de procesarse, en vez
                # de dejarlo todo en la transacción abierta del wizard. Sin esto,
                # si un fichero posterior tarda demasiado y el worker se recicla
                # por --limit-time-cpu, se deshacen TAMBIÉN los ficheros previos
                # ya procesados con éxito en la misma llamada (visto en
                # producción real en parafarmacias-del-sur, 2026-09-02: un
                # import con varios ficheros perdió el trabajo completo por el
                # límite de CPU a mitad del último fichero). Con el commit aquí,
                # una interrupción posterior solo pierde el fichero en curso.
                self.env.cr.commit()

                processed += 1
                if isinstance(result, dict) and result.get("params", {}).get("message"):
                    warnings.append("%s: %s" % (
                        filename,
                        result["params"]["message"],
                    ))

        if not processed and not errors:
            raise UserError(_("Selecciona al menos un fichero para importar."))

        details = []
        if processed:
            details.append(_("Ficheros procesados: %s", processed))
        if warnings:
            details.append(_("Avisos:\n%s", "\n".join(warnings)))
        if errors:
            details.append(_("Errores:\n%s", "\n".join(errors)))

        notification_type = "danger" if errors else "warning" if warnings else "success"
        result = {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Importación Gestool finalizada"),
                "message": "\n\n".join(details),
                "type": notification_type,
                "sticky": bool(errors or warnings),
            },
        }
        if not errors and not warnings:
            result["params"]["next"] = {"type": "ir.actions.act_window_close"}
        return result
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
                "taxes_id": taxes_id,
                "supplier_taxes_id": supplier_taxes_id,
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
                "taxes_id": taxes_id,
                "supplier_taxes_id": supplier_taxes_id,
            })
            # "company_id": company_id,
            # "taxes_id": taxes_id,
            # "supplier_taxes_id": supplier_taxes_id,


    def _get_ticket_pos_config(self, pos_name):
        """Resuelve de forma inequívoca el TPV indicado en la octava columna."""
        pos_name = (pos_name or "").strip()
        if not pos_name:
            return self.env['pos.config'].browse()
        configs = self.env['pos.config'].sudo().search([
            ('name', '=', pos_name),
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ], limit=2)
        return configs if len(configs) == 1 else self.env['pos.config'].browse()

    def _get_import_pricelist(self, config, partner=None):
        """Obtiene una tarifa válida sin alterar los precios recibidos del CSV."""
        config.ensure_one()
        company = config.company_id
        currency = config.currency_id

        candidates = config.pricelist_id
        if partner:
            candidates |= partner.with_company(company).property_product_pricelist
        candidates |= config.available_pricelist_ids
        pricelist = candidates.filtered(
            lambda item: item.active
            and item.currency_id == currency
            and (not item.company_id or item.company_id == company)
        )[:1]
        if pricelist:
            return pricelist

        Pricelist = self.env['product.pricelist'].sudo().with_company(company)
        base_domain = [
            ('active', '=', True),
            ('currency_id', '=', currency.id),
        ]
        pricelist = Pricelist.search(
            base_domain + [('company_id', '=', company.id)], limit=1
        ) or Pricelist.search(
            base_domain + [('company_id', '=', False)], limit=1
        )
        if not pricelist:
            raise UserError(_(
                "No se ha encontrado una tarifa activa en %(currency)s para el "
                "punto de venta '%(pos)s'. Configura una tarifa predeterminada "
                "en el punto de venta antes de importar.",
                currency=currency.display_name,
                pos=config.name,
            ))
        return pricelist

    def _create_import_session(self, config):
        """Crea y abre una sesión aislada 0000 para un TPV existente."""
        config.ensure_one()
        cash_method = self._ensure_import_cash_payment_method(config)
        if not cash_method.journal_id.loss_account_id or not cash_method.journal_id.profit_account_id:
            raise UserError(_(
                "El diario de efectivo '%(journal)s' del punto de venta '%(pos)s' "
                "debe tener configuradas las cuentas de pérdidas y ganancias para "
                "poder cerrar automáticamente la sesión 0000.",
                journal=cash_method.journal_id.name,
                pos=config.name,
            ))
        session = self.env['pos.session'].sudo().create({
            'config_id': config.id,
            'user_id': self.env.uid,
            'rescue': True,
        })
        session.set_opening_control(0.0, _("Importación Gestool"))
        session.sudo().write({'name': '0000'})
        _logger.info(
            "Sesión 0000 creada y abierta para el TPV '%s' (id=%s).",
            config.name, session.id,
        )
        return session

    def _close_import_session(self, session):
        """Cuenta el efectivo teórico y cierra contablemente la sesión 0000."""
        session.ensure_one()
        cash_method = session.payment_method_ids.filtered('is_cash_count')[:1]
        cash_payments = session.order_ids.payment_ids.filtered(
            lambda payment: payment.payment_method_id == cash_method
            and payment.pos_order_id.state in ('paid', 'invoiced', 'done')
        )
        counted_cash = (
            session.cash_register_balance_start
            + sum(session.statement_line_ids.mapped('amount'))
            + sum(cash_payments.mapped('amount'))
        )
        session.post_closing_cash_details(counted_cash)
        session.invalidate_recordset([
            'cash_register_balance_end',
            'cash_register_difference',
        ])
        result = session.close_session_from_ui()
        if not result.get('successful') or session.state != 'closed':
            raise UserError(_(
                "No se pudo cerrar la sesión 0000 del punto de venta %(pos)s: %(reason)s",
                pos=session.config_id.name,
                reason=result.get('message') or _("motivo desconocido"),
            ))
        _logger.info(
            "Sesión 0000 cerrada para el TPV '%s' (id=%s).",
            session.config_id.name, session.id,
        )

    def _ensure_import_cash_payment_method(self, config):
        """Devuelve el método de efectivo configurado en el TPV del CSV."""
        config.ensure_one()
        cash_method = config.payment_method_ids.filtered(
            lambda method: method.active and method.journal_id.type == 'cash'
        )[:1]
        if cash_method:
            return cash_method
        raise UserError(_(
            "El punto de venta '%s' no tiene configurado ningún método de pago en efectivo. "
            "Configúralo antes de importar para no modificar una sesión de venta que pueda estar abierta.",
            config.name,
        ))

    def _replace_order_payments_with_cash(self, pos_order, cash_method):
        """Deja exactamente un pago en efectivo por el total del pedido."""
        pos_order.ensure_one()
        cash_method.ensure_one()
        pos_order._clean_payment_lines()
        pos_order.add_payment({
            'pos_order_id': pos_order.id,
            'payment_method_id': cash_method.id,
            'amount': pos_order.amount_total,
            'payment_date': pos_order.date_order,
        })
        return pos_order.payment_ids

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

    def _get_ticket_product(self, product_code, env=None):
        """Resuelve el producto de una línea Gestool en la compañía activa."""
        env = env or self.env
        product_code = (product_code or "").strip()
        if not product_code:
            return env['product.product'].browse()

        company = env.company
        return env['product.product'].search([
            ('default_code', '=', product_code),
            ('active', '=', True),
            '|',
            ('company_id', '=', company.id),
            ('company_id', '=', False),
        ], limit=1)

    def _parse_ticket_number(self, value, default, field_name):
        """Convierte un dato numérico del CSV y rechaza marcadores no válidos."""
        raw_value = (value or "").strip()
        if not raw_value:
            return default
        try:
            number = float(raw_value)
        except (TypeError, ValueError):
            number = None
        if number is None or not isfinite(number):
            raise UserError(_(
                "Valor numérico inválido en %(field)s: '%(value)s'.",
                field=field_name,
                value=raw_value,
            ))
        return number

    def _ticket_import_warning(
        self, invalid_tickets, malformed_lines, invalid_pos_tickets=None,
        mixed_pos_tickets=None, negative_tickets=None,
        invalid_numeric_tickets=None,
    ):
        """Construye una notificación legible sin desbordar el cliente web."""
        invalid_pos_tickets = invalid_pos_tickets or {}
        mixed_pos_tickets = mixed_pos_tickets or {}
        negative_tickets = negative_tickets or {}
        invalid_numeric_tickets = invalid_numeric_tickets or {}
        details = []
        for reference, product_codes in list(invalid_tickets.items())[:20]:
            details.append(_(
                "Ticket %(ticket)s: producto(s) %(products)s",
                ticket=reference,
                products=", ".join(sorted(product_codes)),
            ))
        if len(invalid_tickets) > 20:
            details.append(_("… y %d ticket(s) más", len(invalid_tickets) - 20))
        if malformed_lines:
            details.append(_(
                "Filas con formato incompleto omitidas: %s",
                ", ".join(str(line) for line in malformed_lines[:20]),
            ))
        for reference, pos_name in list(invalid_pos_tickets.items())[:20]:
            details.append(_(
                "Ticket %(ticket)s: punto de venta '%(pos)s' no encontrado o duplicado",
                ticket=reference,
                pos=pos_name or _("(vacío)"),
            ))
        for reference, pos_names in list(mixed_pos_tickets.items())[:20]:
            details.append(_(
                "Ticket %(ticket)s: aparece en varios puntos de venta (%(points)s)",
                ticket=reference,
                points=", ".join(sorted(pos_names)),
            ))
        for reference, amount in list(negative_tickets.items())[:20]:
            details.append(_(
                "Ticket %(ticket)s omitido: total negativo (%(amount)s)",
                ticket=reference,
                amount=amount,
            ))
        for reference, errors in list(invalid_numeric_tickets.items())[:20]:
            details.append(_(
                "Ticket %(ticket)s omitido: valor(es) numérico(s) inválido(s): %(errors)s",
                ticket=reference,
                errors=", ".join(sorted(errors)),
            ))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Importación Gestool completada con avisos"),
                'message': _(
                    "Se omitieron ventas para evitar pedidos no válidos. "
                    "Revisa los detalles antes de volver a importar el CSV.\n%s",
                    "\n".join(details),
                ),
                'type': 'warning',
                'sticky': True,
            },
        }

    def _import_ticket(self, data_file_ticket):
        try:
            csv_data = list(reader(StringIO(data_file_ticket.decode("utf-8"))))
        except Exception:
            raise UserError(_("Can not read the file"))

        data_rows = list(enumerate(csv_data[1:], start=2))
        invalid_tickets = {}
        invalid_pos_tickets = {}
        mixed_pos_tickets = {}
        invalid_numeric_tickets = {}
        malformed_lines = []
        ticket_pos_names = {}
        ticket_totals = {}
        configs_by_name = {}

        # Validar el fichero completo antes de crear pedidos. Si falla una línea,
        # se omite su ticket entero para no generar una venta/factura parcial.
        for line_number, row in data_rows:
            if len(row) < 18 or not row[3].strip():
                malformed_lines.append(line_number)
                continue

            ticket_reference = row[3].strip()
            pos_name = row[7].strip()
            ticket_pos_names.setdefault(ticket_reference, set()).add(pos_name)
            if len(ticket_pos_names[ticket_reference]) > 1:
                mixed_pos_tickets[ticket_reference] = ticket_pos_names[ticket_reference]

            if pos_name not in configs_by_name:
                configs_by_name[pos_name] = self._get_ticket_pos_config(pos_name)
            if not configs_by_name[pos_name]:
                invalid_pos_tickets[ticket_reference] = pos_name

            product_code = row[15].strip() if len(row) > 15 else ""
            if not self._get_ticket_product(product_code):
                invalid_tickets.setdefault(ticket_reference, set()).add(
                    product_code or _("(código vacío)")
                )

            numbers = {}
            for index, field_name, default in (
                (16, _("precio"), 0.0),
                (17, _("cantidad"), 1.0),
            ):
                try:
                    numbers[index] = self._parse_ticket_number(
                        row[index], default, field_name
                    )
                except UserError:
                    invalid_numeric_tickets.setdefault(
                        ticket_reference, set()
                    ).add(_(
                        "fila %(line)s, %(field)s '%(value)s'",
                        line=line_number,
                        field=field_name,
                        value=(row[index] or "").strip(),
                    ))
            if ticket_reference in invalid_numeric_tickets:
                continue

            price_unit = numbers[16]
            qty = numbers[17]
            tax = self._get_tax_by_amount(row[18]) if len(row) > 18 and row[18] else False
            tax_amount = float(tax.amount) if tax else 0.0
            amount_untaxed = qty * price_unit
            line_total = round(
                amount_untaxed + amount_untaxed * tax_amount / 100, 2
            )
            ticket_totals[ticket_reference] = (
                ticket_totals.get(ticket_reference, 0.0) + line_total
            )

        negative_tickets = {}
        for reference, total in ticket_totals.items():
            pos_names = ticket_pos_names.get(reference, set())
            if len(pos_names) != 1:
                continue
            config = configs_by_name.get(next(iter(pos_names)))
            if config and config.currency_id.compare_amounts(total, 0.0) < 0:
                negative_tickets[reference] = config.currency_id.format(total)

        valid_rows = [
            row for _line_number, row in data_rows
            if len(row) >= 18
            and row[3].strip()
            and row[3].strip() not in invalid_tickets
            and row[3].strip() not in invalid_pos_tickets
            and row[3].strip() not in mixed_pos_tickets
            and row[3].strip() not in negative_tickets
            and row[3].strip() not in invalid_numeric_tickets
        ]

        rows_by_config = {}
        for row in valid_rows:
            config = configs_by_name[row[7].strip()]
            rows_by_config.setdefault(config.id, []).append(row)

        total_processed_orders = 0
        for config_id, config_rows in rows_by_config.items():
            config = self.env['pos.config'].sudo().browse(config_id)
            session = self._create_import_session(config)
            processed_order_ids = set()
            for row in config_rows:
                order = self.parse_ticket(row, session)
                if order:
                    processed_order_ids.add(order.id)

            for index, order_id in enumerate(processed_order_ids, start=1):
                pos_order = self.env['pos.order'].sudo().browse(order_id)
                if pos_order.exists() and pos_order.state == 'draft':
                    self._confirm_and_invoice_order(pos_order)
                # Confirmar cada 10 pedidos, no solo al terminar el fichero
                # entero. Un fichero de un único TPV puede contener miles de
                # tickets y tardar más CPU de la que --limit-time-cpu permite
                # aunque el límite ya se haya subido una vez (visto en
                # producción real en parafarmacias-del-sur, 2026-09-02: con
                # --limit-time-cpu=3600 seguía matando el worker a mitad de
                # fichero). Con este commit periódico, una interrupción
                # posterior solo pierde como mucho los últimos 9 pedidos, no
                # el fichero completo. Aviso: si la interrupción cae justo
                # aquí, la sesión 0000 de este TPV puede quedar abierta sin
                # cerrar (los pedidos ya confirmados/facturados persisten
                # igualmente) — revisar manualmente en ese caso.
                if index % 10 == 0:
                    self.env.cr.commit()
            self._close_import_session(session)
            self.env.cr.commit()
            total_processed_orders += len(processed_order_ids)

        _logger.info("Total pedidos importados: %d", total_processed_orders)
        if (
            invalid_tickets or malformed_lines or invalid_pos_tickets
            or mixed_pos_tickets or negative_tickets or invalid_numeric_tickets
        ):
            return self._ticket_import_warning(
                invalid_tickets,
                malformed_lines,
                invalid_pos_tickets,
                mixed_pos_tickets,
                negative_tickets,
                invalid_numeric_tickets,
            )
        return True

    def parse_ticket(self, row, session):

        _logger.info(
            "Ticket: partner=%s, pos_reference=%s, product=%s, qty=%s, price=%s, tax%%=%s",
            row[9], row[3], row[15], row[17], row[16], row[18] if len(row) > 18 else 'N/A',
        )

        company = session.company_id

        # Entorno con sudo y contexto de compañía correcta
        env = self.env(
            su=True,
            context=dict(self.env.context, allowed_company_ids=[company.id], force_company=company.id),
        )

        partner = env["res.partner"].search([("ref", "=", row[9])], limit=1)
        product_code = row[15].strip()
        product = self._get_ticket_product(product_code, env=env)

        if not product:
            _logger.warning(
                "Línea omitida: producto no encontrado con código '%s' (pos_reference: %s)",
                product_code, row[3],
            )
            return False

        pricelist = self._get_import_pricelist(session.config_id, partner)

        # Resolver impuesto por porcentaje desde row[18]
        tax_amount_raw = row[18] if len(row) > 18 else None
        tax = self._get_tax_by_amount(tax_amount_raw) if tax_amount_raw else env['account.tax'].browse()
        tax_cmd = [(6, 0, [tax.id])] if tax else [(6, 0, [])]

        qty = self._parse_ticket_number(row[17], 1.0, _("cantidad"))
        price_unit = self._parse_ticket_number(row[16], 0.0, _("precio"))
        tax_amount = float(tax.amount) if tax else 0.0

        amount_untaxed = qty * price_unit
        line_tax = round(amount_untaxed * tax_amount / 100, 2)
        amount_total = round(amount_untaxed + line_tax, 2)

        line_vals = (0, 0, {
            'product_id': product.id,
            'qty': qty,
            'price_unit': price_unit,
            'price_subtotal': amount_untaxed,
            'price_subtotal_incl': amount_total,
            'tax_ids': tax_cmd,
            'company_id': company.id,
        })

        pos_order = env["pos.order"].search([
            ("pos_reference", "=", row[3]),
            ("session_id", "=", session.id),
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
                "pricelist_id": pricelist.id,
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

        # 1. La forma de pago del CSV se ignora siempre. El TPV de importación
        # dispone de su propio método de efectivo y el pedido queda con un solo pago.
        cash_pm = self._ensure_import_cash_payment_method(pos_order.config_id)

        _logger.info(
            "Usando método de pago '%s' (id=%s) para pedido %s",
            cash_pm.name, cash_pm.id, pos_order.pos_reference,
        )

        # 2. Sustituir cualquier pago previo por efectivo por el importe total.
        pos_order = env['pos.order'].browse(pos_order.id)
        self._replace_order_payments_with_cash(pos_order, cash_pm)

        # 3. Marcar el pedido como pagado
        env['pos.order'].browse(pos_order.id).action_pos_order_paid()
        _logger.info("Pedido %s marcado como pagado (state=%s).", pos_order.pos_reference, pos_order.state)

        # 4. Marcar para facturar y generar la factura
        env['pos.order'].browse(pos_order.id).write({'to_invoice': True})
        env['pos.order'].browse(pos_order.id).with_context(generate_pdf=False)._generate_pos_order_invoice()
        _logger.info("Factura generada para el pedido %s (factura=%s).", pos_order.pos_reference, pos_order.account_move)

    def _import_supplier_info(self, data_file_supplier_info):
        """Importa la relación de proveedores de un producto desde un CSV.

        Columnas del CSV:
            0 - default_code  (código interno del producto)
            1 - ref           (referencia del proveedor en res.partner)
        """
        try:
            csv_data = reader(StringIO(data_file_supplier_info.decode("utf-8")))
        except Exception:
            raise UserError(_("No se puede leer el fichero de proveedores de producto"))

        for index, row in enumerate(csv_data):
            if len(row) < 2:
                _logger.warning("Fila %d ignorada (menos de 2 columnas): %s", index, row)
                continue
            _logger.info(
                "-------- Proveedor de producto: default_code=%s, proveedor_ref=%s --------",
                row[0], row[1],
            )
            self.parse_supplier_info(row)

    def parse_supplier_info(self, row):
        """Crea o actualiza la línea de proveedor (product.supplierinfo) para un producto.

        Args:
            row[0]: default_code del producto (product.template)
            row[1]: ref del proveedor (res.partner)
        """
        product_code = row[0].strip()
        supplier_ref = row[1].strip()

        # Buscar el producto por su código interno
        product = self.env["product.template"].search(
            [("default_code", "=", product_code)], limit=1
        )
        if not product:
            _logger.warning(
                "Producto no encontrado con default_code='%s'. Fila omitida.", product_code
            )
            return

        # Buscar el proveedor por su referencia interna
        partner = self.env["res.partner"].search(
            [("ref", "=", supplier_ref)], limit=1
        )
        if not partner:
            _logger.warning(
                "Proveedor no encontrado con ref='%s'. Fila omitida.", supplier_ref
            )
            return

        # Comprobar si ya existe la relación proveedor-producto
        existing = self.env["product.supplierinfo"].search(
            [
                ("product_tmpl_id", "=", product.id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )

        if existing:
            _logger.info(
                "La relación proveedor ya existe: producto='%s', proveedor='%s'. No se crea duplicado.",
                product_code, supplier_ref,
            )
        else:
            self.env["product.supplierinfo"].sudo().create(
                {
                    "product_tmpl_id": product.id,
                    "partner_id": partner.id,
                }
            )
            _logger.info(
                "Relación proveedor creada: producto='%s' (id=%s), proveedor='%s' (id=%s).",
                product_code, product.id, supplier_ref, partner.id,
            )

    def _import_multiple_barcodes(self, data_file_multiple_barcodes):
        """Importa relaciones de códigos de barras desde CSV o Excel XLS.

        La primera fila de Excel es la cabecera. En cada fila posterior, la
        columna A es ``default_code`` y la B es el código de barras.
        """
        is_xls = data_file_multiple_barcodes.startswith(b"\xd0\xcf\x11\xe0")
        if is_xls:
            rows = self._read_xls_barcodes(data_file_multiple_barcodes)
        else:
            try:
                rows = reader(StringIO(data_file_multiple_barcodes.decode("utf-8")))
            except (UnicodeDecodeError, TypeError):
                raise UserError(_("No se puede leer el fichero de códigos de barras"))

        company = self.env.company
        counters = {
            "created": 0,
            "existing": 0,
            "conflict": 0,
            "missing_product": 0,
            "invalid": 0,
        }
        _logger.info(
            "======== Importación de códigos de barras | Compañía: %s (id=%s) ========",
            company.name, company.id,
        )

        for index, row in enumerate(rows, start=2 if is_xls else 1):
            if not is_xls and index == 1 and self._is_barcode_header(row):
                continue
            if len(row) < 2:
                _logger.warning("Fila %d ignorada (menos de 2 columnas): %s", index, row)
                counters["invalid"] += 1
                continue
            result = self.parse_multiple_barcodes(row, company)
            counters[result] += 1

        return {
            "params": {
                "message": _(
                    "Creados: %(created)s | Ya existentes: %(existing)s | "
                    "Conflictos ignorados: %(conflict)s | Productos no encontrados: "
                    "%(missing_product)s | Filas inválidas: %(invalid)s",
                    **counters,
                )
            }
        }

    @staticmethod
    def _is_barcode_header(row):
        """Detecta la cabecera habitual del fichero de códigos."""
        header = [str(value).strip().lower() for value in row[:2]]
        return header in (
            ["referencia", "codigo_barras"],
            ["referencia", "código_barras"],
            ["default_code", "barcode"],
        )

    def _read_xls_barcodes(self, file_data):
        """Devuelve las dos primeras columnas de un XLS, omitiendo la cabecera."""
        try:
            import xlrd
        except ImportError as error:
            _logger.exception("No se puede leer el Excel de códigos de barras")
            raise UserError(_("No se puede leer el fichero XLS de códigos de barras")) from error

        try:
            workbook = xlrd.open_workbook(file_contents=file_data)
            sheet = workbook.sheet_by_index(0)
        except (TypeError, ValueError, IndexError, xlrd.biffh.XLRDError) as error:
            _logger.exception("No se puede leer el Excel de códigos de barras")
            raise UserError(_("No se puede leer el fichero XLS de códigos de barras")) from error

        rows = []
        for row_index in range(1, sheet.nrows):
            rows.append([
                self._normalize_import_value(sheet.cell_value(row_index, column))
                for column in (0, 1)
            ])
        return rows

    @staticmethod
    def _normalize_import_value(value):
        """Normaliza números de Excel sin perder ceros iniciales en cadenas."""
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if isinstance(value, float) or re.fullmatch(r"\d+\.00+", text):
            try:
                decimal_value = Decimal(text)
            except InvalidOperation:
                return text
            if decimal_value == decimal_value.to_integral_value():
                return str(decimal_value.quantize(Decimal("1")))
        return text

    def parse_multiple_barcodes(self, row, company=None):
        """Crea o verifica códigos de barras adicionales para un producto en product.barcode.

        Args:
            row[0]: default_code del producto (product.template)
            row[1]: código de barras a registrar
            company: res.company activo (opcional, se toma de self.env.company si no se pasa)
        """
        if company is None:
            company = self.env.company

        product_code = self._normalize_import_value(row[0])
        barcode = self._normalize_import_value(row[1])

        _logger.info(
            "Procesando: default_code='%s', barcode='%s' | Compañía: %s (id=%s)",
            product_code, barcode, company.name, company.id,
        )

        if not product_code or not barcode:
            _logger.warning(
                "Fila ignorada: default_code='%s', barcode='%s' (valores vacíos).",
                product_code, barcode,
            )
            return "invalid"

        # Buscar el producto por código interno filtrando por compañía
        product_tmpl = self.env["product.template"].search(
            [
                ("default_code", "=", product_code),
                "|",
                ("company_id", "=", company.id),
                ("company_id", "=", False),
            ],
            limit=1,
        )
        if not product_tmpl:
            _logger.warning(
                "Producto no encontrado con default_code='%s' en la compañía '%s' (id=%s). Fila omitida.",
                product_code, company.name, company.id,
            )
            return "missing_product"

        # Obtener la variante del producto
        product = product_tmpl.product_variant_ids[:1]
        if not product:
            _logger.warning(
                "El producto '%s' no tiene variantes. Fila omitida.", product_code
            )
            return "invalid"

        # Comprobar si el código de barras ya existe en product.barcode
        existing = self.env["product.barcode"].search(
            [("name", "=", barcode)], limit=1
        )
        if existing:
            _logger.info(
                "El código de barras '%s' ya existe (id=%s, producto='%s', compañía='%s'). No se crea duplicado.",
                barcode, existing.id, existing.product_id.display_name,
                existing.company_id.name or "sin compañía",
            )
            return "existing" if existing.product_id == product else "conflict"

        # Crear el registro en product.barcode
        self.env["product.barcode"].sudo().create({
            "name": barcode,
            "product_id": product.id,
            "product_tmpl_id": product_tmpl.id,
        })
        _logger.info(
            "Código de barras creado: '%s' → producto '%s' (id=%s) | Compañía: %s (id=%s).",
            barcode, product_code, product_tmpl.id, company.name, company.id,
        )
        return "created"

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
