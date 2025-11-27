# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models


class WhatsappComposer(models.TransientModel):
    _inherit = "whatsapp.composer"

    # Variables dinámicas para plantillas (similar a Enterprise)
    variable_1 = fields.Char(string="Variable 1")
    variable_2 = fields.Char(string="Variable 2")
    variable_3 = fields.Char(string="Variable 3")
    variable_4 = fields.Char(string="Variable 4")
    variable_5 = fields.Char(string="Variable 5")
    variable_6 = fields.Char(string="Variable 6")
    variable_7 = fields.Char(string="Variable 7")
    variable_8 = fields.Char(string="Variable 8")
    variable_9 = fields.Char(string="Variable 9")
    variable_10 = fields.Char(string="Variable 10")

    has_variables = fields.Boolean(
        compute="_compute_has_variables",
        string="Template has variables"
    )
    variable_count = fields.Integer(
        compute="_compute_has_variables",
        string="Number of variables"
    )

    @api.depends("template_id", "template_id.body", "template_id.header")
    def _compute_has_variables(self):
        """Detectar si la plantilla tiene variables {{1}}, {{2}}, etc."""
        for composer in self:
            if not composer.template_id:
                composer.has_variables = False
                composer.variable_count = 0
                continue

            # Buscar placeholders {{1}}, {{2}}, etc en body y header
            text = (composer.template_id.body or "") + (composer.template_id.header or "")

            # Pattern para encontrar {{número}}
            pattern = r'\{\{(\d+)\}\}'
            matches = re.findall(pattern, text)

            if matches:
                composer.has_variables = True
                # Obtener el número más alto
                composer.variable_count = max([int(m) for m in matches])
            else:
                composer.has_variables = False
                composer.variable_count = 0

    @api.onchange("template_id")
    def onchange_template_id(self):
        """Cuando cambia la plantilla, actualizar el body con valores de variables."""
        # Llamar al método del módulo padre (sin guion bajo)
        res = super().onchange_template_id()

        if self.template_id and self.has_variables:
            # Pre-cargar valores de ejemplo o del registro
            self._populate_variables_from_record()

        return res

    def _populate_variables_from_record(self):
        """Intentar poblar variables automáticamente desde el registro."""
        if not self.res_model or not self.res_id:
            return

        try:
            record = self.env[self.res_model].browse(self.res_id)

            # Mapeo común de variables para diferentes modelos
            variable_mapping = {
                'res.partner': {
                    1: 'name',
                    2: 'email',
                    3: 'phone',
                    4: 'mobile',
                    5: 'street',
                    6: 'city',
                },
                'sale.order': {
                    1: 'partner_id.name',
                    2: 'name',
                    3: 'amount_total',
                    4: 'date_order',
                },
                'account.move': {
                    1: 'partner_id.name',
                    2: 'name',
                    3: 'amount_total',
                    4: 'invoice_date',
                },
            }

            mapping = variable_mapping.get(self.res_model, {})

            for var_num, field_path in mapping.items():
                if var_num <= 10:  # Solo tenemos 10 variables
                    try:
                        # Obtener valor del campo (puede ser campo relacionado)
                        value = record
                        for field in field_path.split('.'):
                            value = value[field]

                        # Convertir a string y asignar
                        if value:
                            setattr(self, f'variable_{var_num}', str(value))
                    except:
                        pass  # Si falla, dejar vacío
        except:
            pass  # Si hay error, no hacer nada

    def _get_body_with_variables(self):
        """Reemplazar placeholders {{1}}, {{2}}, etc con valores de variables."""
        body = self.body

        if not body or not self.has_variables:
            return body

        # Reemplazar cada {{número}} con su variable correspondiente
        for i in range(1, 11):
            variable_value = getattr(self, f'variable_{i}', '')
            if variable_value:
                # Reemplazar {{i}} con el valor de la variable
                body = body.replace(f'{{{{{i}}}}}', str(variable_value))

        return body

    def _action_send_whatsapp(self):
        """Override para reemplazar variables antes de enviar."""
        # Si hay variables, actualizar el body con los valores
        if self.has_variables:
            original_body = self.body
            self.body = self._get_body_with_variables()

        # Llamar al método original
        result = super()._action_send_whatsapp()

        # Restaurar body original (por si se reutiliza el wizard)
        if self.has_variables:
            self.body = original_body

        return result

