import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SignPdfWizard(models.TransientModel):
    _name = 'sign.pdf.wizard'
    _description = 'Asistente para firmar PDF'

    pdf_file = fields.Binary('Archivo PDF', required=True)
    pdf_filename = fields.Char('Nombre del archivo')
    certificate_id = fields.Many2one('certificate', 'Certificado', required=True,
                                    domain=[('is_valid', '=', True)])

    def action_sign_pdf(self):
        """Crea un registro de firma digital y firma el PDF"""
        if not self.pdf_file or not self.certificate_id:
            raise UserError(_('Debe seleccionar un PDF y un certificado válido.'))

        # Crear el registro de firma digital
        signature = self.env['digital.signature'].create({
            'name': self.pdf_filename or 'Documento firmado',
            'original_pdf': self.pdf_file,
            'original_filename': self.pdf_filename,
            'certificate_id': self.certificate_id.id,
        })

        # Firmar el PDF
        signature.action_sign_pdf()

        # Redirigir al registro creado
        return {
            'name': _('Documento Firmado'),
            'view_mode': 'form',
            'res_model': 'digital.signature',
            'res_id': signature.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
