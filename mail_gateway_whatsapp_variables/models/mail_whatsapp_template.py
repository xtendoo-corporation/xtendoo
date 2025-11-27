# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import re


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    model_id = fields.Many2one(
        'ir.model',
        string="Model",
        help="Model this template is designed for (e.g., res.partner, sale.order, account.move)",
        ondelete='cascade'
    )
    model = fields.Char(
        related='model_id.model',
        string="Model Technical Name",
        store=True,
        readonly=True
    )
    variable_ids = fields.One2many(
        'mail.whatsapp.template.variable',
        'template_id',
        string="Variables",
        help="Variables extracted from template body and header"
    )
    button_ids = fields.One2many(
        'mail.whatsapp.template.button',
        'template_id',
        string="Buttons",
        help="Action buttons for the template"
    )

    @api.onchange('body', 'header')
    def _onchange_body_header_extract_variables(self):
        """Extract variables from body and header automatically."""
        if not self.body and not self.header:
            return

        # Combinar texto de body y header
        text = (self.body or "") + (self.header or "")

        # Buscar placeholders {{número}}
        pattern = r'\{\{(\d+)\}\}'
        matches = re.findall(pattern, text)

        if not matches:
            return

        # Obtener variables únicas ordenadas
        var_numbers = sorted(set([int(m) for m in matches]))

        # Obtener IDs de variables existentes
        existing_vars = {var.name: var for var in self.variable_ids}

        # Crear nuevas variables si no existen
        new_vars = []
        for var_num in var_numbers:
            var_name = f"{{{{var_{var_num}}}}}"

            if var_name not in existing_vars:
                # Determinar si está en header o body
                line_type = 'header' if self.header and f'{{{{{var_num}}}}}' in self.header else 'body'

                new_vars.append((0, 0, {
                    'name': var_name,
                    'line_type': line_type,
                    'field_type': 'free_text',
                    'demo_value': f'Sample {var_num}',
                }))

        if new_vars:
            self.variable_ids = new_vars

