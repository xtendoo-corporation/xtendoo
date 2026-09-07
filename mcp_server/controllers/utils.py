import logging
import re
from typing import Dict, List, Optional, Union

import odoo
from odoo import _, modules
from odoo.api import Environment
from odoo.http import request
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)

# The three GLOBAL switches (is_mcp_enabled / is_oauth_enabled /
# get_allowed_origins) are served from an @ormcache on ``mcp.enabled.model``
# (see mcp_enabled_models.py), exactly like the per-model gates. The cache is
# per-database-registry and invalidated cross-worker by ``registry.clear_cache``
# on any config change (config write + DB signaling), so flipping the master
# kill-switch off, disabling OAuth, or tightening the Origin allowlist
# propagates to every worker on the next request.


def clear_mcp_caches() -> None:
    """Invalidate the @ormcache backing the global MCP switches.

    ``is_mcp_enabled`` / ``is_oauth_enabled`` / ``get_allowed_origins`` (and the
    per-model gates) live in the registry's ``default`` ormcache pool. Production
    config writes flush it via ``registry.clear_cache()`` on the writing env
    (res.config.settings.set_values / mcp.enabled.model._invalidate_mcp_caches),
    which also signals the other workers. This helper does the same for a direct
    ``ir.config_parameter`` write -- or a test toggling a param outside those
    paths. It clears the bound request's registry first (the one actually serving
    this request), then every loaded registry as a fallback for a request-less
    caller (e.g. a test ``setUp``). Clearing the whole ``default`` pool mirrors
    what that write-side invalidation already does.
    """
    try:
        request.env.registry.clear_cache()
    except Exception:  # noqa: BLE001 - no bound request (e.g. test setUp)
        pass
    for registry in list(Registry.registries.values()):
        registry.clear_cache()


def sanitize_model_name(model_name: str) -> str:
    """Validate and strip a model name; raise ValueError if malformed."""
    if not model_name:
        raise ValueError("Model name cannot be empty")
    # Basic validation: only allow alphanumeric, dots, and underscores
    if not re.match(r"^[a-zA-Z0-9._]+$", model_name):
        raise ValueError(f"Invalid model name format: {model_name}")

    return model_name.strip()


def _sanitize_or_log(
    model_name: str, log_prefix: str = "Invalid model name"
) -> Optional[str]:
    """Sanitize a model name, logging and returning ``None`` if malformed.

    Centralizes the ``sanitize_model_name`` try/except the gate functions
    repeated; each caller maps ``None`` to its own denied sentinel.
    """
    try:
        return sanitize_model_name(model_name)
    except ValueError as e:
        _logger.warning("%s: %s", log_prefix, e)
        return None


def is_mcp_enabled() -> bool:
    """Whether MCP is globally enabled (``mcp_server.enabled``, default off).

    Delegates to the @ormcache-d ``mcp.enabled.model._get_mcp_enabled()``, so the
    value is served from the registry cache and invalidated cross-worker on any
    config change (``registry.clear_cache`` + DB signaling) -- the master
    kill-switch takes effect on every worker's next request, not after a TTL. A
    read error (e.g. no bound request) degrades to disabled (fail closed).
    """
    try:
        gates = request.env["mcp.enabled.model"].sudo()  # sudo: admin config read
        return gates._get_mcp_enabled()
    except Exception as e:
        _logger.error(f"Error checking if MCP is enabled: {e}")
        return False


def get_allowed_origins() -> tuple:
    """Parsed ``mcp_server.allowed_origins`` browser-Origin allowlist.

    Comma-separated Origin values (``scheme://host[:port]``), normalized to
    lowercase with trailing slashes stripped. An empty/unset parameter returns
    an empty tuple, which disables Origin validation entirely (permissive
    default -- see ``MCPDispatcher.pre_dispatch``). Served from the @ormcache-d
    ``mcp.enabled.model._get_allowed_origins()`` (cross-worker-invalidated on
    config change). A read error degrades to "no restriction" rather than
    403-ing every browser client on a transient failure -- the endpoint is
    bearer-authenticated, so Origin validation is defense in depth, not the
    authorization boundary.
    """
    try:
        gates = request.env["mcp.enabled.model"].sudo()  # sudo: admin config read
        return gates._get_allowed_origins()
    except Exception as e:
        _logger.error(f"Error reading the MCP Origin allowlist: {e}")
        return ()


def is_oauth_enabled(env: Environment) -> bool:
    """Whether the OAuth 2.1 front door is enabled (``mcp_server.enable_oauth``).

    Enabled by default -- an unset parameter counts as enabled -- so OAuth is
    available as soon as MCP itself is enabled; set the parameter to any value
    other than "True" to accept API-key auth only. Delegates to the @ormcache-d
    ``mcp.enabled.model._get_oauth_enabled()`` (cross-worker-invalidated on
    config change). A read error degrades to disabled (fail closed).
    """
    try:
        gates = env["mcp.enabled.model"].sudo()  # sudo: admin config read
        return gates._get_oauth_enabled()
    except Exception as e:
        _logger.error(f"Error checking if OAuth is enabled: {e}")
        return False


def is_model_mcp_enabled(env: Environment, model_name: str) -> bool:
    """
    Check if a specific model is MCP-enabled via
    `mcp.enabled.model.is_model_enabled()`, which is @ormcache-d (bounded and
    invalidated cross-worker on config change).
    """
    if not is_mcp_enabled():
        return False

    model_name = _sanitize_or_log(model_name)
    if model_name is None:
        return False

    try:
        mcp_models = env[
            "mcp.enabled.model"
        ].sudo()  # sudo: admin-managed MCP config, not user data
        return mcp_models.is_model_enabled(model_name)
    except Exception as e:
        _logger.error(f"Error checking if model {model_name} is MCP-enabled: {e}")
        return False


def check_model_operation_allowed(
    env: Environment, model_name: str, operation: str
) -> bool:
    """
    Check if a specific operation is allowed for an MCP-enabled model via
    `mcp.enabled.model.check_model_operation_enabled()`, which is @ormcache-d
    (bounded and invalidated cross-worker on config change).
    """
    if not is_mcp_enabled():
        return False

    model_name = _sanitize_or_log(model_name)
    if model_name is None:
        return False

    operation = str(operation).strip().lower()

    valid_operations = ["read", "create", "write", "unlink"]
    if operation not in valid_operations:
        _logger.warning(
            f"Invalid operation '{operation}' requested for model '{model_name}'"
        )
        return False

    if not is_model_mcp_enabled(env, model_name):
        return False

    try:
        mcp_models = env[
            "mcp.enabled.model"
        ].sudo()  # sudo: admin-managed MCP config, not user data
        return mcp_models.check_model_operation_enabled(model_name, operation)
    except Exception as e:
        message = (
            f"Error checking if operation {operation} "
            f"is allowed for model {model_name}: {e}"
        )
        _logger.error(message)
        return False


def check_model_method_allowed(env: Environment, model_name: str) -> bool:
    """
    Check if arbitrary public method calls (`call_model_method`) are allowed
    for a model. Returns True only when the model is MCP-enabled AND its
    per-model `allow_method_calls` opt-in flag is set (default off). The gate is
    @ormcache-d via `mcp.enabled.model.is_method_call_enabled()`.
    """
    if not is_mcp_enabled():
        return False

    model_name = _sanitize_or_log(model_name)
    if model_name is None:
        return False

    if not is_model_mcp_enabled(env, model_name):
        return False

    try:
        mcp_models = env[
            "mcp.enabled.model"
        ].sudo()  # sudo: admin-managed MCP config, not user data
        return mcp_models.is_method_call_enabled(model_name)
    except Exception as e:
        _logger.error(
            f"Error checking if method calls are allowed for model {model_name}: {e}"
        )
        return False


def get_enabled_models(env: Environment) -> List[Dict]:
    """
    Get a list of all MCP-enabled models. Each entry is a dict with "model"
    (technical name), "name" (display name) and "operations" (a dict of allowed
    read/create/write/unlink flags built from the loaded record).
    """
    if not is_mcp_enabled():
        return []

    try:
        enabled_model_records = (
            env["mcp.enabled.model"].sudo().search([("active", "=", True)])
        )

        # Batch fetch all model names to avoid N+1 queries
        model_names = enabled_model_records.mapped("model_name")
        ir_models = env["ir.model"].sudo().search([("model", "in", model_names)])

        model_name_map = {m.model: m.name for m in ir_models}

        models_info = []
        for record in enabled_model_records:
            if record.model_name in model_name_map:
                models_info.append(
                    {
                        "model": record.model_name,
                        "name": model_name_map[record.model_name],
                        # Built from the already-loaded recordset to avoid a
                        # per-model permission search by callers.
                        "operations": {
                            "read": record.allow_read,
                            "create": record.allow_create,
                            "write": record.allow_write,
                            "unlink": record.allow_unlink,
                        },
                    }
                )
            else:
                _logger.warning(f"Model {record.model_name} not found in ir.model")

        return models_info
    except Exception as e:
        _logger.error(f"Error fetching enabled models: {e}")
        return []


def get_model_allowed_operations(env: Environment, model_name: str) -> Dict[str, bool]:
    """
    Get a dict of allowed operations for a specific MCP-enabled model, keyed by
    operation name with boolean values. Returns an empty dict if the model is
    not found or not MCP-enabled.
    """
    if not is_mcp_enabled():
        return {}

    model_name = _sanitize_or_log(model_name)
    if model_name is None:
        return {}

    mcp_model_record = (
        env["mcp.enabled.model"]
        .sudo()
        .search([("model_name", "=", model_name), ("active", "=", True)], limit=1)
    )

    if not mcp_model_record:
        return {}

    return {
        "read": mcp_model_record.allow_read,
        "create": mcp_model_record.allow_create,
        "write": mcp_model_record.allow_write,
        "unlink": mcp_model_record.allow_unlink,
    }


XMLRPC_METHOD_OPERATION_MAP = {
    # Read operations
    "read": "read",
    "search": "read",
    "search_read": "read",
    "search_count": "read",
    "name_search": "read",
    "fields_get": "read",
    "export_data": "read",
    "default_get": "read",
    "name_get": "read",
    "get_metadata": "read",
    "get_formview_id": "read",
    "get_formview_action": "read",
    "read_group": "read",
    "formatted_read_group": "read",
    # Create operations
    "create": "create",
    "copy": "create",
    "name_create": "create",
    # Write operations
    "write": "write",
    "toggle_active": "write",
    "action_archive": "write",
    "action_unarchive": "write",
    "message_post": "write",
    # Unlink operations
    "unlink": "unlink",
    "action_delete": "unlink",
    # NB: destructive admin primitives (e.g. button_immediate_uninstall, which
    # UNINSTALLS a module) are deliberately NOT mapped -- an unmapped method is
    # denied by default in check_mcp_access, so the legacy XML-RPC proxy can
    # never translate one into a plain 'unlink' grant.
}


def map_method_to_operation(method: str) -> Optional[str]:
    """
    Map an XML-RPC method to its operation type (read/write/create/unlink),
    or None if the method is not mapped.
    """
    method = str(method).lower().strip()
    return XMLRPC_METHOD_OPERATION_MAP.get(method)


def check_mcp_access(env: Environment, model_name: str, method_name: str) -> bool:
    """
    Check if an XML-RPC method is allowed for a given model via MCP configuration.
    """
    if not model_name or not method_name:
        _logger.warning(
            f"MCP: Invalid model or method name: {model_name}, {method_name}"
        )
        return False

    model_name = _sanitize_or_log(model_name, "MCP")
    if model_name is None:
        return False

    method_name = str(method_name).strip()

    if not is_mcp_enabled():
        _logger.info("MCP: Access denied because MCP is globally disabled.")
        return False

    model_exists = bool(
        env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
    )
    if not model_exists:
        message = f"MCP: Model {model_name} does not exist in this Odoo instance."
        _logger.warning(message)
        return False

    if not env["mcp.enabled.model"].sudo().is_model_enabled(model_name):
        message = (
            f"MCP: Access denied for XML-RPC method '{method_name}' "
            f"on model '{model_name}'. Model not MCP enabled."
        )
        _logger.info(message)
        return False

    operation = map_method_to_operation(method_name)
    if not operation:
        message = (
            f"MCP: XML-RPC method '{method_name}' on model '{model_name}' "
            f"has no defined MCP operation mapping. Access denied by default."
        )
        _logger.warning(message)
        return False

    operation_allowed = (
        env["mcp.enabled.model"]
        .sudo()
        .check_model_operation_enabled(model_name, operation)
    )

    if not operation_allowed:
        message = (
            f"MCP: Access denied for XML-RPC method '{method_name}' "
            f"(operation '{operation}') on model '{model_name}'. "
            f"Operation not allowed by MCP."
        )
        _logger.info(message)
        return False

    # Additional security check: Don't allow methods that start
    # with underscore (private methods)
    if method_name.startswith("_"):
        _logger.warning(
            f"MCP: Attempted access to private method {method_name}. Access denied."
        )
        return False

    message = (
        f"MCP: Access granted for XML-RPC method '{method_name}'"
        f" (operation '{operation}') on model '{model_name}'."
    )
    _logger.debug(message)

    return True


def get_allowed_xmlrpc_methods() -> List[str]:
    """Get a list of all XML-RPC methods that are mapped to MCP operations."""
    return list(XMLRPC_METHOD_OPERATION_MAP.keys())


def get_mcp_server_version() -> str:
    """Return the current MCP server version from the module's manifest."""
    try:
        manifest = modules.module.get_manifest("mcp_server")
        version = manifest.get("version", "1.0.0")
        return version
    except Exception as e:
        _logger.error(f"Error retrieving MCP server version from manifest: {e}")
        return "1.0.0"  # Fallback version


def get_system_info(env: Environment) -> Dict[str, Union[str, int]]:
    """
    Get system information including Odoo version, DB name, language,
    enabled MCP models count, MCP server version, and server timezone.
    """
    db_name = env.cr.dbname
    odoo_version = odoo.release.version

    # Current user's language or system default
    lang = env.context.get("lang")
    if not lang and env.user:
        lang = env.user.lang
    if not lang:
        lang = (
            env["ir.default"].sudo().get("res.partner", "lang")
        )  # A common place for default lang
    if not lang:
        lang = env["ir.config_parameter"].sudo().get_param("base.language", "en_US")

    enabled_mcp_models_count = 0
    if is_mcp_enabled():
        enabled_mcp_models_count = (
            env["mcp.enabled.model"].sudo().search_count([("active", "=", True)])
        )

    server_timezone = env.context.get("tz")
    if not server_timezone and env.user:
        server_timezone = env.user.tz
    if not server_timezone:
        server_timezone = "UTC"

    return {
        "db_name": db_name,
        "odoo_version": odoo_version,
        "language": lang,
        "enabled_mcp_models": enabled_mcp_models_count,
        "mcp_server_version": get_mcp_server_version(),
        "server_timezone": server_timezone,
    }


# Always-safe fallback: the UTC datetime guidance never depends on user state,
# so it is served even when the personalized block cannot be built. Wrapped in a
# per-call helper (not a module-level constant) so ``_()`` translates it in the
# request's language on each call, not once at import in the server's language.
def _utc_datetime_guidance():
    return _(
        "Datetime handling:\n"
        "- All datetimes stored and returned by Odoo are in UTC.\n"
        "- Provide datetimes to tools in UTC.\n"
        "- Convert to the user's timezone only for display."
    )


def _one_line(value: str) -> str:
    """Collapse CR/LF in an interpolated value to a single space.

    User-editable fields (display name, login, company name) are injected
    verbatim into the plain-text context block that clients feed to the LLM as
    instructions. Stripping embedded newlines stops a crafted value from forging
    extra context lines (prompt injection into the caller's own session).
    """
    return str(value).replace("\r", " ").replace("\n", " ")


def build_user_context(env: Environment) -> str:
    """Build the personalized user-context block for ``initialize.instructions``.

    A compact plain-text summary (no HTML) of the calling user's identity,
    timezone and company scope, plus the fixed UTC datetime guidance. Injected by
    spec-compliant MCP clients into the model context on connect, and also
    returned verbatim by the ``get_current_context`` tool. Only ever describes
    the caller's own user -- no new data surface.

    Mirrors the defensive style of this module: on any failure it logs and falls
    back to the always-safe UTC guidance so ``initialize`` still yields useful
    instructions.
    """
    try:
        user = env.user
        timezone_line = user.tz or "UTC (user has no timezone set)"
        company = user.company_id
        lines = [
            _("You are connected to Odoo via MCP as:"),
            _(
                "- User: %(name)s (login: %(login)s)",
                name=_one_line(user.display_name),
                login=_one_line(user.login),
            ),
            _("- Timezone: %(tz)s", tz=timezone_line),
            _(
                "- Active company: %(name)s (ID: %(id)s)",
                name=_one_line(company.display_name),
                id=company.id,
            ),
        ]
        allowed_companies = user.company_ids
        if len(allowed_companies) > 1:
            names = ", ".join(
                f"{_one_line(c.display_name)} (ID: {c.id})" for c in allowed_companies
            )
            lines.append(_("- Allowed companies: %(names)s", names=names))
        lines.append("")
        lines.append(_utc_datetime_guidance())
        return "\n".join(lines)
    except Exception as e:
        _logger.error(f"Error building MCP user context: {e}")
        return _utc_datetime_guidance()
