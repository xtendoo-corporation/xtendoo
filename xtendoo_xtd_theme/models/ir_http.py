# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request


POS_COLOR_SCHEME_COOKIE = "pos_color_scheme"


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
        request.future_response.set_cookie(POS_COLOR_SCHEME_COOKIE, max_age=0)

    def webclient_rendering_context(self):
        context = super().webclient_rendering_context()
        # El script de cabecera de la plantilla lo necesita para decidir, antes
        # de descargar nada pesado, si hay que corregir el tema.
        context["xtd_color_preference"] = self._get_color_preference()
        return context

    @classmethod
    def _get_color_preference(cls):
        user = request.env.user if request else None
        if not user or not user._is_internal():
            return "light"
        return user.res_users_settings_id.color_scheme or "system"

    @classmethod
    def _post_dispatch(cls, response):
        # Solo las páginas HTML llevan el tema: cada RPC, imagen o fichero de
        # assets pasaba antes por aquí, leía los ajustes del usuario
        # (res_users_settings_id no está almacenado: consultas extra) y
        # añadía cabeceras Vary/Accept-CH que empeoraban la caché.
        if response.mimetype == "text/html":
            target_scheme, existing_scheme = cls._get_preferred_color_scheme()
            if target_scheme and target_scheme != existing_scheme:
                response.set_cookie("color_scheme", target_scheme)
            # El TPV decide su bundle (claro u oscuro) con su propia cookie,
            # que en Community nadie escribe: se mantiene igual que la del
            # backend para que /pos/ui respete la preferencia del usuario.
            pos_scheme = target_scheme or existing_scheme
            if (
                pos_scheme in {"light", "dark"}
                and request.httprequest.cookies.get(POS_COLOR_SCHEME_COOKIE) != pos_scheme
            ):
                response.set_cookie(POS_COLOR_SCHEME_COOKIE, pos_scheme)
            response.headers.add("Vary", "Sec-CH-Prefers-Color-Scheme")
            response.headers.add("Accept-CH", "Sec-CH-Prefers-Color-Scheme")
        return super()._post_dispatch(response)
