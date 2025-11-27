# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailWhatsappTemplateVariable(models.Model):
    _name = "mail.whatsapp.template.variable"
    _description = "WhatsApp Template Variable"
    _order = "line_type, sequence, id"

    template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="Template",
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(
        string="Name",
        required=True,
        help="Variable name like {{1}}, {{2}}, etc."
    )
    sequence = fields.Integer(string="Sequence", default=10)
    line_type = fields.Selection([
        ('header', 'Header'),
        ('body', 'Body'),
        ('button', 'Button'),
    ], string="Type", default='body', required=True)

    field_type = fields.Selection([
        ('field', 'Field'),
        ('free_text', 'Free Text'),
        ('user_name', 'User Name'),
        ('user_mobile', 'User Mobile'),
    ], string="Field Type", default='free_text', required=True)

    field_name = fields.Char(
        string="Field Path",
        help="Field path like partner_id.name, amount_total, etc."
    )
    demo_value = fields.Char(
        string="Sample Value",
        required=True,
        default="Sample",
        help="Sample value for preview"
    )
    button_id = fields.Many2one(
        'mail.whatsapp.template.button',
        string="Button",
        help="Button associated with this variable"
    )

    @api.depends('name', 'line_type')
    def _compute_display_name(self):
        for variable in self:
            if variable.line_type == 'header':
                variable.display_name = f"Header {variable.name}"
            elif variable.line_type == 'button':
                variable.display_name = f"Button {variable.name}"
            else:
                variable.display_name = variable.name

    def _extract_variable_index(self):
        """Extract the numeric index from variable name like {{1}} -> 1."""
        import re
        match = re.search(r'\d+', self.name)
        return int(match.group()) if match else 0

