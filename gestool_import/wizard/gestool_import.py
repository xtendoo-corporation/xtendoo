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

    data_file_agentes = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename = fields.Char()
    data_file_partner = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    data_file_category = fields.Binary(
        string="File to Import",
        required=False,
        help="Get you data from Gestool.",
    )
    filename = fields.Char()

    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and go to reconciliation. """
        self.ensure_one()

        data_file_agentes = b64decode(self.data_file_agentes)
        if data_file_agentes:
            self._import_agentes(data_file_agentes)

        # data_file_industry = b64decode(self.data_file_industry)
        # if data_file_industry:
        #     self._import_users(data_file_industry)

        data_file_partner = b64decode(self.data_file_partner)
        if data_file_partner:
            self._import_partner(data_file_partner)

        data_file_category = b64decode(self.data_file_category)
        if data_file_category:
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
        partner = self.env["res.partner"].search([("ref", "=", row[0]), ])

        country_id = self.env["res.country"].search([("name", "=", row[16]), ])
        if country_id:
            country_id = country_id.id

        state_id = self.env["res.country.state"].search([("name", "=", row[6].capitalize()), ])
        if state_id:
            state_id = state_id.id

        agent_id = self.env["res.partner"].search([("name", "=", row[23]), ])
        if agent_id:
            agent_id = [(6, 0, [agent_id.id])]
        else:
            agent_id = [(6, 0, [])]

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
                'comment': row[17],
                'country_id': country_id,
                'agent_ids': agent_id,
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
                'customer_rank': row[19],
                'supplier_rank': row[20],
                'country_id': country_id,
                'agent_ids': agent_id,
            })

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

    def _import_agentes(self, data_file_agentes):
        try:
            csv_data = reader(StringIO(data_file_agentes.decode("utf-8")))
        except Exception:
            raise UserError(_("Can not read the file"))

        for row in csv_data:
            self.parse_agentes(row)
        return

    def parse_agentes(self, row):
        agente = self.env["res.partner"].search([("ref", "=", row[0]), ])
        if agente:
            agente.write({
                "name": row[1],
                'email': row[10],
                'display_name': row[1],
                'is_company': 0,
                'active': 1,
                'customer_rank': 0,
                'supplier_rank': 0,
                'agent':1,
            })
        else:
            self.env["res.partner"].create({
                "ref": row[0],
                "name": row[1],
                'email': row[10],
                'display_name': row[1],
                'is_company': 0,
                'active': 1,
                'customer_rank': 0,
                'supplier_rank': 0,
                'agent':1,
            })
