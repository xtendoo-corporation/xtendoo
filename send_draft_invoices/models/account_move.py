# -*- coding: utf-8 -*-
"""
Extensión de `account.move` para enviar facturas en borrador a los seguidores.
"""
from odoo import api, fields, models, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore
from markupsafe import Markup
import base64


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_send_draft_to_followers(self):
        print("*"*100)
        print("senf_request_email")
        user = self.user_id
        users = []
        partners = self.mapped('message_partner_ids').filtered(lambda p: p.email)
        if not partners:
            raise UserError("No hay seguidores con email para enviar.")
        attachment = self.generate_draft_pdf()
        if not attachment:
            raise UserError("No se pudo generar el PDF.")
        for partner in partners:
            users += partner
            if not partner.email:
                continue
            body_html = f"""
                          <p>Tenemos que ver el texto que vamos a poner aqui</p>
                          <p>Saludos cordiales, Odoo</p>
                      """
            mail_values = {
                'subject': 'Factura',
                'email_from': user.email or 'no-reply@example.com',
                'email_to': partner.email,
                'body_html': body_html,
                # Adjuntamos el attachment creado arriba
                'attachment_ids': [(4, attachment.id)],
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()
        self._create_notificacion(users)

    def generate_draft_pdf(self):
        """Genera el PDF de la factura en borrador usando el informe 'Facturas sin pago'."""
        # Buscar el informe por modelo y nombre de reporte
        report = self.env['ir.actions.report'].search([
            ('model', '=', 'account.move'),
            ('report_name', '=', 'account.report_invoice')
        ], limit=1)

        if not report:
            # Fallback: buscar cualquier informe de facturas
            report = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1)

        if not report:
            raise UserError('No se encontró el informe "Facturas sin pago".')

        try:
            # _render requiere report_name y res_ids como parámetros
            pdf_content = report._render_qweb_pdf(report.report_name, self.ids)[0]
        except Exception as e:
            raise UserError('No se pudo generar el PDF de la factura: %s' % str(e))

        if not pdf_content:
            raise UserError('No se pudo generar el PDF de la factura.')

        attachment = self.env['ir.attachment'].create({
            'name': "Factura_borrador.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        return attachment

    def _create_notificacion(self, users):
        """Crea una nota interna en el chatter con la lista de usuarios a los que se envió la factura."""
        if not users:
            return

        # Construir la lista de usuarios en formato HTML
        user_list = ""
        for partner in users:
            user_list += f"<li><strong>{partner.name}</strong> - {partner.email}</li>"

        # Crear el mensaje completo en HTML bien formateado
        message = Markup(f"""<div>
<p>Se ha enviado la factura borrador a los siguientes usuarios:</p>
<ul>
{user_list}
</ul>
</div>""")

        # Añadir la nota interna al chatter
        self.message_post(
            body=message,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
