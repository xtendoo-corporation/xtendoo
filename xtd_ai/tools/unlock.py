"""Unlock per tool (ANALISIS_PERMISOS §6.5).

Inside an AI run (``xtd_ai_run`` in the context) the ORM guards deny by default.
A tool may declare in ``@xtd_ai_tool(unlocks=...)`` the concrete operations it
needs (``"sale.order.action_confirm"``, or ``"*.message_post"`` for a method of
any model). The gateway puts that list in the context (``GRANT_KEY``) ONLY while
it executes that tool after the policy authorised it (a confirmed card or an N1
action); previews and policy checks never get it.

Inside the tool body, ``unlock(record, method)`` returns ``record`` with the key
that lifts that one guard for that one record (``UNLOCK_KEY``). A guard calls
``is_unlocked(self, method)``: true only for a single record, the same operation
and id, and an operation granted to the running tool. Every other guard (other
records, other operations, the e-mail guard) stays in force.
"""

from .errors import XtdAiDraftOnlyError

GRANT_KEY = "xtd_ai_grant"
UNLOCK_KEY = "xtd_ai_unlock"


def _op(record, method):
    return f"{record._name}.{method}"


def _granted(context, record, method):
    grant = context.get(GRANT_KEY) or ()
    return _op(record, method) in grant or f"*.{method}" in grant


def unlock(record, method):
    """``record`` with the guard of ``method`` lifted for it alone.

    Raises ``XtdAiDraftOnlyError`` if the running tool did not declare the
    operation or ``record`` is not exactly one record."""
    if len(record) != 1 or not _granted(record.env.context, record, method):
        raise XtdAiDraftOnlyError(
            record.env._("Esta herramienta no puede desbloquear esta operación.")
        )
    return record.with_context(**{UNLOCK_KEY: (_op(record, method), record.id)})


def is_unlocked(record, method):
    """Whether the guard of ``method`` is lifted for ``record`` (see ``unlock``)."""
    context = record.env.context
    key = context.get(UNLOCK_KEY)
    return bool(
        len(record) == 1
        and _granted(context, record, method)
        and isinstance(key, (tuple, list))
        and len(key) == 2
        and key[0] == _op(record, method)
        and key[1] == record.id
    )
