# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
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
    auto_attach_pdf = fields.Boolean(
        string="Auto-attach PDF",
        default=True,
        help="Automatically attach PDF report when available (Sale Order, Invoice, etc.)"
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

    @api.model
    def default_get(self, fields_list):
        """Override to auto-attach PDF for sale.order and account.move."""
        res = super().default_get(fields_list)

        # Get context values
        res_model = res.get('res_model') or self.env.context.get('default_res_model')
        res_id = res.get('res_id') or self.env.context.get('default_res_id')
        auto_attach = res.get('auto_attach_pdf', True)

        if res_model and res_id and auto_attach:
            attachment_ids = self._get_auto_attachments(res_model, res_id)
            if attachment_ids:
                res['attachment_ids'] = [(6, 0, attachment_ids)]

        return res

    def _get_auto_attachments(self, res_model, res_id):
        """Generate and return attachment IDs for the given record.

        Supports:
        - sale.order: Quotation/Order PDF
        - account.move: Invoice PDF
        """
        import logging
        _logger = logging.getLogger(__name__)

        attachment_ids = []

        try:
            if res_model == 'sale.order':
                attachment_ids = self._generate_sale_order_pdf(res_id)
            elif res_model == 'account.move':
                attachment_ids = self._generate_invoice_pdf(res_id)
        except Exception as e:
            _logger.warning(f"Could not auto-attach PDF for {res_model} {res_id}: {e}")

        return attachment_ids

    def _generate_sale_order_pdf(self, order_id):
        """Generate PDF for sale order and return attachment IDs."""
        order = self.env['sale.order'].browse(order_id)
        if not order.exists():
            return []

        # Get the report action
        report = self.env.ref('sale.action_report_saleorder', raise_if_not_found=False)
        if not report:
            return []

        # Generate PDF
        pdf_content, content_type = report._render_qweb_pdf(report.report_name, order.ids)

        # Determine filename based on state
        if order.state in ['draft', 'sent']:
            filename = f'Quotation_{order.name}.pdf'
        else:
            filename = f'Order_{order.name}.pdf'

        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_content)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': 'sale.order',
            'res_id': order.id,
            'mimetype': 'application/pdf',
        })

        return [attachment.id]

    def _generate_invoice_pdf(self, move_id):
        """Generate PDF for invoice/bill and return attachment IDs."""
        move = self.env['account.move'].browse(move_id)
        if not move.exists() or move.move_type not in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
            return []

        # Get the report action
        report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        if not report:
            return []

        # Generate PDF
        pdf_content, content_type = report._render_qweb_pdf(report.report_name, move.ids)

        # Determine filename based on type
        if move.move_type == 'out_invoice':
            doc_type = 'Invoice'
        elif move.move_type == 'out_refund':
            doc_type = 'Refund'
        elif move.move_type == 'in_invoice':
            doc_type = 'Bill'
        else:
            doc_type = 'Credit_Note'

        filename = f'{doc_type}_{move.name.replace("/", "_")}.pdf'

        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_content)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': pdf_base64,
            'res_model': 'account.move',
            'res_id': move.id,
            'mimetype': 'application/pdf',
        })

        return [attachment.id]


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
