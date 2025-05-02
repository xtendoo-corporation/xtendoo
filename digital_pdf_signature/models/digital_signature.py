import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import tempfile
import os
from datetime import datetime
from endesive import pdf

class DigitalSignature(models.Model):
    _name = 'digital.signature'
    _description = 'Firma Digital PDF'

    name = fields.Char('Nombre', required=True)
    original_pdf = fields.Binary('PDF Original', required=True)
    original_filename = fields.Char('Nombre del archivo original')
    signed_pdf = fields.Binary('PDF Firmado', readonly=True)
    signed_filename = fields.Char('Nombre del archivo firmado')
    certificate_id = fields.Many2one('certificate', 'Certificado', required=True)
    signing_date = fields.Datetime('Fecha de firma', readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('signed', 'Firmado'),
    ], default='draft', string='Estado')

    def action_sign_pdf(self):
        """Firma el documento PDF con el certificado seleccionado"""
        self.ensure_one()
        if not self.certificate_id or not self.certificate_id.is_valid:
            raise UserError(_("Debe seleccionar un certificado válido."))

        if not self.certificate_id.private_key_id:
            raise UserError(_("El certificado debe tener una clave privada asociada."))

        # Guardar PDF original en un archivo temporal
        pdf_content = base64.b64decode(self.original_pdf)
        temp_original = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_original.write(pdf_content)
        temp_original.close()

        # Archivo temporal para el PDF firmado
        temp_signed = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_signed.close()

        try:
            # Preparar datos para la firma
            date = datetime.now()
            certificate = base64.b64decode(self.certificate_id.with_context(bin_size=False).pem_certificate)
            private_key = self.certificate_id.private_key_id

            # Datos de firma
            signature_info = {
                'signingdate': date.strftime('D:%Y%m%d%H%M%S%z'),
                'reason': 'Documento firmado digitalmente',
                'location': self.env.company.name,
                'contact': self.env.user.name,
            }

            # Firmar el PDF
            self._sign_pdf_with_certificate(
                temp_original.name,
                temp_signed.name,
                certificate,
                private_key,
                signature_info)

            # Leer el PDF firmado
            with open(temp_signed.name, 'rb') as f:
                signed_data = f.read()

            # Actualizar el registro
            self.write({
                'signed_pdf': base64.b64encode(signed_data),
                'signed_filename': f"{os.path.splitext(self.original_filename)[0]}_signed.pdf",
                'signing_date': fields.Datetime.now(),
                'state': 'signed',
            })

        finally:
            # Limpiar archivos temporales
            os.unlink(temp_original.name)
            os.unlink(temp_signed.name)

        return True

    def _sign_pdf_with_certificate(self, input_file, output_file, certificate, private_key, signature_info):
        """Realiza la firma del PDF usando la biblioteca endesive"""

        # Obtener la clave privada en formato adecuado para firmar
        key = base64.b64decode(private_key.with_context(bin_size=False).pem_key)

        with open(input_file, 'rb') as f:
            datau = f.read()

        # Datos de la firma
        dct = {
            'sigflags': 3,
            'contact': signature_info['contact'],
            'location': signature_info['location'],
            'signingdate': signature_info['signingdate'],
            'reason': signature_info['reason'],
        }

        # Firmar el PDF
        dataz = pdf.cms.sign(
            datau,
            dct,
            key,
            certificate,
            [],
            'sha256'
        )

        # Guardar el PDF firmado
        with open(output_file, 'wb') as f:
            f.write(dataz)
