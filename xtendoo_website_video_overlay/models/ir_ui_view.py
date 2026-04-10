# -*- coding: utf-8 -*-
# Xtendoo Software S.L.U.

from odoo import api, models
import logging
import re

_logger = logging.getLogger(__name__)

_MODULE = 'xtendoo_website_video_overlay'
_BASE_KEY = f'{_MODULE}.s_video_overlay'
# Patrón del template copy website-specific: website.<module>.s_video_overlay_HASH
_TEMPLATE_COPY_PREFIX = f'website.{_BASE_KEY}_'
# Patrón del inherit view en snippet_custom: website.snippets.<module>.s_video_overlay_HASH
_INHERIT_VIEW_PREFIX = f'website.snippets.{_BASE_KEY}_'


def _extract_hash(key, prefix):
    """Devuelve el hash de la clave si empieza por el prefijo, o None."""
    if key and key.startswith(prefix):
        return key[len(prefix):]
    return None


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _cleanup_video_overlay_orphan_views(self):
        """
        Elimina las vistas website-específicas con hash que Odoo crea cuando
        se arrastra/edita/borra el snippet s_video_overlay en el editor.

        Limpia AMBOS tipos de vistas para evitar referencias rotas:
          - Template copies:  website.xtendoo_website_video_overlay.s_video_overlay_HASH
          - Inherit views:    website.snippets.xtendoo_website_video_overlay.s_video_overlay_HASH
        """
        orphans = self.sudo().search([
            '|',
            ('key', '=like', f'{_TEMPLATE_COPY_PREFIX}%'),
            ('key', '=like', f'{_INHERIT_VIEW_PREFIX}%'),
        ])
        if orphans:
            _logger.info(
                "Xtendoo video overlay: limpiando %d vistas huérfanas: %s",
                len(orphans),
                orphans.mapped('key'),
            )
            orphans.sudo().with_context(no_cow=True).unlink()

    def unlink(self):
        """
        Cascada bidireccional:
        - Al borrar un template copy  (website.xtendoo...s_video_overlay_HASH)
          → borra el inherit view    (website.snippets.xtendoo...s_video_overlay_HASH)
        - Al borrar un inherit view   (website.snippets.xtendoo...s_video_overlay_HASH)
          → borra el template copy   (website.xtendoo...s_video_overlay_HASH)
        """
        companion_keys = []
        for view in self:
            if not view.key:
                continue
            h = _extract_hash(view.key, _TEMPLATE_COPY_PREFIX)
            if h:
                companion_keys.append(f'{_INHERIT_VIEW_PREFIX}{h}')
                continue
            h = _extract_hash(view.key, _INHERIT_VIEW_PREFIX)
            if h:
                companion_keys.append(f'{_TEMPLATE_COPY_PREFIX}{h}')

        result = super().unlink()

        if companion_keys:
            companions = self.sudo().search([('key', 'in', companion_keys)])
            if companions:
                _logger.info(
                    "Xtendoo video overlay: cascada unlink de %d vistas compañeras: %s",
                    len(companions),
                    companions.mapped('key'),
                )
                companions.sudo().with_context(no_cow=True).unlink()

        return result
