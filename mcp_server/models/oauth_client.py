"""OAuth 2.1 client registry for the native MCP authorization server.

Each record is a relying party (typically an MCP browser client) provisioned via
RFC 7591 dynamic client registration. The model doubles as Authlib's
``ClientMixin`` so the authorization server validates redirect URIs, grant /
response types and the (public-client) token-endpoint auth method straight off
the stored fields. These are public PKCE clients only -- no client secret is
ever issued or stored.
"""

from authlib.oauth2.rfc6749 import ClientMixin

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from ..controllers.oauth_server import (
    SUPPORTED_GRANT_TYPES,
    SUPPORTED_RESPONSE_TYPES,
    SUPPORTED_TOKEN_ENDPOINT_AUTH_METHODS,
    expand_registered_scopes,
)

# MCP browser clients are public clients: they authenticate the token endpoint
# with PKCE and only ever run the auth-code + refresh flow. Dynamically
# registered clients are pinned to this profile regardless of what they request.
# The stored defaults are the space-joined form of the single source of truth --
# the capability lists advertised by the authorization server -- so the two can
# never drift apart.
_DEFAULT_GRANT_TYPES = " ".join(SUPPORTED_GRANT_TYPES)
_DEFAULT_RESPONSE_TYPES = " ".join(SUPPORTED_RESPONSE_TYPES)
_DEFAULT_TOKEN_ENDPOINT_AUTH_METHOD = " ".join(SUPPORTED_TOKEN_ENDPOINT_AUTH_METHODS)


class OauthClient(models.Model, ClientMixin):
    _name = "mcp.oauth.client"
    _description = "OAuth Client"
    _rec_name = "client_id"
    _order = "create_date desc"

    client_id = fields.Char(
        string="Client ID",
        required=True,
        copy=False,
        help="Public identifier issued to the client at registration.",
    )
    client_name = fields.Char(
        string="Name",
        help="Human-readable name the client supplied at registration "
        "(RFC 7591 'client_name'). Shown on the consent screen and admin views; "
        "falls back to the client ID when absent.",
    )
    redirect_uris = fields.Text(
        string="Redirect URIs",
        help="Whitespace-separated allow-list of redirect URIs, matched exactly "
        "at authorize and token time.",
    )
    grant_types = fields.Char(
        string="Grant Types",
        default=_DEFAULT_GRANT_TYPES,
        help="Space-separated OAuth grant types the client may use.",
    )
    response_types = fields.Char(
        string="Response Types",
        default=_DEFAULT_RESPONSE_TYPES,
        help="Space-separated OAuth response types the client may use.",
    )
    token_endpoint_auth_method = fields.Char(
        string="Token Endpoint Auth Method",
        default=_DEFAULT_TOKEN_ENDPOINT_AUTH_METHOD,
        help="How the client authenticates at the token endpoint "
        "('none' for public PKCE clients).",
    )
    scope = fields.Char(
        string="Scope",
        help="Space-separated scopes the client is allowed to request.",
    )
    created_via = fields.Char(
        string="Created Via",
        index=True,
        help="How the client was provisioned, e.g. 'dcr' for dynamic client "
        "registration.",
    )
    active = fields.Boolean(
        default=True,
        help="Inactive clients are rejected by the authorization server.",
    )
    # Redeclared to add a DB index: create_date backs both the _order
    # ("create_date desc") and the daily GC range-query (_gc_oauth), which
    # deletes DCR clients older than the retention window.
    create_date = fields.Datetime(index=True)

    # client_id is the lookup key (query_client resolves it via search); a DB
    # uniqueness constraint (which also provides the lookup index) rules out a
    # duplicate ever masking another registration. Server-generated tokens make
    # a collision astronomically unlikely, but the guarantee is defense-in-depth.
    _unique_client_id = models.Constraint(
        "UNIQUE(client_id)",
        "OAuth client_id must be unique.",
    )

    # The three OAuth models (client / token / authorization.code) deliberately
    # carry NO ir.rule, so group_mcp_admin sees every user's credential rows
    # DB-wide. This is intentional: the ACL grants admins read-only + only hashes
    # (never raw tokens/codes) are stored, every mutation re-checks has_group here
    # before sudo(), and DB-wide read is required by admin token revocation (which
    # must list and revoke any user's outstanding tokens).
    def _ensure_mcp_admin(self):
        """Gate the ``sudo()``-backed toggle actions on real MCP-admin status.

        ``action_activate`` / ``action_deactivate`` are public methods that
        ``sudo()``-write, and ``/web/dataset/call_kw`` invokes public methods
        with no ``ir.model.access`` pre-check, so without this any authenticated
        user could toggle any client (e.g. re-enable one an admin disabled for
        incident response). Checked against the *real* user before any sudo().
        """
        if not self.env.user.has_group("mcp_server.group_mcp_admin"):
            raise AccessError(
                _("Only MCP administrators may change OAuth client status.")
            )

    def action_deactivate(self):
        """Admin action (client form header): block this client's access.

        Routed through ``sudo()`` because the admin ACL on this model is
        read-only: a delegated MCP admin must not be able to write client rows
        directly (editing an existing client's ``redirect_uris`` could hijack an
        in-flight authorization). Toggling ``active`` is the one sanctioned
        change, so it is performed with elevated rights from this vetted action.
        Deactivating cuts off every access token the client already issued
        (``ir.http._resolve_oauth_token`` rejects tokens of an inactive client).
        """
        self._ensure_mcp_admin()
        self.sudo().write({"active": False})  # sudo: sanctioned toggle; ACL read-only

    def action_activate(self):
        """Admin action (client form header): re-enable a deactivated client."""
        self._ensure_mcp_admin()
        self.sudo().write({"active": True})  # sudo: sanctioned toggle; ACL read-only

    @api.depends("client_name", "client_id")
    def _compute_display_name(self):
        for client in self:
            client.display_name = client.client_name or client.client_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _redirect_uri_list(self):
        self.ensure_one()
        return (self.redirect_uris or "").split()

    @api.model
    def _register_client(self, client_info, client_metadata):
        """Create and return a client record from RFC 7591 DCR data.

        ``client_info`` carries the server-generated ``client_id`` (public PKCE
        clients get no secret); ``client_metadata`` carries the validated,
        requested metadata. Capabilities are pinned to the public-client
        auth-code + refresh profile regardless of what was requested.
        """
        redirect_uris = client_metadata.get("redirect_uris") or []
        vals = {
            "client_id": client_info["client_id"],
            "client_name": client_metadata.get("client_name") or "",
            "redirect_uris": "\n".join(redirect_uris),
            "scope": client_metadata.get("scope") or "",
            "grant_types": _DEFAULT_GRANT_TYPES,
            "response_types": _DEFAULT_RESPONSE_TYPES,
            "token_endpoint_auth_method": _DEFAULT_TOKEN_ENDPOINT_AUTH_METHOD,
            "created_via": "dcr",
        }
        return self.create(vals)

    # ------------------------------------------------------------------
    # Authlib ClientMixin interface
    # ------------------------------------------------------------------
    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        uris = self._redirect_uri_list()
        return uris[0] if uris else None

    def get_allowed_scope(self, scope):
        # Must never return None: Authlib raises InvalidScopeError on None.
        if not scope:
            return self.scope or ""
        if not self.scope:
            return scope
        # Hierarchy-aware bound: expand the client's registered scope so a coarse
        # registration ("mcp") covers the finer scopes it subsumes (mcp:read /
        # mcp:write), then keep only the requested scopes within it. String-subset
        # matching would wrongly treat "mcp" and "mcp:read" as disjoint.
        allowed = expand_registered_scopes(self.scope)
        filtered = " ".join(s for s in scope.split() if s in allowed)
        # On a genuine no-overlap, return the client's OWN registered scope --
        # never the caller's un-narrowed request, which would hand back scopes the
        # client never registered. _save_token is the authoritative source for the
        # persisted code/token scope; this keeps Authlib's validation and the
        # token-response scope consistent with the client's registration.
        return filtered or self.scope

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self._redirect_uri_list()

    def check_client_secret(self, client_secret):
        # Public PKCE clients have no secret; secret-based authentication always
        # fails closed. Kept so the ClientMixin interface stays complete.
        return False

    def check_endpoint_auth_method(self, method, endpoint):
        if endpoint == "token":
            return method == self.token_endpoint_auth_method
        return True

    def check_response_type(self, response_type):
        return response_type in (self.response_types or "").split()

    def check_grant_type(self, grant_type):
        return grant_type in (self.grant_types or "").split()
