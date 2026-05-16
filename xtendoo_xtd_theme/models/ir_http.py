# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def color_scheme(self):
        target_scheme, existing_scheme = self._get_preferred_color_scheme()
        if target_scheme:
            return target_scheme
        if existing_scheme in {"light", "dark"}:
            return existing_scheme
        return super().color_scheme()

    @classmethod
    def _get_preferred_color_scheme(cls):
        if not request:
            return None, None

        existing_scheme = request.httprequest.cookies.get("color_scheme")
        user = request.env.user
        if not user or not user._is_internal():
            return None, existing_scheme

        preference = getattr(user.res_users_settings_id, "color_scheme", "system")
        if preference in {"light", "dark"}:
            return preference, existing_scheme

        browser_preference = request.httprequest.headers.get(
            "Sec-CH-Prefers-Color-Scheme"
        )
        if browser_preference in {"light", "dark"}:
            return browser_preference, existing_scheme

        return None, existing_scheme

    @classmethod
    def _post_logout(cls):
        super()._post_logout()
        request.future_response.set_cookie("color_scheme", max_age=0)

    @classmethod
    def _post_dispatch(cls, response):
        target_scheme, existing_scheme = cls._get_preferred_color_scheme()
        if target_scheme and target_scheme != existing_scheme:
            response.set_cookie("color_scheme", target_scheme)
        response.headers.add("Vary", "Sec-CH-Prefers-Color-Scheme")
        response.headers.add("Accept-CH", "Sec-CH-Prefers-Color-Scheme")
        return super()._post_dispatch(response)

