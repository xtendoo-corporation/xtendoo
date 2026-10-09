import functools
import hashlib
import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

COOKIE_NAME = "xtd_hr_mp"
PAGE_SIZE = 20


@functools.lru_cache(maxsize=1)
def _assets_version():
    """Hash of the static CSS/JS: appended to their URLs so phones never keep
    serving a stale stylesheet after an update (cache busting)."""
    digest = hashlib.sha1()
    for path in ("static/src/css/portal.css", "static/src/js/portal.js"):
        with file_open(f"xtendoo_hr_attendance_mobile_portal/{path}", "rb") as handle:
            digest.update(handle.read())
    return digest.hexdigest()[:10]


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


class MobilePortal(http.Controller):
    """HTTP layer only: resolves the employee from the session cookie and
    hands over to ``hr.attendance.portal.access`` (auth) and
    ``hr.attendance.portal.punch`` (attendance logic). The employee is
    NEVER taken from request parameters."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_lang(self, company):
        """Public requests carry no user language: follow the phone's browser
        language when it is installed, else the company's one."""
        installed = [code for code, _name in request.env["res.lang"].get_installed()]
        wanted = request.best_lang
        lang = None
        if wanted:
            lang = wanted if wanted in installed else next(
                (c for c in installed if c.split("_")[0] == wanted.split("_")[0]), None
            )
        lang = lang or company.sudo().partner_id.lang
        if lang and request.env.lang != lang:
            request.update_context(lang=lang)

    def _session(self):
        token = request.httprequest.cookies.get(COOKIE_NAME)
        access = request.env["hr.attendance.portal.access"]._resolve_session(token)
        self._set_lang(access.company_id or request.env.company)
        return access

    def _render(self, template, values=None, status=200):
        values = dict(
            values or {}, csrf_token=request.csrf_token(), assets_v=_assets_version()
        )
        employee = values.get("employee")
        self._set_lang(employee.company_id if employee else request.env.company)
        response = request.render(template, values, status=status)
        return _no_store(response)

    def _unauthorized(self):
        return self._render("xtendoo_hr_attendance_mobile_portal.unauthorized", status=401)

    def _json(self, payload, status=200):
        return _no_store(request.make_json_response(payload, status=status))

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------
    @http.route("/fichaje/activar/<string:token>", type="http", auth="public",
                methods=["GET"], sitemap=False)
    def activate_page(self, token, **kw):
        # GET only shows a confirmation page: link previewers (WhatsApp,
        # mail clients...) fetch URLs and must not burn the one-time token.
        return self._render(
            "xtendoo_hr_attendance_mobile_portal.activate", {"token": token}
        )

    @http.route("/fichaje/activar", type="http", auth="public", methods=["POST"],
                sitemap=False)  # csrf enabled (default)
    def activate(self, token=None, **kw):
        Access = request.env["hr.attendance.portal.access"]
        Attempt = request.env["hr.attendance.portal.attempt"]
        ip = request.httprequest.remote_addr
        if Attempt._is_blocked(ip):
            return self._render(
                "xtendoo_hr_attendance_mobile_portal.activation_failed",
                {"blocked": True}, status=429,
            )
        user_agent = request.httprequest.user_agent
        device = f"{user_agent.platform or ''} {user_agent.browser or ''}".strip()
        access, session_token = Access._redeem(token, device_info=device)
        if not access:
            Attempt._register_failure(ip)
            return self._render(
                "xtendoo_hr_attendance_mobile_portal.activation_failed",
                {"blocked": False}, status=400,
            )
        response = _no_store(request.redirect("/fichaje", local=True))
        response.set_cookie(
            COOKIE_NAME, session_token,
            max_age=access.company_id.portal_attendance_session_days * 86400,
            path="/fichaje",
            secure=request.httprequest.is_secure,
            httponly=True,
            samesite="Lax",
        )
        _logger.info("Mobile punch portal: access %s activated", access.id)
        return response

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    @http.route("/fichaje", type="http", auth="public", methods=["GET"], sitemap=False)
    def home(self, **kw):
        access = self._session()
        if not access:
            return self._unauthorized()
        employee = access.employee_id
        Punch = request.env["hr.attendance.portal.punch"]
        return self._render(
            "xtendoo_hr_attendance_mobile_portal.home",
            {
                "employee": employee,
                "state": Punch.get_state(employee),
                "privacy_text": employee.company_id.portal_attendance_privacy_text,
            },
        )

    @http.route("/fichaje/historial", type="http", auth="public", methods=["GET"],
                sitemap=False)
    def history(self, page=1, **kw):
        access = self._session()
        if not access:
            return self._unauthorized()
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        employee = access.employee_id
        history = request.env["hr.attendance.portal.punch"].get_history(
            employee, page=page, page_size=PAGE_SIZE
        )
        return self._render(
            "xtendoo_hr_attendance_mobile_portal.history",
            {"employee": employee, "history": history},
        )

    # ------------------------------------------------------------------
    # Punch (write): CSRF-protected form POST, JSON answer
    # ------------------------------------------------------------------
    @http.route("/fichaje/marcar", type="http", auth="public", methods=["POST"],
                sitemap=False)
    def punch(self, action=None, geo_status=None, latitude=None, longitude=None,
              accuracy=None, **kw):
        access = self._session()
        if not access:
            return self._json({"ok": False, "error": "unauthorized"}, status=401)
        employee = access.employee_id
        Punch = request.env["hr.attendance.portal.punch"]
        try:
            Punch.punch(
                employee, action, geo_status, latitude, longitude, accuracy,
                ip_address=request.httprequest.remote_addr,
                browser=request.httprequest.user_agent.browser,
            )
        except UserError as exc:
            return self._json({"ok": False, "error": exc.args[0]}, status=400)
        state = Punch.get_state(employee)
        return self._json(
            {
                "ok": True,
                "checked_in": state["checked_in"],
                "last_label": state["last_label"],
                "geo": geo_status == "ok",
            }
        )

    # ------------------------------------------------------------------
    # PWA
    # ------------------------------------------------------------------
    @http.route("/fichaje/manifest.webmanifest", type="http", auth="public",
                methods=["GET"], sitemap=False)
    def manifest(self, **kw):
        base = "/xtendoo_hr_attendance_mobile_portal/static/img"
        manifest = {
            "name": request.env._("Time clock"),
            "short_name": request.env._("Time clock"),
            "start_url": "/fichaje",
            "scope": "/fichaje",
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#ffffff",
            "theme_color": "#f45700",
            "icons": [
                {"src": f"{base}/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": f"{base}/icon-512.png", "sizes": "512x512", "type": "image/png"},
                {"src": f"{base}/icon-512.png", "sizes": "512x512",
                 "type": "image/png", "purpose": "maskable"},
            ],
        }
        response = request.make_json_response(manifest)
        response.headers["Content-Type"] = "application/manifest+json"
        return response
