from odoo import models, fields, api
import threading


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        for invoice in self:
            if invoice.partner_id.email and invoice.move_type == 'out_invoice' and invoice.partner_id.auto_invoice:
                invoice.send_email()
        return res

    # def send_email(self):
    #     print("*"*120)
    #     print("Entra a SEND MAIL")
    #     print("*"*120)
    #     self.ensure_one()
    #     template = self.env.ref('account.email_template_edi_invoice')
    #     print("template", template)
    #     # email_message = template.with_context(mail_notify_force_send=True).send_mail(self.id)
    #     print("*" * 120)
    #     # return email_message
    def send_email(self):
        print("*" * 120)
        print("Entra a SEND MAIL")
        mail_template = self.env.ref('account.email_template_edi_invoice')
        mail_send = mail_template.send_mail(self.id, force_send=True)
        print("mail_send", mail_send)
        if mail_send:
            partner_name = self.partner_id.name
            invoice_name = self.name
            invoice_origin = self.invoice_origin
            amount_total = self.amount_total
            company_name = self.company_id.name
            payment_reference = self.payment_reference
            signature = self.invoice_user_id.signature
            notification_body = f"""
            <div style="margin: 0px; padding: 0px;">
            <p><b>Factura enviada automáticamente</b></p>
            <p style="margin: 0px; padding: 0px; font-size: 13px;">
                Estimado/a {partner_name},
                <br /><br />
                Aquí está su Factura {invoice_name} (con referencia: {invoice_origin}) por un importe total de {amount_total}€ de parte de {company_name}.Por favor, revise la forma de pago.
                <br /><br />
                Utilice la siguiente comunicación para el pago: <span style="font-weight:bold;" t-out="object.payment_reference or ''">{payment_reference}</span>.
                <br /><br />
                No dude en contactarnos si tiene alguna pregunta.
                <br />
                {signature}
                <br />
            </p>
        </div>
        """
            self.message_post(body=notification_body, subtype_id=self.env.ref('mail.mt_note').id)
            self.is_move_sent = True

        print("*" * 120)


