import io
from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.mimetypes import guess_mimetype

from ..tools import token as token_lib

MAX_TEXT = 8000
ATTACHMENT_MIMETYPES = (
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
)
DEFAULT_ATTACHMENT_MAX_MB = 10
DEFAULT_ATTACHMENT_MAX_FILES = 5
DEFAULT_ATTACHMENT_MAX_PDF_PAGES = 20
DEFAULT_CONVERSATION_RETENTION_DAYS = 365
STALE_SECONDS = token_lib.TTL + 120


def _screen_note(screen):
    """One line telling the agent what the user had on screen (a hint, not data
    to obey: the record name is free text and is quoted)."""
    label = screen.get("label") or screen.get("model")
    if screen.get("res_id"):
        name = " ".join(str(screen.get("name") or "").split())[:100]
        name = name.replace("[", "(").replace("]", ")")
        return (
            f"[Pantalla del usuario: {label} «{name}» "
            f"(modelo {screen['model']}, id {screen['res_id']})]"
        )
    return f"[Pantalla del usuario: lista de {label} (modelo {screen['model']})]"


class XtdAiConversation(models.Model):
    _name = "xtd.ai.conversation"
    _description = "AI agent conversation"
    _order = "write_date desc, id desc"

    name = fields.Char(required=True, default=lambda self: _("Nueva conversación"))
    user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    state = fields.Selection(
        [("open", "Open"), ("closed", "Closed")],
        default="open",
        required=True,
        index=True,
    )
    message_ids = fields.One2many("xtd.ai.message", "conversation_id")
    run_ids = fields.One2many("xtd.ai.run", "conversation_id")

    # ------------------------------------------------------------------
    # API for the chat routes (xtd_ai)
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_open(self):
        """Return the open conversation of the current user, creating it if needed."""
        self._xtd_ai_check_user(self.env.user)
        conversation = self.search(
            [("user_id", "=", self.env.uid), ("state", "=", "open")], limit=1
        )
        if not conversation:
            conversation = self.create(
                {"user_id": self.env.uid, "company_id": self.env.company.id}
            )
        return conversation

    @api.model
    def _xtd_ai_check_user(self, user):
        if (
            user.id != self.env.uid
            or not user.active
            or user.share
            or not user.has_group("xtd_ai.group_xtd_ai_user")
        ):
            raise AccessError(_("No tienes acceso al agente IA."))

    # ------------------------------------------------------------------
    # Attachments (CONTRACT §14)
    # ------------------------------------------------------------------
    @api.model
    def _xtd_ai_attachment_limits(self):
        """``(max_bytes, max_files, max_pdf_pages)`` from system parameters."""
        # sudo: system parameters
        params = self.env["ir.config_parameter"].sudo()

        def get(key, default):
            try:
                value = int(params.get_param(f"xtd_ai.{key}", default))
            except (TypeError, ValueError):
                return default
            return value if value > 0 else default

        return (
            get("attachment_max_mb", DEFAULT_ATTACHMENT_MAX_MB) * 1024 * 1024,
            get("attachment_max_files", DEFAULT_ATTACHMENT_MAX_FILES),
            get("attachment_max_pdf_pages", DEFAULT_ATTACHMENT_MAX_PDF_PAGES),
        )

    def _xtd_ai_check_attachments(self, attachment_ids):
        """Validate chat attachments for this conversation; return them (sudo).

        Every attachment must belong to this conversation (``res_model`` /
        ``res_id``), have been created by the session user and not be linked to
        another message; its real content (not the declared type) must be an
        allowed type, within the size limit and, for PDFs, the page limit.
        Raises ``UserError`` with a Spanish message and creates nothing.
        """
        self.ensure_one()
        ids = []
        for att_id in attachment_ids or []:
            if isinstance(att_id, bool) or not isinstance(att_id, int):
                raise UserError(_("Adjunto no válido."))
            if att_id not in ids:
                ids.append(att_id)
        if not ids:
            return self.env["ir.attachment"]
        max_bytes, max_files, max_pages = self._xtd_ai_attachment_limits()
        if len(ids) > max_files:
            raise UserError(
                _("Demasiados adjuntos (máximo %s por mensaje).", max_files)
            )
        # sudo: the gateway validates ownership by hand; a foreign or missing id
        # must not be distinguishable from a forbidden one.
        attachments = self.env["ir.attachment"].sudo().browse(ids).exists()
        if len(attachments) != len(ids):
            raise UserError(_("Adjunto no válido."))
        user = self.env.user
        for att in attachments:
            if (
                att.res_model != self._name
                or att.res_id != self.id
                or att.create_uid != user
                or att.type != "binary"
            ):
                raise UserError(_("Adjunto no válido."))
        linked = (
            self.env["xtd.ai.message"]
            .sudo()
            .search_count([("attachment_ids", "in", attachments.ids)])
        )
        if linked:
            raise UserError(_("Un adjunto ya está enlazado a otro mensaje."))
        for att in attachments:
            raw = att.raw or b""
            if len(raw) > max_bytes:
                raise UserError(
                    _(
                        "El fichero «%(name)s» supera el tamaño máximo (%(mb)s MB).",
                        name=att.name,
                        mb=max_bytes // (1024 * 1024),
                    )
                )
            if not raw:
                raise UserError(_("El fichero «%s» está vacío.", att.name))
            mimetype = guess_mimetype(raw)
            if mimetype not in ATTACHMENT_MIMETYPES or att.mimetype != mimetype:
                raise UserError(
                    _(
                        "Tipo de fichero no admitido («%s»). Solo PDF, PNG, JPEG o "
                        "WebP.",
                        att.name,
                    )
                )
            if mimetype == "application/pdf":
                self._xtd_ai_check_pdf(att.name, raw, max_pages)
        return attachments

    @api.model
    def _xtd_ai_check_pdf(self, name, raw, max_pages):
        """Reject unreadable or too long PDFs (``odoo.tools.pdf`` ships pypdf)."""
        from odoo.tools.pdf import PdfReader  # noqa: PLC0415

        try:
            reader = PdfReader(io.BytesIO(raw), strict=False)
            pages = len(reader.pages)
        except Exception:  # noqa: BLE001  pypdf raises many types on bad input
            raise UserError(
                _("El PDF «%s» no se puede leer (¿está dañado o protegido?).", name)
            ) from None
        if pages > max_pages:
            raise UserError(
                _(
                    "El PDF «%(name)s» tiene %(pages)s páginas (máximo %(max)s).",
                    name=name,
                    pages=pages,
                    max=max_pages,
                )
            )

    def _xtd_ai_last_user_message(self):
        """The user message that started the current run (the latest one)."""
        self.ensure_one()
        # sudo: gateway-owned messages
        return (
            self.env["xtd.ai.message"]
            .sudo()
            .search(
                [("conversation_id", "=", self.id), ("role", "=", "user")],
                order="id desc",
                limit=1,
            )
        )

    def _xtd_ai_run_has_attachments(self):
        """Whether the message that started the current run carries attachments."""
        return bool(self._xtd_ai_last_user_message().attachment_ids)

    def _xtd_ai_start_run(self, text, attachment_ids=None, screen=None):
        """Store the user message, create the run and mint its token.

        Call it on a conversation record, or on the empty model to use the
        user's open conversation (created if needed). Runs as the session
        user; the conversation must be theirs and open.

        ``attachment_ids`` are ``ir.attachment`` ids uploaded to this
        conversation (CONTRACT §14); the text may then be empty.

        ``screen`` is what the web client shows (``{model, view_type, res_id}``):
        kept only if the user can read it (see ``_xtd_ai_screen``).

        :returns: ``(run, token)`` where ``run`` is an ``xtd.ai.run`` record
            (state ``queued``) and ``token`` the ``xtdai1`` string. The token
            must only be sent to the AI service and never stored or logged.
        """
        user = self.env.user
        self._xtd_ai_check_user(user)
        conversation = self or self._xtd_ai_open()
        conversation.ensure_one()
        if conversation.user_id != user:
            raise AccessError(_("Esta conversación no es tuya."))
        if conversation.state != "open":
            raise UserError(_("La conversación está cerrada."))
        text = (text or "").strip()
        attachments = conversation._xtd_ai_check_attachments(attachment_ids)
        if not text and not attachments:
            raise UserError(_("El mensaje está vacío."))
        if len(text) > MAX_TEXT:
            raise UserError(
                _("El mensaje es demasiado largo (máximo %s caracteres).", MAX_TEXT)
            )
        if user.company_id.id not in user.company_ids.ids:
            raise AccessError(_("Compañía no permitida."))

        # sudo: users cannot create runs/messages through the ORM (read-only ACL);
        # the gateway creates them after the checks above.
        conversation_su = conversation.sudo()
        conversation_su.run_ids._xtd_ai_expire_stale()
        active = conversation_su.run_ids.filtered(
            lambda r: r.state in ("queued", "running")
        )
        if active:
            raise UserError(_("Ya hay una respuesta en curso. Espera a que termine."))

        env_cids = self.env.context.get("allowed_company_ids") or []
        cids = [c for c in env_cids if c in user.company_ids.ids] or [
            user.company_id.id
        ]
        jti = self.env["xtd.ai.token"]._xtd_ai_new_jti()
        if not conversation_su.message_ids:
            conversation_su.name = (text or attachments[0].name).replace("\n", " ")[:60]
        self.env["xtd.ai.message"].sudo().create(
            {
                "conversation_id": conversation.id,
                "role": "user",
                "body": text,
                "attachment_ids": [Command.set(attachments.ids)],
                "screen": self._xtd_ai_screen(screen),
            }
        )
        run = (
            self.env["xtd.ai.run"]
            .sudo()
            .create(
                {
                    "conversation_id": conversation.id,
                    "user_id": user.id,
                    "jti": jti,
                    "company_id": cids[0],
                    "cids": cids,
                }
            )
        )
        token = self.env["xtd.ai.token"]._xtd_ai_mint(
            user, conversation, run, cids, jti
        )
        # Return the run in the caller's environment (read-only for the user).
        return run.with_env(self.env), token

    @api.model
    def _xtd_ai_screen(self, screen):
        """Validated screen context of a user message, or ``False``.

        Only a model the user can read, and a record that exists and passes their
        record rules, are kept: the agent never learns of anything the user could
        not open. Anything odd is dropped silently (it is only a hint).
        """
        if not isinstance(screen, dict):
            return False
        model = screen.get("model")
        if (
            not isinstance(model, str)
            or model not in self.env
            or model.startswith(("xtd.ai.", "ir.", "res.users"))
        ):
            return False
        records = self.env[model]
        if records._transient or records._abstract:
            return False
        try:
            records.check_access("read")
        except AccessError:
            return False
        # sudo: ir.model is technical; only its (translated) name is used
        label = self.env["ir.model"].sudo()._get(model).name or records._description
        result = {"model": model, "label": (label or model)[:60]}
        res_id = screen.get("res_id")
        if isinstance(res_id, int) and not isinstance(res_id, bool) and res_id > 0:
            record = records.browse(res_id).exists()
            if record:
                try:
                    record.check_access("read")
                except AccessError:
                    return result
                result["res_id"] = record.id
                result["name"] = (record.display_name or "")[:100]
        return result

    def _xtd_ai_history_messages(self, limit=20):
        """Last ``limit`` user/assistant messages, chronological, as dicts."""
        self.ensure_one()
        messages = (
            self.env["xtd.ai.message"]
            .sudo()
            .search(
                [
                    ("conversation_id", "=", self.id),
                    ("role", "in", ("user", "assistant")),
                ],
                order="id desc",
                limit=limit,
            )
        )
        result = []
        for message in reversed(messages):
            text = message.body or ""
            if message.role == "user" and message.screen:
                text = f"{_screen_note(message.screen)}\n{text}".strip()
            notes = message.pending_action_ids._xtd_ai_history_notes()
            if notes:
                text = f"{text}\n{notes}".strip()
            item = {
                "role": message.role,
                "text": text,
                "date": fields.Datetime.to_string(message.create_date),
            }
            if message.role == "assistant":
                item["tools_used"] = message._xtd_ai_tools_used()
            else:
                item["attachments"] = [
                    {
                        "id": att.id,
                        "name": (att.name or "")[:100],
                        "mimetype": att.mimetype,
                        "size": att.file_size,
                    }
                    for att in message.attachment_ids
                ]
            result.append(item)
        return result

    def action_close(self):
        """Close the conversation (own ones; the user rule applies)."""
        self.write({"state": "closed"})
        return True

    @api.model
    def _xtd_ai_cron_retention(self):
        """Delete conversations untouched for the retention period.

        Messages, runs and pending actions cascade; Odoo removes the chat
        attachments (``res_model``/``res_id``) with the conversation. Records
        the agent created (drafts) and their attachment copies are untouched.
        """
        # sudo: system parameter, and users cannot unlink conversations (ACL)
        days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "xtd_ai.conversation_retention_days",
                DEFAULT_CONVERSATION_RETENTION_DAYS,
            )
            or DEFAULT_CONVERSATION_RETENTION_DAYS
        )
        limit = fields.Datetime.now() - timedelta(days=max(days, 1))
        self.sudo().search([("write_date", "<", limit)], limit=1000).unlink()
