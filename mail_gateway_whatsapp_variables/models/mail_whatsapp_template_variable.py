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
        help="Variable name like {{1}}, {{2}}, etc. or descriptive name"
    )
    variable_index = fields.Integer(
        string="Variable Index",
        help="Numeric index of the variable (1, 2, 3, etc.)",
        default=1
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

    field_id = fields.Many2one(
        'ir.model.fields',
        string="Field",
        domain="[('model_id', '=', template_model_id), ('store', '=', True)]",
        help="Select a field from the template's model"
    )
    template_model_id = fields.Many2one(
        'ir.model',
        related='template_id.model_id',
        string="Template Model",
        store=False
    )
    field_name = fields.Char(
        string="Field Path",
        compute="_compute_field_name",
        store=True,
        readonly=False,
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

    @api.depends('field_id')
    def _compute_field_name(self):
        """Compute field_name from selected field_id."""
        for variable in self:
            if variable.field_id:
                variable.field_name = variable.field_id.name
            elif not variable.field_name:
                variable.field_name = False

    @api.onchange('name')
    def _onchange_name_extract_index(self):
        """Auto-extract variable index from name when name contains {{N}} pattern."""
        if self.name:
            import re
            match = re.search(r'\{\{(\d+)\}\}', self.name)
            if match:
                extracted_index = int(match.group(1))
                if extracted_index > 0:
                    self.variable_index = extracted_index

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
        """Extract the numeric index from name like {{1}} -> 1 or from variable_index field."""
        import re

        # First, try to extract from name pattern {{N}}
        if self.name:
            match = re.search(r'\{\{(\d+)\}\}', self.name)
            if match:
                return int(match.group(1))

        # If no pattern found, use variable_index field
        if self.variable_index and self.variable_index > 0:
            return self.variable_index

        # Last resort: try to extract any number from name
        if self.name:
            match = re.search(r'\d+', self.name)
            if match:
                return int(match.group())

        return 0

