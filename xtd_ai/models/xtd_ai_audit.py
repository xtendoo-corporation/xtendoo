import logging
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

TEXT_LIMIT = 300
AUTH_FAILED_BURST = 100  # max auth_failed rows per minute (flood protection)

# Plazos de conservación (RGPD art. 5.1.c minimización y 5.1.e limitación del plazo;
# LOPDGDD). El RGPD no fija un número de días: se conserva solo lo necesario para la
# finalidad (trazabilidad y seguridad de las acciones del agente). Por defecto la
# conversación (que contiene el texto libre del usuario) 90 días y el registro de
# auditoría (sin texto libre, con datos personales ofuscados) 180 días, el plazo
# habitual en registros de seguridad. Configurables por ``ir.config_parameter``;
# los mínimos evitan dejar el registro inservible para investigar un incidente.
DEFAULT_AUDIT_RETENTION_DAYS = 180
MIN_AUDIT_RETENTION_DAYS = 30
DEFAULT_CONVERSATION_RETENTION_DAYS = 90
MIN_CONVERSATION_RETENTION_DAYS = 30
PURGE_BATCH = 5000  # filas por lote en la purga de auditoría
PURGE_MAX_BATCHES = 10  # lotes por ejecución del cron (el resto, al día siguiente)


def retention_days(env, key, default, minimum):
    """Días de retención del parámetro ``key``: valor inválido -> ``default``;
    nunca menos de ``minimum``."""
    # sudo: parámetro de sistema
    raw = env["ir.config_parameter"].sudo().get_param(key, default)
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = default
    if days <= 0:
        days = default
    return max(days, minimum)


# Minimización (art. 5.1.c): en la auditoría se ofuscan los datos personales de los
# argumentos; se conserva un prefijo corto para poder correlacionar a mano, nunca el
# dato completo. Lo que no se puede detectar (nombres en texto libre) se acota con el
# plazo corto. Se mantienen herramienta, ids, resultado y error.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]{4}){2,7}(?:[ -]?[A-Z0-9]{1,4})?\b")
_NIF_RE = re.compile(
    r"\b(?:ES-?)?(?:[XYZ]-?\d{7}-?[A-Z]|\d{8}-?[A-Z]|[A-HJNP-SUVW]-?\d{7}-?[0-9A-J])\b",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?<![\w.])(?:(?:\+|00)\d{1,3}[\s.-]?)?[6-9]\d{2}[\s.-]?\d{2,3}[\s.-]?\d{2,3}"
    r"(?:[\s.-]?\d{2,3})?(?![\w])"
)
# Claves cuyo valor es siempre un dato personal.
_PERSONAL_KEYS = {
    "vat", "nif", "cif", "dni", "email", "email_from", "email_to", "email_cc",
    "phone", "mobile", "telefono", "iban", "acc_number", "partner_name",
    "contact_name", "customer_name", "employee_name", "street", "street2",
}  # fmt: skip


def _mask(text, keep):
    return text[:keep] + "***"


def redact_personal_text(text):
    """Ofusca en ``text`` emails, IBAN, NIF/CIF/NIE y teléfonos (prefijo + ``***``)."""
    text = _EMAIL_RE.sub(lambda m: _mask(m.group(0), 2) + "@***", text)
    text = _IBAN_RE.sub(lambda m: _mask(m.group(0), 4), text)
    text = _NIF_RE.sub(lambda m: _mask(m.group(0), 2), text)
    return _PHONE_RE.sub(lambda m: _mask(m.group(0), 3), text)


def redact_personal(value, key=None, depth=0):
    """Copia de ``value`` con los datos personales ofuscados (dicts/listas/textos)."""
    if depth > 6:
        return None
    if key is not None and str(key).lower() in _PERSONAL_KEYS and value:
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            return _mask(str(value), 2)
    if isinstance(value, str):
        return redact_personal_text(value)
    if isinstance(value, dict):
        return {k: redact_personal(v, k, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_personal(v, key, depth + 1) for v in value]
    return value


def truncate_texts(value, depth=0):
    """Return a JSON-safe copy of ``value`` with every string cut to 300 chars."""
    if depth > 6:
        return None
    if isinstance(value, str):
        return value if len(value) <= TEXT_LIMIT else value[:TEXT_LIMIT] + "..."
    if isinstance(value, dict):
        return {str(k): truncate_texts(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [truncate_texts(v, depth + 1) for v in value[:100]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:TEXT_LIMIT]


class XtdAiAudit(models.Model):
    _name = "xtd.ai.audit"
    _description = "AI agent audit log"
    _order = "id desc"

    run_id = fields.Many2one(
        "xtd.ai.run", ondelete="set null", index=True, readonly=True
    )
    user_id = fields.Many2one(
        "res.users", ondelete="set null", index=True, readonly=True
    )
    company_id = fields.Many2one("res.company", ondelete="set null", readonly=True)
    event = fields.Selection(
        [
            ("tool_call", "Tool call"),
            ("auth_failed", "Authentication failed"),
            ("confirm", "Confirmation"),
            ("cancel", "Cancellation"),
            ("undo", "Undo"),
            ("guard_blocked", "Guard blocked"),
            ("attachment_read", "Attachment read"),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    tool_name = fields.Char(readonly=True)
    arguments = fields.Json(readonly=True)
    outcome = fields.Selection(
        [
            ("ok", "OK"),
            ("error", "Error"),
            ("pending", "Pending"),
            ("denied", "Denied"),
            ("handoff", "Handed to the user"),
        ],
        required=True,
        readonly=True,
    )
    error_code = fields.Char(readonly=True)
    record_refs = fields.Json(readonly=True)
    duration_ms = fields.Integer(readonly=True)

    # ------------------------------------------------------------------
    # Immutability: the log is written only by the gateway (see _xtd_ai_log)
    # ------------------------------------------------------------------
    def write(self, vals):  # pylint: disable=method-required-super
        # Append-only by design: write never reaches super().
        raise AccessError(self.env._("The AI audit log is immutable."))

    def unlink(self):
        # Deliberate: the audit log is append-only; only the purge cron may delete.
        # pylint: disable=no-raise-unlink
        if not self.env.context.get("_xtd_ai_audit_purge"):
            raise AccessError(self.env._("The AI audit log cannot be deleted."))
        return super().unlink()

    @api.model
    def _xtd_ai_log(self, event, outcome, **values):
        """Create one audit row. Arguments are truncated; tokens are never stored.

        sudo: nobody has create rights on this model (ACL); the gateway is the
        only writer.
        """
        vals = {"event": event, "outcome": outcome}
        for key in (
            "run_id",
            "user_id",
            "company_id",
            "tool_name",
            "error_code",
            "duration_ms",
        ):
            if values.get(key) is not None:
                vals[key] = values[key]
        if values.get("arguments") is not None:
            # Se ofusca antes de truncar: el dato no llega nunca a la tabla.
            vals["arguments"] = truncate_texts(redact_personal(values["arguments"]))
        if values.get("record_refs") is not None:
            vals["record_refs"] = truncate_texts(values["record_refs"])
        return self.sudo().create(vals)

    @api.model
    def _xtd_ai_log_auth_failed(
        self, dbname_registry, reason, user_id=None, run_id=None
    ):
        """Log an authentication failure on its own cursor (the request is rolled back).

        Never receives the token. Throttled to avoid flooding the table.
        """
        try:
            with dbname_registry.cursor() as cr:
                env = api.Environment(cr, 1, {})
                recent = env["xtd.ai.audit"].search_count(
                    [
                        ("event", "=", "auth_failed"),
                        (
                            "create_date",
                            ">=",
                            fields.Datetime.now() - timedelta(minutes=1),
                        ),
                    ]
                )
                if recent >= AUTH_FAILED_BURST:
                    _logger.warning("xtd_ai auth_failed (throttled): %s", reason)
                    return
                env["xtd.ai.audit"]._xtd_ai_log(
                    "auth_failed",
                    "denied",
                    error_code=reason,
                    user_id=user_id,
                    run_id=run_id,
                )
        except Exception:
            _logger.exception("Could not write the xtd_ai auth_failed audit row")

    @api.model
    def _xtd_ai_cron_purge(self):
        """Borra la auditoría anterior al plazo de retención, por lotes."""
        days = retention_days(
            self.env,
            "xtd_ai.audit_retention_days",
            DEFAULT_AUDIT_RETENTION_DAYS,
            MIN_AUDIT_RETENTION_DAYS,
        )
        limit = fields.Datetime.now() - timedelta(days=days)
        purge = self.sudo().with_context(_xtd_ai_audit_purge=True)
        for _batch in range(PURGE_MAX_BATCHES):
            old = purge.search([("create_date", "<", limit)], limit=PURGE_BATCH)
            old.unlink()
            if len(old) < PURGE_BATCH:
                break
