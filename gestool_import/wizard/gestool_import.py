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
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_partner = fields.Char()

    data_file_bank = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_bank = fields.Char()

    data_file_atypical = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_atypical = fields.Char()

    data_file_kits = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename_kits = fields.Char()

    # data_file_category = fields.Binary(
    #     string="File to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename_category = fields.Char()
    #
    # data_file_product = fields.Binary(
    #     string="File to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename_product = fields.Char()

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

        if self.data_file_bank:
            data_file_bank = b64decode(self.data_file_bank)
            if data_file_bank:
                self._import_bank(data_file_bank)

        if self.data_file_atypical:
            data_file_atypical = b64decode(self.data_file_atypical)
            if data_file_atypical:
                self._import_atypical(data_file_atypical)

        if self.data_file_kits:
            data_file_kits = b64decode(self.data_file_kits)
            if data_file_kits:
                self._import_kits(data_file_kits)

        # if self.data_file_category:
        #     data_file_category = b64decode(self.data_file_category)
        #     if data_file_category:
        #         self._import_category(data_file_category)
        #
        # if self.data_file_product:
        #     data_file_product = b64decode(self.data_file_product)
        #     if data_file_product:
        #         self._import_product(data_file_product)

    def _import_atypical(self, data_file_atypical):
        try:
            if data_file_atypical:
                csv_data = reader(StringIO(data_file_atypical.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        if csv_data:
            for row in csv_data:
                print("--------------------Atipicas de clientes--------------------------")
                self.parse_atypical(row)
            return

    def parse_atypical(self, row):
        partner = self.env["res.partner"].search([("ref", "=", row[0]), ])
        product = self.env["product.template"].search([("default_code", "=", row[1]), ])

        print("Cliente", row[0])
        print("Articulo", row[1])
        print("Precio", row[2])
        #print("Descuento", row[3])

        if product:
            if partner:
                # Comprobamos que no exista
                headpricelist = self.env["product.pricelist"].search([("name", "=", partner.name), ])

                # Metemos las cabeceras de las tarifas

                if not headpricelist:
                    headpricelist = self.env["product.pricelist"].sudo().create({
                        "name": partner.name,
                    })

                if row[2] != "0.000":
                    # Metemos las lineas de las tarifas
                    self.env["product.pricelist.item"].sudo().create({
                        "pricelist_id": headpricelist.id,
                        "product_tmpl_id": product.id,
                        'applied_on': "1_product",
                        'compute_price': "fixed",
                        'fixed_price': row[2],
                    })
                    print("creado por precio")

                if len(row) > 3 and row[3] != "0.000":
                    # Metemos las lineas de las tarifas
                    self.env["product.pricelist.item"].sudo().create({
                        "pricelist_id": headpricelist.id,
                        "product_tmpl_id": product.id,
                        'applied_on': "1_product",
                        'compute_price': "percentage",
                        'percent_price': row[3],
                    })
                    print("creado por descuento")

                # La aplicamos al cliente
                partner.sudo().write({
                    "property_product_pricelist": headpricelist,
                })

            else:
                print("No existe el partner con código:", row[0])
        else:
            print("No existe el producto con código:", row[1])

    def _import_kits(self, data_file_kits):
        try:
            if data_file_kits:
                csv_data = reader(StringIO(data_file_kits.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        if csv_data:
            for row in csv_data:
                print("--------------------Listas de materiales--------------------------")
                self.parse_kits(row)
            return

    def parse_kits(self, row):

        print("Compuesto", row[0])
        print("Componente", row[1])
        print("Unidades", row[2])

        # Busca el producto compuesto
        compound = self.env["product.template"].search([("default_code", "=", row[0])],)
        # Busca el producto componente
        component = self.env["product.template"].search([("default_code", "=", row[1])],)

        if not compound:
            print(f"No existe el producto compuesto con código: {row[0]}")
            return

        if not component:
            print(f"No existe el producto componente con código: {row[1]}")
            return

        # Busca o crea la lista de materiales (BOM)
        bom = self.env["mrp.bom"].search([("product_tmpl_id", "=", compound.id)], limit=1)
        if not bom:
            bom = self.env["mrp.bom"].sudo().create({
                "product_tmpl_id": compound.id,
                "type": "normal",
            })

        # Añade el componente a la lista de materiales
        self.env["mrp.bom.line"].sudo().create({
            "bom_id": bom.id,
            "product_id": component.id,
            "product_qty": row[2],
        })
        print(f"Componente añadido a la lista de materiales: {component.name}")

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
        partner = self.env["res.partner"].search([("name", "=", row[1]), ])
    #
    #     # country_id = self.env["res.country"].search([("name", "=", "España", ])
    #     # if country_id:
    #     #     country_id = country_id.id
    #
    #     state_id = self.env["res.country.state"].search([("name", "=", row[6].capitalize()), ])
    #     if state_id:
    #         state_id = state_id.id
    #
        # agent_id = self.env[("res.users")].search([("name", "=", row[23]), ])
        # if agent_id:
        #     agent_id = agent_id.id
        # else:
        #     agent_id = ""

        pago_id = self.env[("account.payment.term")].search([("name", "=", row[21]), ])
        if pago_id:
            pago_id = pago_id.id
        else:
            pago_id = ""

        ruta_id = self.env[("partner.delivery.zone")].search([("name", "=", row[26]), ])
        if ruta_id:
            ruta_id = ruta_id.id
        else:
            ruta_id = ""

        print("/////////CLIENTE//////////")
        print("partner", partner)
        print("nombre:", row[1])
        # print('agent', row[23])
        # print('agent_id', agent_id)
        print('ruta', row[26])
        print('ruta_id', ruta_id)

        if partner:
            print("Entro a modificar")
            partner.sudo().write({
                # 'user_id': agent_id,
                # 'user_id': agent_id,
                # "ref": row[24],
                # "property_payment_term_id": pago_id,
                "delivery_zone_id": ruta_id,
            })
    #     else:
    #         self.env["res.partner"].sudo().create({
    #             "ref": row[0],
    #             "name": row[1],
    #             'street': row[3],
    #             'city': row[4],
    #             'zip': row[5],
    #             'phone': row[7],
    #             'mobile': row[8],
    #             'website': row[9],
    #             'email': row[10],
    #             'display_name': row[14],
    #             'company_name': row[15],
    #             'is_company': 1,
    #             'active': 1,
    #             'comment': row[17],
    #             'customer_rank': row[19],
    #             'supplier_rank': row[20],
    #             'company_id': 1,
    #             'lang': "es_ES",
    #             'state_id': state_id,
    #             'vat': row[2],
    #             'country_id': 68,
    #             # 'agent_ids': agent_id,
    #         })

    def _import_bank(self, data_file_bank):
        try:
            if data_file_bank:
                csv_data = reader(StringIO(data_file_bank.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            print("--------------------Banco de cliente--------------------------")
            self.parse_bank(row)
        return

    def parse_bank(self, row):
        partner = self.env["res.partner"].search([("name", "=", row[5]), ])
        acc_bank = self.env["res.partner.bank"].search([("acc_number", "=", row[0]), ])

        print("/////////Bancos//////////")
        print("acc_number", row[0])
        print("sanitized_acc_number:", row[1])
        print('partner', row[5])

        if partner:
            if acc_bank:
                print("Cuenta de cliente ya existe")
            else:
                self.env["res.partner.bank"].sudo().create({
                    "acc_number": row[0],
                    "sanitized_acc_number": row[1],
                    'partner_id': partner.id,
                })
        else:
            print("Cliente no existe")

    # def _import_category(self, data_file_category):
    #     try:
    #         if data_file_category:
    #             csv_data = reader(StringIO(data_file_category.decode("utf-8")))
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #
    #     for row in csv_data:
    #         print("--------------------CATEGORY--------------------------")
    #         # self.parse_categories(row)
    #     return
    #
    # # def parse_categories(self, row):
    # #     category = self.env["product.category"].search([("name", "=", row[0]),])
    # #     if not category:
    # #         self.env["product.category"].create({
    # #             "name": row[0],
    # #             "parent_id" : 1,
    # #         })
    #
    # def _import_product(self, data_file_product):
    #     try:
    #         csv_data = reader(StringIO(data_file_product.decode("utf-8")))
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #
    #     for row in csv_data:
    #         print("--------------------PRODUCT--------------------------")
    #         self.parse_products(row)
    #     return
    #
    # def parse_products(self, row):
    #     print(row)
    #
    #     taxes_id = self.env["account.tax"].search([("description", "=", row[6]), ])
    #     print("taxes_id", taxes_id.name)
    #     if taxes_id:
    #         taxes_id = [(6, 0, [taxes_id.id])]
    #     else:
    #         taxes_id = [(6, 0, [])]
    #
    #     supplier_taxes_id = self.env["account.tax"].search([("description", "=", row[7]), ])
    #     print("supplier_taxes_id", supplier_taxes_id.name)
    #     if supplier_taxes_id:
    #         supplier_taxes_id = [(6, 0, [supplier_taxes_id.id])]
    #     else:
    #         supplier_taxes_id = [(6, 0, [])]
    #
    #     product = self.env["product.template"].search([("default_code", "=", row[0]),])
    #
    #     if not product:
    #         print("Producto No existe-------------------------------")
    #         self.env["product.template"].create({
    #             "default_code": row[0],
    #             "name": row[2],
    #             "list_price": row[4],
    #             "standard_price": row[5],
    #             "taxes_id": taxes_id,
    #             "supplier_taxes_id": supplier_taxes_id,
    #             "detailed_type": "product",
    #         })
    #     else:
    #         print("Producto existe-------------------------------")
    #         product.sudo().write({
    #             "name": row[2],
    #             "list_price": row[4],
    #             "standard_price": row[5],
    #             "taxes_id": taxes_id,
    #             "supplier_taxes_id": supplier_taxes_id,
    #         })
    #
    # # def _import_agentes(self, data_file_agentes):
    # #     try:
    # #         if data_file_agentes:
    # #             csv_data = reader(StringIO(data_file_agentes.decode("utf-8")))
    # #     except Exception:
    # #         raise UserError(_("Can not read the file"))
    # #
    # #     for row in csv_data:
    # #         print("--------------------AGENTES--------------------------")
    # #         # self.parse_agentes(row)
    # #     return
    #
    # # def parse_agentes(self, row):
    # #     agente = self.env["res.partner"].search([("ref", "=", row[0]), ])
    # #     if agente:
    # #         agente.write({
    # #             "name": row[1],
    # #             'email': row[10],
    # #             'display_name': row[1],
    # #             'is_company': 0,
    # #             'active': 1,
    # #             'customer_rank': 0,
    # #             'supplier_rank': 0,
    # #             'agent':1,
    # #         })
    # #     else:
    # #         self.env["res.partner"].create({
    # #             "ref": row[0],
    # #             "name": row[1],
    # #             'email': row[10],
    # #             'display_name': row[1],
    # #             'is_company': 0,
    # #             'active': 1,
    # #             'customer_rank': 0,
    # #             'supplier_rank': 0,
    # #             'agent':1,
    # #         })
