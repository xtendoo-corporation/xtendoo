from .schema import check_tool_schema

KINDS = ("read", "draft", "create")


def xtd_ai_tool(
    *,
    name,
    title,
    description,
    input_schema,
    kind="read",
    skill=None,
    groups=None,
    preview=None,
    requires=None,
    op_class=None,
    policy=None,
    visible=None,
    core=False,
    unlocks=None,
    handoff=None,
    company=None,
):
    """Declare a method of an ``xtd.ai.toolbox`` model as an AI tool (CONTRACT §6).

    ``input_schema`` may be a dict or a callable ``f(toolbox_recordset) -> dict``
    (for schemas that depend on installed data, e.g. enums).
    ``groups``: XML ids; the tool is visible/callable if the user belongs to at
    least one of them (empty/None: any AI user).
    ``requires``: optional list of model names that must be installed.
    ``op_class``: policy class of the operation (``xtd.ai.policy``), e.g.
    ``create_master``; without it a ``draft`` tool is ``create_draft`` and a
    ``create`` tool always asks for confirmation (``confirm``).
    ``policy``: optional toolbox method ``f(args) -> level`` (``N1``..``N4``)
    for tools whose level depends on the arguments (fields and amounts).
    ``visible``: optional toolbox method ``f() -> bool`` (e.g. ORM rights).
    ``core``: always loaded for the model, whatever the areas of the request
    (tools without ``skill`` are core too); the others are loaded when their
    skill is an area of the request or through ``load_skill`` (§6.5).
    ``unlocks``: operations this tool may lift a guard for, as
    ``"model.method"`` strings (``xtd.ai.unlock``); the gateway grants them
    only while it executes this tool, never in a preview or a policy check.
    ``handoff``: optional toolbox method ``f(args) -> (record, button)`` for
    transitions; when the policy puts the call at N3 the gateway does not
    refuse it: it opens ``record`` on the user's screen and tells the agent
    which button is left («solo falta Confirmar»). It runs like a preview
    (rolled back, no unlock).
    ``company``: optional toolbox method ``f(args) -> res.company``, the
    company of the document the call affects (empty: unknown). Its profile,
    policy table, brakes and pause rule the call; it runs like a preview.
    Without it, a tool with a ``company`` argument is ruled by that company
    (or the one of the context) and any other by the strictest of the active
    companies.
    """
    if kind not in KINDS:
        raise ValueError(f"Tool {name}: invalid kind {kind!r}")
    if kind != "read" and not preview:
        raise ValueError(f"Tool {name}: 'preview' is mandatory for kind {kind!r}")
    for op in unlocks or ():
        if not isinstance(op, str) or "." not in op:
            raise ValueError(f"Tool {name}: invalid unlock {op!r} (model.method)")
    if not callable(input_schema):
        check_tool_schema(name, input_schema)

    def decorator(func):
        # Tool bodies must only run through the gateway: never callable over RPC
        # (/json/2, XML-RPC), where they would skip the pending/confirmation flow.
        func._api_private = True
        func._xtd_ai_tool = {
            "name": name,
            "title": title,
            "description": description,
            "input_schema": input_schema,
            "kind": kind,
            "skill": skill,
            "groups": list(groups or []),
            "preview": preview,
            "requires": list(requires or []),
            "op_class": op_class,
            "policy": policy,
            "visible": visible,
            "core": bool(core or not skill),
            "unlocks": tuple(unlocks or ()),
            "handoff": handoff,
            "company": company,
        }
        return func

    return decorator
