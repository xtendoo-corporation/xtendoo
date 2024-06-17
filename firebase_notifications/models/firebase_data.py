import json
import base64
from odoo import models, fields, api


class FirebaseData(models.Model):
    _name = 'firebase.data'
    _description = 'Firebase Data'

    json_file = fields.Binary('JSON File')

    type = fields.Char(string='Type', store=True)
    project_id = fields.Char(string='Project ID', store=True)
    private_key_id = fields.Char(string='Private Key ID', store=True)
    private_key = fields.Char(string='Private Key', store=True)
    client_email = fields.Char(string='Client Email', store=True)
    client_id = fields.Char(string='Client ID', store=True)
    auth_uri = fields.Char(string='Auth URI', store=True)
    token_uri = fields.Char(string='Token URI', store=True)
    auth_provider_x509_cert_url = fields.Char(string='Auth Provider X509 Cert URL', store=True)
    client_x509_cert_url = fields.Char(string='Client X509 Cert URL', store=True)
    universe_domain = fields.Char(string='Universe Domain', store=True)

    @api.model
    def import_json_file(self, json_file):
        json_content = base64.b64decode(json_file).decode('utf-8')
        data = json.loads(json_content)

        return self.create({
            'json_file': json_file,
            'type': data['type'],
            'project_id': data['project_id'],
            'private_key_id': data['private_key_id'],
            'private_key': data['private_key'],
            'client_email': data['client_email'],
            'client_id': data['client_id'],
            'auth_uri': data['auth_uri'],
            'token_uri': data['token_uri'],
            'auth_provider_x509_cert_url': data['auth_provider_x509_cert_url'],
            'client_x509_cert_url': data['client_x509_cert_url'],
            'universe_domain': data['universe_domain'],
        })

    def get_credentials(self):
        return {
            'type': self.type,
            'project_id': self.project_id,
            'private_key_id': self.private_key_id,
            'private_key': self.private_key,
            'client_email': self.client_email,
            'client_id': self.client_id,
            'auth_uri': self.auth_uri,
            'token_uri': self.token_uri,
            'auth_provider_x509_cert_url': self.auth_provider_x509_cert_url,
            'client_x509_cert_url': self.client_x509_cert_url,
            'universe_domain': self.universe_domain
        }
