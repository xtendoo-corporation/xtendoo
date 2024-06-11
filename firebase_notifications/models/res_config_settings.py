import json
import base64
from odoo import models, fields, api
from .firebase_data import FirebaseData


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    firebase_oca_json_file = fields.Binary('JSON File')
    firebase_data_id = fields.Many2one('firebase.data', string="Firebase Data")

    firebase_oca_type = fields.Char(
        string='Type',
        related="firebase_data_id.type"
    )
    firebase_oca_project_id = fields.Char(
        string='Project ID',
        related="firebase_data_id.project_id")
    firebase_oca_private_key_id = fields.Char(
        string='Private Key ID',
        related="firebase_data_id.private_key_id"
    )
    firebase_oca_private_key = fields.Char(
        string='Private Key',
        related="firebase_data_id.private_key"
    )
    firebase_oca_client_email = fields.Char(
        string='Client Email',
        related="firebase_data_id.client_email"
    )
    firebase_oca_client_id = fields.Char(
        string='Client ID',
        related="firebase_data_id.client_id"
    )
    firebase_oca_auth_uri = fields.Char(
        string='Auth URI',
        related="firebase_data_id.auth_uri"
    )
    firebase_oca_token_uri = fields.Char(
        string='Token URI',
        related="firebase_data_id.token_uri"
    )
    firebase_oca_auth_provider_x509_cert_url = fields.Char(
        string='Auth Provider X509 Cert URL',
        related="firebase_data_id.auth_provider_x509_cert_url"
    )
    firebase_oca_client_x509_cert_url = fields.Char(
        string='Client X509 Cert URL',
        related="firebase_data_id.client_x509_cert_url"
    )
    firebase_oca_universe_domain = fields.Char(
        string='Universe Domain',
        related="firebase_data_id.universe_domain"
    )

    @api.onchange('firebase_oca_json_file')
    def import_json_file(self):
        if self.firebase_oca_json_file:
            # Borrar los datos existentes
            if self.firebase_data_id:
                self.firebase_data_id.unlink()

            # Importar el nuevo archivo JSON
            firebase_data = self.env['firebase.data'].import_json_file(self.firebase_oca_json_file)
            self.firebase_data_id = firebase_data.id

    def get_credentials(self):
        firebase_data = self.firebase_data_id
        if firebase_data:
            return {
                'type': firebase_data.type,
                'project_id': firebase_data.project_id,
                'private_key_id': firebase_data.private_key_id,
                'private_key': firebase_data.private_key,
                'client_email': firebase_data.client_email,
                'client_id': firebase_data.client_id,
                'auth_uri': firebase_data.auth_uri,
                'token_uri': firebase_data.token_uri,
                'auth_provider_x509_cert_url': firebase_data.auth_provider_x509_cert_url,
                'client_x509_cert_url': firebase_data.client_x509_cert_url,
                'universe_domain': firebase_data.universe_domain
            }
        else:
            return {}
