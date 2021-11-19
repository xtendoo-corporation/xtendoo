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

        data_file_partner = b64decode(self.data_file_partner)
        if data_file_partner:
            self._import_partner(data_file_partner)

        data_file_category = b64decode(self.data_file_category)
        if data_file_partner:
            self._import_category(data_file_category)

    def _import_partner(self, data_file_partner):
        try:
            csv_data = reader(StringIO(data_file_partner.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            self.parse_partner(row)
        return

    def parse_partner(self, row):

        partner = self.env["res.partner"].search([("ref", "=", row[0]),])

        if partner:
            print("modifico")
            print(row[1])
            # partner.write({
            #                 "name": row[1],
            #               })
        else:
            self.env["res.partner"].create(
                 {
                    "ref": row[0],
                    "name": row[1],
                    'vat': row[2],
                 }
            )

    def _import_category(self, data_file_category):

        try:
            csv_data = reader(StringIO(data_file_category.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            print(".")
            # print("/" * 80)
            # print(row)
            # print("/" * 80)
        return

    # def parse_categories(self, row, parent_id):
    #     category = self.env["product.category"].search([("name", "=", row[5]),])
    #     if not category:
    #         self.env["product.category"].create(
    #             {"name": row[5], "parent_id": parent_id,}
    #         )
    #
    # def parse_product(self, row, iva_id):
    #     price = float(row[10].replace(",", "."))
    #     category = self.env["product.category"].search([("name", "=", row[5]),])
    #     if category:
    #         category_id = category.id
    #     else:
    #         category_id = 0
    #
    #     product = self.env["product.product"].search([("default_code", "=", row[2]),])
    #
    #     if product:
    #         product.write(
    #             {
    #                 "name": row[1],
    #                 "categ_id": category_id,
    #                 "standard_price": price,
    #                 "taxes_id": [(6, 0, [iva_id])],
    #             }
    #         )
    #     else:
    #         self.env["product.template"].create(
    #             {
    #                 "name": row[1],
    #                 "default_code": row[2],
    #                 "categ_id": category_id,
    #                 "standard_price": price,
    #                 "type": "product",
    #                 "invoice_policy": "delivery",
    #                 "taxes_id": [(6, 0, [iva_id])],
    #             }
    #         )
    #
    # def get_parent_id(self):
    #     category_parent_id = self.env["product.category"].search(
    #         [("name", "=", "Todos"),]
    #     )
    #     if category_parent_id:
    #         return category_parent_id.id
    #     return 0
    #
    # def _parse_file(self, data_file):
    #     try:
    #         data = StringIO(data_file.decode("utf-8"))
    #         csv_data = reader(data)
    #         next(csv_data)
    #     except Exception:
    #         raise UserError(_("Can not read the file"))
    #     parent_id = self.get_parent_id()
    #     iva = self.env["account.tax"].search([("name", "=", "IVA 21% (Bienes)"),])
    #     if iva:
    #         iva_id = iva.id
    #     else:
    #         iva_id = 0
    #     for row in csv_data:
    #         self.parse_categories(row, parent_id)
    #         self.parse_product(row, iva_id)
    #     return
