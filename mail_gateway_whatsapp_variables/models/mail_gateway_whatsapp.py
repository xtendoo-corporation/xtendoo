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
        import logging
        _logger = logging.getLogger(__name__)

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

                _logger.info(f"Template: {whatsapp_template.name}, has variables: {bool(whatsapp_template.variable_ids)}")

                # Check if template has variables configured
                if whatsapp_template.variable_ids:
                    # Get values from context or from record
                    template_variables = self.env.context.get("template_variables", {})

                    # If no variables in context, try to get them from the record
                    if not template_variables:
                        template_variables = self._get_variables_from_template(
                            whatsapp_template, channel
                        )

                    _logger.info(f"Variables obtained: {template_variables}")

                    # Build components array with variables
                    if template_variables:
                        components = self._build_template_components(
                            whatsapp_template, template_variables
                        )

                        _logger.info(f"Components built: {components}")

                        if components:
                            payload["template"]["components"] = components
                            _logger.info(f"Final payload: {payload}")

        return payload

    def _get_variables_from_template(self, template, channel=None):
        """Get variable values from the record specified in the template's model.

        Args:
            template: mail.whatsapp.template record
            channel: discuss.channel record (optional)

        Returns:
            dict: Variable values {1: 'value1', 2: 'value2', ...}
        """
        import logging
        _logger = logging.getLogger(__name__)

        variables = {}

        # Check if template has a model configured
        if not template.model_id:
            _logger.warning(f"Template {template.name} has no model configured, using demo values")
            for var in template.variable_ids.filtered(lambda v: v.line_type in ['body', 'header']):
                var_index = var._extract_variable_index()
                if var_index and var.demo_value:
                    variables[var_index] = var.demo_value
            return variables

        # Get the model from the template
        res_model = template.model_id.model
        _logger.info(f"Template model: {res_model}")

        res_id = None

        # PRIORITY 1: If template is for res.partner and we have a channel, get partner from channel
        # This is the CORRECT destinatary of the message
        if res_model == 'res.partner' and channel:
            if hasattr(channel, 'channel_partner_ids') and channel.channel_partner_ids:
                # Filter out OdooBot and current user
                partners = channel.channel_partner_ids.filtered(
                    lambda p: p.id != self.env.ref('base.partner_root').id and p.id != self.env.user.partner_id.id
                )
                if partners:
                    res_id = partners[0].id
                    _logger.info(f"Got partner ID from channel (destinatary): {res_id}")

        # PRIORITY 2: Try to get from context active_id
        if not res_id:
            res_id = self.env.context.get("active_id")
            if res_id:
                _logger.info(f"Got ID from context active_id: {res_id}")

        # PRIORITY 3: Try to get from context default_res_id
        if not res_id:
            res_id = self.env.context.get("default_res_id")
            if res_id:
                _logger.info(f"Got ID from context default_res_id: {res_id}")

        if not res_id:
            # Fallback to demo values
            _logger.warning(f"No record ID found for model {res_model}, using demo values")
            for var in template.variable_ids.filtered(lambda v: v.line_type in ['body', 'header']):
                var_index = var._extract_variable_index()
                if var_index and var.demo_value:
                    variables[var_index] = var.demo_value
            return variables

        try:
            record = self.env[res_model].browse(res_id)
            _logger.info(f"Using record: {record.display_name} (Model: {res_model}, ID: {res_id})")

            # Get filtered variables
            template_vars = template.variable_ids.filtered(lambda v: v.line_type in ['body', 'header'])
            _logger.info(f"Processing {len(template_vars)} variables from template")

            # Process each variable configured in the template
            for var in template_vars:
                _logger.info(f"Processing variable: {var.name}, variable_index: {var.variable_index}, field_type: {var.field_type}, field_name: {var.field_name}")

                var_index = var._extract_variable_index()
                _logger.info(f"Variable index extracted: {var_index}")

                if not var_index:
                    _logger.warning(f"No valid index for variable {var.name}")
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
                        _logger.info(f"Got field value: {value}")
                    except Exception as ex:
                        value = var.demo_value or ''
                        _logger.warning(f"Error getting field value: {ex}, using demo: {value}")

                elif var.field_type == 'user_name':
                    value = self.env.user.name
                    _logger.info(f"Got user_name: {value}")

                elif var.field_type == 'user_mobile':
                    value = self.env.user.mobile or self.env.user.phone or ''
                    _logger.info(f"Got user_mobile: {value}")

                elif var.field_type == 'free_text':
                    # Use demo value as default for free text
                    value = var.demo_value or ''
                    _logger.info(f"Got free_text: {value}")

                if value:
                    variables[var_index] = value
                    _logger.info(f"Added variable {var_index}: {value}")
                else:
                    _logger.warning(f"No value for variable {var.name} (index {var_index})")

            _logger.info(f"Final variables collected: {variables}")

        except Exception as e:
            # Log error but don't fail the send
            _logger.error(f"Exception in _get_variables_from_template: {e}", exc_info=True)

        return variables

    def _build_template_components(self, template, variables):
        """Build the components array for WhatsApp template with variables.

        Args:
            template: mail.whatsapp.template record
            variables: dict with variable values {1: 'value1', 2: 'value2', ...}

        Returns:
            list: Components array for WhatsApp API
        """
        import logging
        _logger = logging.getLogger(__name__)

        components = []

        # Check if header has variables
        if template.header:
            header_params = self._extract_variables_from_text(template.header, variables)
            if header_params:
                components.append({
                    "type": "header",
                    "parameters": header_params
                })
                _logger.info(f"Added header component with {len(header_params)} parameters")

        # Check if body has variables
        if template.body:
            body_params = self._extract_variables_from_text(template.body, variables)
            if body_params:
                components.append({
                    "type": "body",
                    "parameters": body_params
                })
                _logger.info(f"Added body component with {len(body_params)} parameters")

        # Process buttons with dynamic URLs (if any)
        if hasattr(template, 'button_ids') and template.button_ids:
            button_components = self._build_button_components(template)
            if button_components:
                components.extend(button_components)
                _logger.info(f"Added {len(button_components)} button components")

        _logger.info(f"Total components: {len(components)}")
        return components

    def _build_button_components(self, template):
        """Build button components for WhatsApp template.

        Args:
            template: mail.whatsapp.template record

        Returns:
            list: Button components array for WhatsApp API
        """
        import logging
        _logger = logging.getLogger(__name__)

        components = []

        # Process URL buttons with dynamic type
        dynamic_url_buttons = template.button_ids.filtered(
            lambda b: b.button_type == 'url' and b.url_type == 'dynamic'
        )

        for idx, button in enumerate(dynamic_url_buttons):
            # For dynamic URLs, we need to provide the dynamic suffix parameter
            # The base URL is in the template, we only send the dynamic part
            dynamic_suffix = self.env.context.get(f'button_dynamic_url_{idx}', '')

            if dynamic_suffix:
                components.append({
                    "type": "button",
                    "sub_type": "url",
                    "index": str(idx),
                    "parameters": [{
                        "type": "text",
                        "text": dynamic_suffix
                    }]
                })
                _logger.info(f"Added dynamic URL button component for '{button.name}' with suffix: {dynamic_suffix}")
            else:
                _logger.warning(f"Dynamic URL button '{button.name}' has no dynamic suffix in context")

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

