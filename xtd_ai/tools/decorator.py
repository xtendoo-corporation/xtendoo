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
):
    """Declare a method of an ``xtd.ai.toolbox`` model as an AI tool (CONTRACT §6).

    ``input_schema`` may be a dict or a callable ``f(toolbox_recordset) -> dict``
    (for schemas that depend on installed data, e.g. enums).
    ``groups``: XML ids; the tool is visible/callable if the user belongs to at
    least one of them (empty/None: any AI user).
    ``requires``: optional list of model names that must be installed.
    """
    if kind not in KINDS:
        raise ValueError(f"Tool {name}: invalid kind {kind!r}")
    if kind != "read" and not preview:
        raise ValueError(f"Tool {name}: 'preview' is mandatory for kind {kind!r}")
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
        }
        return func

    return decorator
