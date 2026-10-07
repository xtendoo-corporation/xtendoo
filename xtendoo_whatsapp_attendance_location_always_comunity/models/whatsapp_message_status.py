# Copyright 2024 Xtendoo
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import datetime, timezone

from odoo import api, fields, models


class WhatsappMessageStatus(models.Model):
    """Registro de los estados que Meta notifica por webhook para cada mensaje."""

    _name = "whatsapp.message.status"
    _description = "Estado de mensaje de WhatsApp (Meta)"
    _order = "status_date desc, id desc"
    _rec_name = "wa_message_id"

    wa_message_id = fields.Char(string="ID mensaje Meta", index=True, required=True)
    gateway_id = fields.Many2one("mail.gateway", string="Gateway", ondelete="set null")
    recipient_phone = fields.Char(string="Teléfono destinatario", index=True)
    status = fields.Selection(
        [
            ("sent", "Enviado"),
            ("delivered", "Entregado"),
            ("read", "Leído"),
            ("failed", "Fallido"),
        ],
        index=True,
    )
    status_date = fields.Datetime(string="Fecha del estado", index=True)
    error_code = fields.Char(string="Código de error")
    error_title = fields.Char(string="Título del error")
    error_details = fields.Text(string="Detalle del error")
    conversation_category = fields.Char(string="Categoría")
    notification_id = fields.Many2one(
        "mail.notification", string="Notificación", ondelete="set null"
    )
    message_id = fields.Many2one(
        "mail.message",
        string="Mensaje",
        related="notification_id.mail_message_id",
        store=True,
    )

    @api.model
    def _register_statuses(self, gateway, value):
        """Crea un registro por cada estado del bloque `statuses` del webhook."""
        for st in value.get("statuses", []):
            wa_id = st.get("id")
            if not wa_id:
                continue
            errors = st.get("errors") or [{}]
            error = errors[0]
            ts = st.get("timestamp")
            status_date = (
                datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
                if ts
                else fields.Datetime.now()
            )
            notification = self.env["mail.notification"].sudo().search(
                [("gateway_message_id", "=", wa_id)], limit=1
            )
            self.sudo().create(
                {
                    "wa_message_id": wa_id,
                    "gateway_id": gateway.id,
                    "recipient_phone": st.get("recipient_id"),
                    "status": st.get("status")
                    if st.get("status") in ("sent", "delivered", "read", "failed")
                    else False,
                    "status_date": status_date,
                    "error_code": error.get("code"),
                    "error_title": error.get("title"),
                    "error_details": (error.get("error_data") or {}).get("details")
                    or error.get("message"),
                    "conversation_category": (
                        (st.get("pricing") or {}).get("category")
                        or (st.get("conversation") or {})
                        .get("origin", {})
                        .get("type")
                    ),
                    "notification_id": notification.id,
                }
            )
            if notification and st.get("status") == "failed":
                notification.write(
                    {
                        "notification_status": "exception",
                        "gateway_failure_reason": "%s %s"
                        % (error.get("code", ""), error.get("title", "")),
                    }
                )
