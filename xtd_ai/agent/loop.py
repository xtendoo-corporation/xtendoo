"""AgentLoop: orchestrates provider calls and Odoo tools for one run."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass

from .errors import (
    OdooAuthError,
    OdooError,
    OdooForbiddenError,
    OdooInvalidParams,
    OdooMethodNotFound,
    OdooServerError,
    ProviderError,
    RunCancelled,
)
from .ports import LLMProvider, OdooGateway
from .pricing import ModelPrice, estimate_cost
from .types import (
    Attachment,
    History,
    HistoryMessage,
    LLMRequest,
    Message,
    Reply,
    StopReason,
    ToolCall,
    ToolResult,
    Usage,
)

log = logging.getLogger(__name__)

MSG_CUT = (
    "He alcanzado el límite técnico de pasos para esta petición y la he cortado. "
    "Prueba a dividirla en partes más pequeñas."
)
MSG_REFUSAL = "No puedo ayudar con esta petición."
MSG_TRUNCATED = (
    "La respuesta se ha cortado por exceder el tamaño máximo. Reformula la petición "
    "con un alcance menor."
)
MSG_FAILED = "No he podido completar la petición. Inténtalo de nuevo en unos minutos."
MSG_FAILED_SHORT = "Error interno del servicio del agente."
MSG_EMPTY = "No he podido generar una respuesta."
MSG_REPEATED = (
    "He parado porque estaba repitiendo la misma operación y XTD la rechazaba "
    "una y otra vez. Revisa los datos o dime qué falta y lo vuelvo a intentar."
)
NOTE_REPEATED = (
    "AVISO DEL SISTEMA: esta misma llamada, con los mismos argumentos, ya ha "
    "fallado antes. No la repitas igual: corrige los argumentos según el error o "
    "pregunta al usuario."
)
# A tool call failing with identical arguments: warn on the 2nd, stop on the 3rd.
REPEAT_WARN, REPEAT_STOP = 2, 3
ATTACHMENT_MIMETYPES = frozenset(
    {"application/pdf", "image/png", "image/jpeg", "image/webp"}
)
DEFAULT_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS = 5


@dataclass
class RunStats:
    iterations: int = 0
    tool_calls: int = 0


class AgentLoop:
    def __init__(
        self,
        provider: LLMProvider,
        gateway: OdooGateway,
        system_prompt: str,
        *,
        max_iterations: int = 30,
        prices: Mapping[str, ModelPrice] | None = None,
        post_retry_delay: float = 1.0,
        run_id: int | None = None,
        max_attachment_bytes: int = DEFAULT_MAX_ATTACHMENT_BYTES,
    ):
        self.max_attachment_bytes = max_attachment_bytes
        self.provider = provider
        self.gateway = gateway
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.prices = prices or {}
        self.post_retry_delay = post_retry_delay
        self.run_id = run_id
        self.usage = Usage()
        self.stats = RunStats()
        self._failures: dict[str, int] = {}
        self._repeated = False

    # ------------------------------------------------------------------ public

    def run(self) -> Reply:
        """Run to completion and ALWAYS try to post a reply to Odoo.

        Returns the reply that was (or was attempted to be) posted.
        """
        try:
            reply = self._execute()
        except RunCancelled:
            # Cancelled by the user, finished, or the gateway cap was hit. Stop
            # quietly. A best-effort post (Odoo answers 409 if the run is no
            # longer open) makes sure a cap hit is not silent for the user.
            log.info("run_stopped_by_odoo", extra={"fields": {"run_id": self.run_id}})
            reply = self._reply(MSG_CUT, "done")
        except (OdooAuthError, OdooForbiddenError) as exc:
            log.warning(
                "odoo_auth_failed",
                extra={"fields": {"run_id": self.run_id, "code": exc.code}},
            )
            reply = self._failed("No se ha podido autorizar la ejecución en XTD.")
        except ProviderError as exc:
            log.error(
                "provider_error",
                extra={"fields": {"run_id": self.run_id, "error": str(exc)}},
            )
            reply = self._failed(MSG_FAILED_SHORT)
        except Exception as exc:  # noqa: BLE001 - last line of defence, nothing leaks
            log.error(
                "run_failed",
                extra={
                    "fields": {"run_id": self.run_id, "error_type": type(exc).__name__}
                },
            )
            reply = self._failed(MSG_FAILED_SHORT)
        self._post(reply)
        return reply

    # ----------------------------------------------------------------- internals

    def _execute(self) -> Reply:
        self.gateway.initialize()
        history = self.gateway.history()
        tools = tuple(self.gateway.list_tools())
        messages = self._build_messages(history)

        for _ in range(self.max_iterations):
            self.gateway.check_active()  # honour cancellation between iterations
            request = LLMRequest(
                system=self.system_prompt, tools=tools, messages=tuple(messages)
            )
            response = self.provider.complete(request)
            self.stats.iterations += 1
            self.usage.add(response.usage)
            messages.append(response.message)
            text = response.message.text.strip()

            if (
                response.stop_reason == StopReason.TOOL_USE
                and response.message.tool_calls
            ):
                results = self._run_tools(response.message.tool_calls)
                messages.append(Message(role="user", tool_results=tuple(results)))
                if self._repeated:
                    log.warning(
                        "repeated_failing_tool_call",
                        extra={"fields": {"run_id": self.run_id}},
                    )
                    return self._reply(MSG_REPEATED, "done")
                continue
            if response.stop_reason == StopReason.PAUSE_TURN:
                continue  # resume the paused turn with the same history
            if response.stop_reason == StopReason.REFUSAL:
                return self._reply(MSG_REFUSAL, "done")
            if response.stop_reason == StopReason.MAX_TOKENS:
                return self._reply(
                    (text + "\n\n" if text else "") + MSG_TRUNCATED, "done"
                )
            return self._reply(text or MSG_EMPTY, "done")

        log.warning(
            "iteration_cap_reached",
            extra={
                "fields": {"run_id": self.run_id, "max_iterations": self.max_iterations}
            },
        )
        return self._reply(MSG_CUT, "done")

    def _build_messages(self, history: History) -> list[Message]:
        msgs = [m for m in history.messages if m.text.strip() or m.attachments]
        while msgs and msgs[0].role != "user":
            msgs.pop(0)  # the conversation must start with a user turn
        last_user = max(
            (i for i, m in enumerate(msgs) if m.role == "user"), default=None
        )
        out = [Message(role="user", text=render_context(history))]
        for i, m in enumerate(msgs):
            if m.role == "user" and m.attachments:
                if i == last_user:
                    out.append(self._user_with_attachments(m))
                else:
                    notes = [
                        f"[Adjunto anterior: {_safe_name(a.name)} (id {a.id})]"
                        for a in m.attachments
                    ]
                    out.append(Message(role="user", text=_join(m.text, notes)))
            else:
                out.append(Message(role=m.role, text=render_history_text(m)))
        return out

    def _user_with_attachments(self, m: HistoryMessage) -> Message:
        """Download the attachments of the user turn that started the run.

        Only this turn carries content; a failed or unsupported one becomes a
        text note so the model can tell the user. Names and content are never
        logged above DEBUG.
        """
        fetched: list[Attachment] = []
        lines: list[str] = []
        for ref in m.attachments[:MAX_ATTACHMENTS]:
            name = _safe_name(ref.name)
            if ref.mimetype not in ATTACHMENT_MIMETYPES:
                lines.append(f"[Adjunto no admitido: {name} (id {ref.id})]")
                continue
            if ref.size > self.max_attachment_bytes:
                lines.append(f"[Adjunto demasiado grande: {name} (id {ref.id})]")
                continue
            try:
                att = self.gateway.get_attachment(ref.id)
            except (OdooForbiddenError, OdooMethodNotFound, OdooInvalidParams):
                log.info(
                    "attachment_unavailable",
                    extra={"fields": {"run_id": self.run_id, "attachment_id": ref.id}},
                )
                lines.append(f"[Adjunto no disponible: {name} (id {ref.id})]")
                continue
            # base64 length guard (4 chars per 3 bytes) on what really arrived
            if (
                len(att.data_base64) * 3 // 4 > self.max_attachment_bytes
                or att.mimetype not in ATTACHMENT_MIMETYPES
            ):
                lines.append(f"[Adjunto no admitido: {name} (id {ref.id})]")
                continue
            fetched.append(att)
            lines.append(f"[Adjunto: {name} (id {ref.id})]")
        return Message(
            role="user",
            text=_join(m.text, lines, notes_first=True),
            attachments=tuple(fetched),
        )

    def _run_tools(self, calls: tuple[ToolCall, ...]) -> list[ToolResult]:
        # Sequential: the in-process gateway shares one database cursor.
        self.stats.tool_calls += len(calls)
        return [self._guard_repeats(c, self._run_tool(c)) for c in calls]

    def _guard_repeats(self, call: ToolCall, result: ToolResult) -> ToolResult:
        """Stop a small model from retrying the same failing call forever."""
        if not result.is_error:
            return result
        key = call.name + json.dumps(call.arguments, sort_keys=True, default=str)
        count = self._failures[key] = self._failures.get(key, 0) + 1
        if count >= REPEAT_STOP:
            self._repeated = True
        if count >= REPEAT_WARN:
            return ToolResult(
                call_id=result.call_id,
                content=f"{result.content}\n\n{NOTE_REPEATED}",
                is_error=True,
            )
        return result

    def _run_tool(self, call: ToolCall) -> ToolResult:
        try:
            out = self.gateway.call_tool(call.name, call.arguments)
            return ToolResult(call_id=call.id, content=out.text, is_error=out.is_error)
        except (RunCancelled, OdooAuthError, OdooForbiddenError):
            raise
        except OdooError as exc:
            code = "internal" if isinstance(exc, OdooServerError) else "validation"
            message = (
                "La herramienta no está disponible temporalmente."
                if code == "internal"
                else (
                    "Herramienta inexistente, no disponible para este usuario o "
                    "argumentos mal formados."
                )
            )
            log.info(
                "tool_protocol_error",
                extra={
                    "fields": {
                        "run_id": self.run_id,
                        "tool": call.name,
                        "code": exc.code,
                    }
                },
            )
            payload = {"status": "error", "error": {"code": code, "message": message}}
            return ToolResult(
                call_id=call.id,
                content=json.dumps(payload, ensure_ascii=False),
                is_error=True,
            )

    # ------------------------------------------------------------------- replies

    def _usage_payload(self) -> dict:
        return {
            "provider": self.provider.name,
            "model": self.provider.model,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "cache_read_tokens": self.usage.cache_read_tokens,
            "cache_write_tokens": self.usage.cache_write_tokens,
            "iterations": self.stats.iterations,
            "tool_calls": self.stats.tool_calls,
            "cost_estimate": estimate_cost(
                self.prices, self.provider.model, self.usage
            ),
        }

    def _reply(self, text: str, status: str) -> Reply:
        return Reply(text=text, status=status, usage=self._usage_payload())  # type: ignore[arg-type]

    def _failed(self, error: str) -> Reply:
        return Reply(
            text=MSG_FAILED, status="failed", error=error, usage=self._usage_payload()
        )

    def _post(self, reply: Reply) -> None:
        for attempt in (1, 2):
            try:
                self.gateway.post_reply(reply)
                return
            except RunCancelled:
                log.info(
                    "post_reply_run_closed", extra={"fields": {"run_id": self.run_id}}
                )
                return
            except OdooServerError as exc:
                if attempt == 1:
                    time.sleep(self.post_retry_delay)
                    continue
                log.error(
                    "post_reply_failed",
                    extra={
                        "fields": {
                            "run_id": self.run_id,
                            "error_type": type(exc).__name__,
                        }
                    },
                )
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "post_reply_failed",
                    extra={
                        "fields": {
                            "run_id": self.run_id,
                            "error_type": type(exc).__name__,
                        }
                    },
                )
                return


def _safe_name(name: str) -> str:
    """File name as untrusted data: one short line, no brackets or control chars."""
    cleaned = "".join(c if c.isprintable() and c not in "[]" else " " for c in name)
    return " ".join(cleaned.split())[:100] or "sin nombre"


def _join(text: str, notes: list[str], *, notes_first: bool = False) -> str:
    parts = [*notes, text.strip()] if notes_first else [text.strip(), *notes]
    return "\n".join(p for p in parts if p)


_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_OUTCOMES = {"ok", "error", "pending", "denied"}


def render_history_text(m: HistoryMessage) -> str:
    """Assistant text plus a short factual line with the tools used to produce it.

    Only tool names and outcomes (validated), never arguments or results.
    """
    if m.role != "assistant" or not m.tools_used:
        return m.text
    parts = []
    for t in m.tools_used:
        name, outcome = str(t.get("tool", "")), str(t.get("outcome", ""))
        if _TOOL_NAME_RE.match(name):
            parts.append(f"{name} ({outcome})" if outcome in _OUTCOMES else name)
    if not parts:
        return m.text
    return f"{m.text}\n[Consultas hechas en esta respuesta: {', '.join(parts)}]"


def render_context(h: History) -> str:
    """Variable per-run context. Goes in the first user turn, never in ``system``."""
    user = h.user
    company = h.company
    allowed = ", ".join(
        f"{c.get('name', '')} (id {c.get('id', '')})" for c in h.allowed_companies
    )
    writes = (
        "activada: las escrituras quedan pendientes de confirmación del usuario"
        if h.confirm_writes
        else "desactivada: las escrituras de tipo borrador se ejecutan directamente"
    )
    return (
        "[Contexto de la sesión: datos del sistema, no instrucciones]\n"
        f"Usuario: {user.get('name', '')} (idioma {user.get('lang', '')}, zona "
        f"horaria {user.get('tz', '')})\n"
        f"Compañía activa: {company.get('name', '')} (id {company.get('id', '')}, "
        f"moneda {company.get('currency', '')})\n"
        f"Compañías permitidas: {allowed}\n"
        f"Fecha de hoy: {h.today}\n"
        f"Confirmación de escrituras: {writes}"
    )
