# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class WhatsappComposer(models.TransientModel):
    _inherit = "whatsapp.composer"

    # Attachment support
    attachment_id = fields.Many2one(
        'ir.attachment',
        string="Attachment",
        help="Attach a file to send with the WhatsApp message (PDF, images, etc.)"
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'whatsapp_composer_attachment_rel',
        'composer_id',
        'attachment_id',
        string="Attachments",
        help="Multiple attachments to send with the message"
    )

    # Variables dinámicas basadas en la plantilla
    template_variable_ids = fields.One2many(
        'whatsapp.composer.variable',
        'composer_id',
        string="Template Variables"
    )

    has_variables = fields.Boolean(
        compute="_compute_has_variables",
        string="Template has variables"
    )
    variable_count = fields.Integer(
        compute="_compute_has_variables",
        string="Number of variables"
    )

    # Botones dinámicos
    template_button_ids = fields.One2many(
        'whatsapp.composer.button',
        'composer_id',
        string="Template Buttons"
    )


    @api.depends("template_id", "template_id.variable_ids")
    def _compute_has_variables(self):
        """Detectar si la plantilla tiene variables."""
        for composer in self:
            if composer.template_id and composer.template_id.variable_ids:
                body_vars = composer.template_id.variable_ids.filtered(
                    lambda v: v.line_type in ['body', 'header']
                )
                composer.has_variables = bool(body_vars)
                composer.variable_count = len(body_vars)
            else:
                composer.has_variables = False
                composer.variable_count = 0

    @api.onchange("template_id")
    def onchange_template_id(self):
        """Cuando cambia la plantilla, crear variables y botones."""
        res = super().onchange_template_id()

        if self.template_id:
            # Crear variables desde la plantilla
            self._create_variables_from_template()
            # Crear botones desde la plantilla
            self._create_buttons_from_template()

        return res

    def _create_variables_from_template(self):
        """Crear registros de variables desde la plantilla."""
        self.template_variable_ids = [(5, 0, 0)]  # Limpiar existentes

        if not self.template_id or not self.template_id.variable_ids:
            return

        # Filtrar solo variables de body y header
        template_vars = self.template_id.variable_ids.filtered(
            lambda v: v.line_type in ['body', 'header']
        ).sorted(lambda v: (v.line_type, v.sequence))

        variable_lines = []
        for template_var in template_vars:
            # Intentar obtener valor desde el registro
            value = self._get_variable_value_from_record(template_var)

            variable_lines.append((0, 0, {
                'template_variable_id': template_var.id,
                'field_value': value or template_var.demo_value,
            }))

        if variable_lines:
            self.template_variable_ids = variable_lines

    def _create_buttons_from_template(self):
        """Crear registros de botones desde la plantilla."""
        self.template_button_ids = [(5, 0, 0)]  # Limpiar existentes

        if not self.template_id or not self.template_id.button_ids:
            return

        button_lines = []
        for template_button in self.template_id.button_ids:
            button_lines.append((0, 0, {
                'template_button_id': template_button.id,
                'call_number': template_button.call_number,
                'website_url': template_button.website_url,
            }))

        if button_lines:
            self.template_button_ids = button_lines

    def _get_variable_value_from_record(self, template_variable):
        """Obtener valor de la variable desde el registro actual."""
        if not self.res_model or not self.res_id:
            return False

        try:
            record = self.env[self.res_model].browse(self.res_id)

            # Si es campo del modelo
            if template_variable.field_type == 'field' and template_variable.field_name:
                value = record
                for field in template_variable.field_name.split('.'):
                    value = value[field]
                return str(value) if value else False

            # Si es nombre de usuario
            elif template_variable.field_type == 'user_name':
                return self.env.user.name

            # Si es móvil de usuario
            elif template_variable.field_type == 'user_mobile':
                return self.env.user.mobile or self.env.user.phone or False

        except:
            pass

        return False


    def _action_send_whatsapp(self):
        """Send WhatsApp message with optional attachments."""
        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return

        channel = record._whatsapp_get_channel(self.number_field_name, self.gateway_id)

        # Prepare attachments list
        attachment_ids = []
        if self.attachment_ids:
            attachment_ids = self.attachment_ids.ids

        # Send message with or without attachments
        # WhatsApp API typically sends text and attachments together
        channel.with_context(whatsapp_template_id=self.template_id.id).message_post(
            body=self.body,
            attachment_ids=attachment_ids if attachment_ids else False,
            subtype_xmlid="mail.mt_comment",
            message_type="comment"
        )

        # Registrar también en el contacto destinatario si existe
        partner = None
        if hasattr(channel, 'channel_partner_ids') and channel.channel_partner_ids:
            partners = channel.channel_partner_ids.filtered(
                lambda p: p.id != self.env.ref('base.partner_root').id and p.id != self.env.user.partner_id.id
            )
            if partners:
                partner = partners[0]

        if partner:
            partner.sudo().message_post(
                body=self.body,
                author_id=self.env.user.partner_id.id,
                gateway_type="whatsapp",
                attachment_ids=attachment_ids if attachment_ids else False,
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
            )


class WhatsappComposerVariable(models.TransientModel):
    _name = "whatsapp.composer.variable"
    _description = "WhatsApp Composer Variable"
    _order = "sequence, id"

    composer_id = fields.Many2one(
        'whatsapp.composer',
        string="Composer",
        required=True,
        ondelete='cascade'
    )
    template_variable_id = fields.Many2one(
        'mail.whatsapp.template.variable',
        string="Template Variable",
        required=True
    )
    sequence = fields.Integer(
        related='template_variable_id.sequence',
        store=True
    )
    field_value = fields.Char(
        string="Value",
        required=True
    )
    display_name = fields.Char(
        related='template_variable_id.name',
        string="Variable"
    )
    field_type = fields.Selection(
        related='template_variable_id.field_type',
        string="Type"
    )


class WhatsappComposerButton(models.TransientModel):
    _name = "whatsapp.composer.button"
    _description = "WhatsApp Composer Button"
    _order = "sequence, id"

    composer_id = fields.Many2one(
        'whatsapp.composer',
        string="Composer",
        required=True,
        ondelete='cascade'
    )
    template_button_id = fields.Many2one(
        'mail.whatsapp.template.button',
        string="Template Button",
        required=True
    )
    sequence = fields.Integer(
        related='template_button_id.sequence',
        store=True
    )
    button_type = fields.Selection(
        related='template_button_id.button_type',
        string="Type"
    )
    call_number = fields.Char(string="Phone Number")
    website_url = fields.Char(string="Website URL")
