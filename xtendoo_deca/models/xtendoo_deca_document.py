# -*- coding: utf-8 -*-
import base64
import secrets
from datetime import timedelta

from werkzeug.urls import url_quote

from odoo import api, fields, models
from odoo.exceptions import UserError


class XtendooDecaDocument(models.Model):
    _name = 'xtendoo.deca.document'
    _description = 'Documento Electrónico de Control Administrativo (DeCA)'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Referencia', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Empresa', required=True,
        default=lambda self: self.env.company)
    picking_id = fields.Many2one(
        'stock.picking', string='Albarán', required=True, ondelete='cascade')

    # Datos exigidos por el art. 6 de la Orden FOM/2861/2012.
    cargador_partner_id = fields.Many2one(
        'res.partner', string='Cargador contractual', required=True,
        help='Persona física o jurídica que contrata directamente con el '
             'transportista efectivo el transporte del envío.')
    cargador_nif = fields.Char(string='NIF cargador', required=True)
    transportista_partner_id = fields.Many2one(
        'res.partner', string='Transportista efectivo', required=True,
        help='Titular de la autorización a cuyo amparo se realiza '
             'materialmente el transporte.')
    transportista_nif = fields.Char(string='NIF transportista', required=True)
    origen = fields.Char(string='Origen del envío', required=True)
    destino = fields.Char(string='Destino del envío', required=True)
    mercancia_naturaleza = fields.Text(string='Naturaleza de la mercancía', required=True)
    mercancia_peso = fields.Float(string='Peso (kg)')
    matricula_vehiculo = fields.Char(string='Matrícula del vehículo')
    autorizacion_especial = fields.Char(string='Autorización especial de circulación')
    fecha_servicio = fields.Datetime(string='Fecha de realización del transporte', required=True)
    observaciones = fields.Text(string='Observaciones')

    # Documento electrónico (apartados Segundo y Tercero de la Resolución).
    token = fields.Char(string='Token', readonly=True, copy=False, index=True)
    qr_url = fields.Char(string='URL pública (QR)', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('superseded', 'Sustituido'),
    ], string='Estado', default='draft', copy=False, tracking=True)
    download_enabled = fields.Boolean(string='Descarga habilitada', default=True, copy=False)

    pdf_file = fields.Binary(string='PDF DeCA', attachment=True, copy=False)
    pdf_filename = fields.Char(string='Nombre de archivo', copy=False)

    previous_document_id = fields.Many2one(
        'xtendoo.deca.document', string='Documento anterior', copy=False, readonly=True,
        help='Documento sustituido por este, conservado a efectos de '
             'trazabilidad (apartado Quinto.2 de la Resolución).')

    _sql_constraints = [
        ('token_uniq', 'unique(token)', 'El token del DeCA debe ser único.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        docs = super().create(vals_list)
        for doc in docs:
            if not doc.name:
                doc.name = 'DECA/%06d' % doc.id
        return docs

    def _get_public_base_url(self):
        """Return the configured public URL, including its protocol."""
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url',
        ) or ''
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url.lstrip('/')
        return base_url.rstrip('/')

    def get_barcode_src(self):
        """Fuente de imagen para el código QR, usando el generador de
        códigos de barras nativo de Odoo (sin dependencias externas)."""
        self.ensure_one()
        return '/report/barcode/?type=QR&value=%s&width=200&height=200' % url_quote(self.qr_url or '')

    def _generate_pdf(self):
        for doc in self:
            if not doc.token:
                doc.token = secrets.token_urlsafe(24)
            doc.qr_url = '%s/deca/%s' % (doc._get_public_base_url(), doc.token)
            pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf(
                'xtendoo_deca.action_report_xtendoo_deca', doc.ids)
            doc.write({
                'pdf_file': base64.b64encode(pdf_content),
                'pdf_filename': '%s.pdf' % (doc.name or 'DeCA').replace('/', '_'),
                'state': 'generated',
                'download_enabled': True,
            })

    def action_generate(self):
        for doc in self:
            if doc.state == 'generated':
                raise UserError(
                    'Este DeCA ya se generó. Use "Modificar datos (nuevo PDF)" '
                    'para actualizarlo conservando la trazabilidad.')
        self._generate_pdf()
        return True

    def action_regenerate(self):
        """Genera un nuevo DeCA con nueva URL/QR (apartado Quinto.2): el
        documento anterior se conserva a efectos de trazabilidad."""
        self.ensure_one()
        new_doc = self.copy({
            'previous_document_id': self.id,
            'state': 'draft',
            'token': False,
            'qr_url': False,
            'pdf_file': False,
            'pdf_filename': False,
            'name': False,
        })
        self.state = 'superseded'
        new_doc._generate_pdf()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'xtendoo.deca.document',
            'res_id': new_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_disable_download(self):
        self.write({'download_enabled': False})

    def action_view_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.qr_url,
            'target': 'new',
        }

    @api.model
    def _cron_disable_expired_downloads(self):
        """Art. Tercero.5: transcurridos 7 días naturales tras la
        finalización del servicio, se podrá desactivar la descarga. El
        fichero se conserva igualmente (adjunto) durante al menos 1 año."""
        expiry = fields.Datetime.now() - timedelta(days=7)
        docs = self.search([
            ('download_enabled', '=', True),
            ('fecha_servicio', '<=', expiry),
            ('state', '=', 'generated'),
        ])
        docs.write({'download_enabled': False})
