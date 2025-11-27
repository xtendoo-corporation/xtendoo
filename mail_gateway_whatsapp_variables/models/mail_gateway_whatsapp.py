# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re
from odoo import models


class MailGatewayWhatsappService(models.AbstractModel):
    _inherit = "mail.gateway.whatsapp"

    def _send_payload(
        self, channel, body=False, media_id=False, media_type=False, media_name=False
    ):
        """Override to add template components (variables) support."""
        # Get the base payload from parent
        payload = super()._send_payload(
            channel, body=body, media_id=media_id, media_type=media_type, media_name=media_name
        )

        # If it's a template message, check if we need to add components
        if payload and payload.get("type") == "template" and body:
            whatsapp_template_id = self.env.context.get("whatsapp_template_id")

            if whatsapp_template_id:
                whatsapp_template = self.env["mail.whatsapp.template"].browse(
                    whatsapp_template_id
                )

                # Check if template has variables configured
                if whatsapp_template.variable_ids:
                    # Get values from context or from record
                    template_variables = self.env.context.get("template_variables", {})

                    # If no variables in context, try to get them from the record
                    if not template_variables:
                        template_variables = self._get_variables_from_template(
                            whatsapp_template
                        )

                    # Build components array with variables
                    if template_variables:
                        components = self._build_template_components(
                            whatsapp_template, template_variables
                        )

                        if components:
                            payload["template"]["components"] = components

        return payload

    def _get_variables_from_template(self, template):
        """Get variable values from the current record based on template configuration.

        Args:
            template: mail.whatsapp.template record

        Returns:
            dict: Variable values {1: 'value1', 2: 'value2', ...}
        """
        variables = {}

        # Get the record from context
        res_model = self.env.context.get("res_model")
        res_id = self.env.context.get("res_id")

        if not res_model or not res_id:
            return variables

        try:
            record = self.env[res_model].browse(res_id)

            # Process each variable configured in the template
            for var in template.variable_ids.filtered(lambda v: v.line_type in ['body', 'header']):
                var_index = var._extract_variable_index()

                if not var_index:
                    continue

                # Get value based on field_type
                value = None

                if var.field_type == 'field' and var.field_name:
                    # Get value from record field
                    try:
                        value = record
                        for field in var.field_name.split('.'):
                            value = value[field]
                        value = str(value) if value else ''
                    except:
                        value = var.demo_value or ''

                elif var.field_type == 'user_name':
                    value = self.env.user.name

                elif var.field_type == 'user_mobile':
                    value = self.env.user.mobile or self.env.user.phone or ''

                elif var.field_type == 'free_text':
                    # Use demo value as default for free text
                    value = var.demo_value or ''

                if value:
                    variables[var_index] = value

        except Exception as e:
            # Log error but don't fail the send
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Error getting variables from template: {e}")

        return variables

    def _build_template_components(self, template, variables):
        """Build the components array for WhatsApp template with variables.

        Args:
            template: mail.whatsapp.template record
            variables: dict with variable values {1: 'value1', 2: 'value2', ...}

        Returns:
            list: Components array for WhatsApp API
        """
        components = []

        # Check if header has variables
        if template.header:
            header_params = self._extract_variables_from_text(template.header, variables)
            if header_params:
                components.append({
                    "type": "header",
                    "parameters": header_params
                })

        # Check if body has variables
        if template.body:
            body_params = self._extract_variables_from_text(template.body, variables)
            if body_params:
                components.append({
                    "type": "body",
                    "parameters": body_params
                })

        return components

    def _extract_variables_from_text(self, text, variables):
        """Extract variables from text and build parameters array.

        Args:
            text: Text with placeholders like {{1}}, {{2}}, etc.
            variables: dict with variable values

        Returns:
            list: Parameters array for WhatsApp API
        """
        if not text:
            return []

        # Find all {{number}} placeholders
        pattern = r'\{\{(\d+)\}\}'
        matches = re.findall(pattern, text)

        if not matches:
            return []

        # Build parameters array in order
        parameters = []
        for match in sorted(set(matches), key=int):
            var_num = int(match)
            value = variables.get(var_num, '')

            if value:
                parameters.append({
                    "type": "text",
                    "text": str(value)
                })

        return parameters

