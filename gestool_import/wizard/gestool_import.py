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

    data_file_users = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename = fields.Char()

    # data_file_industry = fields.Binary(
    #     string="File to Import",
    #     required=False,
    #     help="Get you data from Gestool.",
    # )
    # filename = fields.Char()

    data_file_partner = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename = fields.Char()

    data_file_category = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename = fields.Char()

    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()

        data_file_users = b64decode(self.data_file_users)
        if data_file_users:
            self._import_users(data_file_users)

        # data_file_industry = b64decode(self.data_file_industry)
        # if data_file_industry:
        #     self._import_users(data_file_industry)

        data_file_partner = b64decode(self.data_file_partner)
        if data_file_partner:
            self._import_partner(data_file_partner)

        data_file_category = b64decode(self.data_file_category)
        if data_file_category:
            self._import_category(data_file_category)

    ###################CLIENTES PROVEEDORES###################

    def _import_partner(self, data_file_partner):
        try:
            csv_data = reader(StringIO(data_file_partner.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            self.parse_partner(row)
        return

    def parse_partner(self, row):

        partner = self.env["res.partner"].search([("ref", "=", row[0]), ])

        country_id = self.env["res.country"].search([("name", "=", row[16]), ])
        if country_id:
            country_id = country_id.id

        state_id = self.env["res.country.state"].search([("name", "=", row[6].capitalize()), ])
        if state_id:
            state_id = state_id.id

        if partner:
            partner.write({
                "name": row[1],
                'vat': row[2],
                'street': row[3],
                'city': row[4],
                'zip': row[5],
                'state_id': state_id,
                'phone': row[7],
                'mobile': row[8],
                'website': row[9],
                'email': row[10],
                'display_name': row[14],
                'company_name': row[15],
                'is_company': 1,
                'active': 1,
                'comment': row[17],
                'customer_rank': row[20],
                'supplier_rank': row[21],
                'country_id': country_id,
            })
        else:
            self.env["res.partner"].create({
                "ref": row[0],
                "name": row[1],
                'vat': row[2],
                'street': row[3],
                'city': row[4],
                'zip': row[5],
                'state_id': state_id,
                'phone': row[7],
                'mobile': row[8],
                'website': row[9],
                'email': row[10],
                'display_name': row[14],
                'company_name': row[15],
                'is_company': 1,
                'active': 1,
                'comment': row[17],
                'customer_rank': row[20],
                'supplier_rank': row[21],
                'country_id': country_id,
            })

    ###################CATEGORIAS###################

    def _import_category(self, data_file_category):

        try:
            csv_data = reader(StringIO(data_file_category.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            self.parse_categories(row)
        return

    def parse_categories(self, row):
        category = self.env["product.category"].search([("name", "=", row[0]),])
        if not category:
            self.env["product.category"].create({
                "name": row[0],
                "parent_id" : 1,
            })


    ###################GRUPOS###################

    # def _import_industry(self, data_file_industry):
    #
    #     try:
    #         csv_data = reader(StringIO(data_file_industry.decode("utf-8")))
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #
    #     for row in csv_data:
    #         print("#######GRUPOS#######")
    #         print("/" * 80)
    #         print(row)
    #         print("/" * 80)
    #         #self.parse_industry(row)
    #     return
    #
    # def parse_industry(self, row):
    #
    #     industry = self.env["res.users"].search([("ref", "=", row[0]), ])
    #
    #     if industry:
    #         print("modificar")
    #         print(row[1])
    #         # user.write({
    #         #     "name": row[0]
    #         # })
    #     else:
    #         print("crear")
    #         print(row[1])
    #         # self.env["res.users"].create({
    #         #     "name": row[0]
    #         # })

    ###################AGENTES COMERCIALES###################

    def _import_users(self, data_file_users):

        try:
            csv_data = reader(StringIO(data_file_users.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            print("#######AGENTES#######")
            print("/" * 80)
            print(row)
            print("/" * 80)
            self.parse_users(row)
        return

    def parse_users(self, row):

        user = self.env["res.users"].search([("name", "=", row[0]), ])

        if user:
            print("modificar")
            print(row[1])
            # user.write({
            #     "name": row[0]
            # })
        else:
            print("crear")
            print(row[1])
            # self.env["res.users"].create({
            #     "name": row[0]
            # })
