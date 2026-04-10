# -*- coding: utf-8 -*-
# Creado por Xtendoo Software S.L.U.
from . import models


def _post_init_cleanup(env):
    """Limpia vistas huérfanas del snippet tras instalar o actualizar el módulo."""
    env['ir.ui.view']._cleanup_video_overlay_orphan_views()
