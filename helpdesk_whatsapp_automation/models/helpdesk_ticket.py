# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    assigned_employee_id = fields.Many2one(
        "res.users",
        string="Empleado Asignado",
        help="Empleado asignado para la comunicación de este ticket.",
    )

    def write(self, vals):
        # Determine if stage is changing
        stage_changing = 'stage_id' in vals
        
        # We need to know the state before the write
        old_stages = {ticket.id: ticket.stage_id.id for ticket in self}

        res = super().write(vals)

        if stage_changing:
            # For each ticket, check if it just became closed when it wasn't
            for ticket in self:
                old_stage_id = old_stages.get(ticket.id)
                old_stage = self.env['helpdesk.ticket.stage'].browse(old_stage_id)
                new_stage = ticket.stage_id

                if new_stage.closed and not old_stage.closed:
                    ticket._send_closed_ticket_notification()
        
        return res

    def _send_closed_ticket_notification(self):
        self.ensure_one()
        # notify BOTH the communication manager AND the communication employee assigned to the partner.
        # It's better to fetch them from the partner, in case the ticket doesn't have them explicitly set?
        # The user says: "cerrar ticket debe avisar tanto al encargado de comunicacion como al empleado de comunicacion que tenga asignado el contacto"
        partner = self.partner_id
        if not partner:
            return

        manager = partner.communication_manager_id
        employee = partner.communication_employee_id
        
        template = self.env.ref("helpdesk_whatsapp_automation.email_template_closed_whatsapp_ticket", raise_if_not_found=False)
        if not template:
            return

        email_to_list = []
        if employee and employee.email_formatted:
            email_to_list.append(employee.email_formatted.replace('\n', '').replace('\r', ''))
        if manager and manager.email_formatted:
            email_to_list.append(manager.email_formatted.replace('\n', '').replace('\r', ''))

        if not email_to_list:
            return

        email_from = self.company_id.email_formatted or self.env.user.email_formatted
        if email_from:
            email_from = email_from.replace('\n', '').replace('\r', '')

        email_values = {
            'email_to': ','.join(email_to_list),
            'email_from': email_from,
        }
        
        template.sudo().send_mail(self.id, force_send=True, email_values=email_values)
