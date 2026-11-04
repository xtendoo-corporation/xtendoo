"""Payment reminder by email for an overdue customer invoice (wave 2B).

Always a card (N2) with recipient, subject and text; the text is a fixed one
filled with the invoice data, never written by the model. The tool only posts
the message on that invoice: it never posts, pays or modifies it. The email is
the only way out and its guard is lifted for that one invoice inside this tool.
"""

from datetime import timedelta

from odoo import fields, models
from odoo.tools import plaintext2html
from odoo.tools.misc import format_date, formatLang

from odoo.addons.xtd_ai.tools import XtdAiToolError, unlock, xtd_ai_tool

from .xtd_ai_toolbox_account import _WRITE_GROUPS, _obj


class XtdAiToolboxAccountReminder(models.AbstractModel):
    _name = "xtd.ai.toolbox.account.reminder"
    _inherit = "xtd.ai.toolbox"
    _description = "AI tools: payment reminders"

    _xtd_ai_skills = {"cobros": "data/skills/cobros.md"}
    _xtd_ai_skill_hints = {
        "cobros": {
            "models": (),
            "words": (
                "recordatorio",
                "recordar",
                "reclamar",
                "reclamacion",
                "cobro",
                "cobrar",
                "vencid",
                "moroso",
                "impagad",
            ),
        }
    }

    def _xtd_ai_overdue_invoice(self, ref):
        invoice = self._xtd_ai_resolve(
            "account.move", ref, domain=[("move_type", "=", "out_invoice")]
        )
        invoice.check_access("read")
        env = self.env
        today = fields.Date.context_today(self)
        if (
            invoice.state != "posted"
            or invoice.payment_state not in ("not_paid", "partial")
            or not invoice.invoice_date_due
            or invoice.invoice_date_due >= today
        ):
            raise XtdAiToolError(
                "validation",
                env._(
                    "%s no es una factura publicada, pendiente y vencida: no se "
                    "le manda recordatorio.",
                    invoice.name or invoice.display_name,
                ),
            )
        partner = invoice.partner_id
        if not partner.email:
            raise XtdAiToolError(
                "validation",
                env._(
                    "%s no tiene correo electrónico: añádelo en su ficha.",
                    partner.display_name,
                ),
            )
        return invoice

    def _xtd_ai_reminder_window_hours(self):
        """Ventana antirrepetición en horas (0 desactiva la protección)."""
        # Parámetro xtd_ai.payment_reminder_window_hours (solo sistema: lo lee la config)
        raw = self.env["xtd.ai.agent.config"]._xtd_ai_param(
            "payment_reminder_window_hours", "24"
        )
        try:
            return max(float(raw), 0.0)
        except (TypeError, ValueError):
            return 24.0

    def _xtd_ai_recent_reminders(self, invoice):
        """Recordatorios ya enviados para esta factura dentro de la ventana."""
        hours = self._xtd_ai_reminder_window_hours()
        if not hours:
            return self.env["mail.message"]
        subject, _body, _amount = self._xtd_ai_reminder_text(invoice)
        since = fields.Datetime.now() - timedelta(hours=hours)
        # La factura ya se leyó con los permisos del usuario: sus mensajes también
        return invoice.message_ids.filtered(
            lambda m: m.message_type == "comment"
            and m.subject == subject
            and m.date >= since
        )

    def _xtd_ai_check_no_recent_reminder(self, invoice):
        recent = self._xtd_ai_recent_reminders(invoice)
        if recent:
            hours = self._xtd_ai_reminder_window_hours()
            raise XtdAiToolError(
                "validation",
                self.env._(
                    "Ya se envió un recordatorio de %(name)s el %(date)s (hay "
                    "protección de %(hours)s h contra repetidos): no se reenvía. "
                    "Díselo al usuario.",
                    name=invoice.name,
                    date=format_date(self.env, max(recent.mapped("date"))),
                    hours=int(hours),
                ),
            )

    def _xtd_ai_reminder_text(self, invoice):
        env = self.env
        amount = formatLang(
            env, invoice.amount_residual, currency_obj=invoice.currency_id
        )
        subject = env._(
            "Recordatorio de pago: factura %(name)s",
            name=invoice.name,
        )
        body = env._(
            "Estimado cliente:\n\n"
            "Le recordamos que la factura %(name)s, con vencimiento el %(due)s, "
            "tiene pendiente un importe de %(amount)s.\n\n"
            "Si ya ha realizado el pago, por favor ignore este mensaje.\n\n"
            "Un saludo,\n%(company)s",
            name=invoice.name,
            due=format_date(env, invoice.invoice_date_due),
            amount=amount,
            company=invoice.company_id.name,
        )
        return subject, body, amount

    @xtd_ai_tool(
        name="send_payment_reminder",
        title="Recordatorio de cobro",
        description=(
            "Manda por correo un recordatorio de pago de una factura de cliente "
            "publicada y vencida a su cliente, con un texto fijo de XTD (importe "
            "pendiente y vencimiento). No cambia la factura. El destinatario es el "
            "cliente de la factura y el texto no lo escribes tú. Queda una tarjeta "
            "con destinatario, asunto y texto. Una factura por llamada."
        ),
        input_schema=_obj(
            {
                "invoice": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "Id numérico (preferible) o número de la factura.",
                }
            },
            ["invoice"],
        ),
        kind="draft",
        skill="cobros",
        groups=_WRITE_GROUPS,
        requires=["account.move"],
        op_class="send_external",
        preview="_xtd_ai_preview_send_payment_reminder",
        handoff="_xtd_ai_handoff_send_payment_reminder",
        unlocks=("account.move.send_email",),
    )
    def tool_send_payment_reminder(self, args):
        invoice = self._xtd_ai_overdue_invoice(args["invoice"])
        # Se re-comprueba al confirmar: entre la tarjeta y el clic pudo salir otro
        self._xtd_ai_check_no_recent_reminder(invoice)
        subject, body, _amount = self._xtd_ai_reminder_text(invoice)
        partner = invoice.partner_id
        unlock(invoice, "send_email").message_post(
            subject=subject,
            body=plaintext2html(body),
            partner_ids=partner.ids,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            email_layout_xmlid="mail.mail_notification_light",
        )
        return {
            "data": {
                "invoice": invoice.name,
                "sent_to": partner.email,
                "undo": self.env._("Un correo enviado no se puede retirar."),
            },
            "records": [self._xtd_ai_ref(invoice) | {"undo_edit": {"before": {}}}],
        }

    def _xtd_ai_preview_send_payment_reminder(self, args):
        invoice = self._xtd_ai_overdue_invoice(args["invoice"])
        # Con uno reciente no hay tarjeta: se explica y no se reenvía
        self._xtd_ai_check_no_recent_reminder(invoice)
        subject, body, amount = self._xtd_ai_reminder_text(invoice)
        partner = invoice.partner_id
        window = self._xtd_ai_reminder_window_hours()
        subtype = self.env.ref("mail.mt_comment")
        followers = invoice.message_follower_ids.filtered(
            lambda f: f.partner_id
            and f.partner_id != partner
            and f.partner_id != self.env.user.partner_id
            and subtype in f.subtype_ids
        ).partner_id
        extra = (
            [
                {
                    "field": self.env._("Seguidores avisados"),
                    "value": ", ".join(
                        f"{p.display_name} <{p.email or '-'}>" for p in followers[:5]
                    ),
                }
            ]
            if followers
            else []
        )
        return {
            "summary": self.env._(
                "Recordar a %(partner)s el pago de %(name)s (%(amount)s)",
                partner=(partner.display_name or "")[:60],
                name=invoice.name,
                amount=amount,
            ),
            "lines": [
                {
                    "field": self.env._("Para"),
                    "value": f"{partner.display_name} <{partner.email}>",
                },
            ]
            + extra
            + [
                {
                    "field": self.env._("Recordatorios previos"),
                    "value": self.env._(
                        "Ninguno en las últimas %s h", int(window)
                    )
                    if window
                    else self.env._("Protección antirrepetidos desactivada"),
                },
                {"field": self.env._("Asunto"), "value": subject},
                {"field": self.env._("Texto"), "value": body[:300]},
                {
                    "field": self.env._("Efecto"),
                    "value": self.env._(
                        "Sale un correo real al cliente y queda en el historial de "
                        "la factura. La factura no cambia."
                    ),
                },
            ],
            "confirm_label": self.env._("Enviar"),
            "irreversible": True,
        }

    def _xtd_ai_handoff_send_payment_reminder(self, args):
        invoice = self._xtd_ai_overdue_invoice(args["invoice"])
        return invoice, self.env._("Enviar mensaje")
