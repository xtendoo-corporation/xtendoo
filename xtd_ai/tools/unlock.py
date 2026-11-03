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


def unlock(record, method, *more):
    """``record`` with the guard of ``method`` (and of ``more`` methods, e.g. the
    confirmation email of a validated delivery) lifted for it alone.

    Raises ``XtdAiDraftOnlyError`` if the running tool did not declare every
    operation or ``record`` is not exactly one record."""
    methods = (method, *more)
    if len(record) != 1 or not all(
        _granted(record.env.context, record, m) for m in methods
    ):
        raise XtdAiDraftOnlyError(
            record.env._("Esta herramienta no puede desbloquear esta operación.")
        )
    ops = tuple(_op(record, m) for m in methods)
    return record.with_context(
        **{UNLOCK_KEY: (ops[0] if len(ops) == 1 else ops, record.id)}
    )


def _key_ops(key):
    if not isinstance(key, (tuple, list)) or len(key) != 2:
        return ()
    ops = key[0]
    if isinstance(ops, str):
        return (ops,)
    if isinstance(ops, (tuple, list)) and all(isinstance(o, str) for o in ops):
        return tuple(ops)
    return ()


def is_unlocked(record, method):
    """Whether the guard of ``method`` is lifted for ``record`` (see ``unlock``)."""
    context = record.env.context
    key = context.get(UNLOCK_KEY)
    return bool(
        len(record) == 1
        and _granted(context, record, method)
        and _op(record, method) in _key_ops(key)
        and key[1] == record.id
    )


def unlocked_record(env, method):
    """``(model, id)`` of the one record whose ``method`` guard is lifted in
    ``env`` (for guards of models that work for another record, such as the
    outgoing mail of a document), or ``None``."""
    key = env.context.get(UNLOCK_KEY)
    for op in _key_ops(key):
        model, _sep, name = op.rpartition(".")
        if name == method and isinstance(key[1], int):
            grant = env.context.get(GRANT_KEY) or ()
            if op in grant or f"*.{method}" in grant:
                return model, key[1]
    return None
