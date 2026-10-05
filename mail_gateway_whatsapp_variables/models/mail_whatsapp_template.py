# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
import re


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    # Campos para flujo de confirmación automática
    requires_confirmation = fields.Boolean(
        string="Requiere Confirmación",
        default=False,
        help="Si está marcado, esta plantilla espera una respuesta del cliente antes de enviar otra plantilla automáticamente"
    )
    confirmation_template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="Plantilla tras Confirmación",
        help="Plantilla que se enviará automáticamente cuando el cliente responda"
    )
    confirmation_type = fields.Selection([
        ('button', 'Botón Interactivo (cualquier botón)'),
        ('text_si', 'Texto: "Sí" o "Si"'),
        ('text_ok', 'Texto: "OK" o "ok"'),
        ('any', 'Cualquier Respuesta')
    ], string="Tipo de Confirmación", default='button',
       help="Tipo de respuesta esperada para activar la plantilla de confirmación")

    def _prepare_values_to_import(self, gateway, json_data):
        # OCA pairs existing buttons by name only and breaks (singleton error)
        # when several share the text. ``self`` is only used there for
        # ``button_ids``, so call it on an empty recordset (all buttons come
        # back as creates) and re-pair them in ``_match_import_buttons``.
        vals = super(MailWhatsappTemplate, self.browse())._prepare_values_to_import(
            gateway, json_data
        )
        # Si la plantilla está aprobada por Meta, la consideramos soportada
        if json_data.get("status", "").lower() == "approved":
            vals["is_supported"] = True
        if vals.get("button_ids"):
            # Callers may use the empty model, so fall back to looking the
            # existing template up by its Meta id to re-pair buttons.
            template = self or self.with_context(active_test=False).search(
                [
                    ("gateway_id", "=", gateway.id),
                    ("template_uid", "=", json_data.get("id")),
                ],
                limit=1,
            )
            vals["button_ids"] = template._match_import_buttons(vals["button_ids"])
        return vals

    def _match_import_buttons(self, button_commands):
        """Re-pair the buttons computed by OCA with the existing ones.

        OCA matches by name only, but Meta allows several buttons with the same
        text in one template. Here the match is by position (``sequence`` holds
        the index in ``component["buttons"]``) and by type, falling back to
        name + type for buttons whose stored order differs. ``self`` may be an
        empty recordset (new template), in which case everything is created.
        """
        existing = self.button_ids.sorted(lambda btn: (btn.sequence, btn.id))
        claimed = self.env["mail.whatsapp.template.button"]
        commands = []
        for command in button_commands:
            button_vals = command[2]
            index = button_vals["sequence"]
            candidates = existing - claimed
            button = existing[index : index + 1] - claimed
            if button.button_type != button_vals["button_type"]:
                button = candidates.filtered(
                    lambda btn, vals=button_vals: btn.button_type == vals["button_type"]
                    and btn.name == vals["name"]
                )[:1]
            if button:
                claimed |= button
                commands.append(Command.update(button.id, button_vals))
            else:
                commands.append(Command.create(button_vals))
        return commands


class MailWhatsappTemplateButton(models.Model):
    _inherit = "mail.whatsapp.template.button"

    # Same key as OCA's: the ORM merges _sql_constraints by key, so this one
    # replaces it and ``_add_sql_constraints`` swaps it in the DB on ``-u``.
    # Meta allows repeated texts in a template (e.g. quick reply + URL).
    _sql_constraints = [
        (
            "unique_name_per_template",
            "UNIQUE(name, button_type, template_id, sequence)",
            "Button name must be unique by template, type and position",
        )
    ]
