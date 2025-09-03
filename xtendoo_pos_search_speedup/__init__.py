# -*- coding: utf-8 -*-
from . import hooks

# Exponemos las funciones de hooks a nivel del módulo
post_init_hook = hooks.post_init_hook
uninstall_hook = hooks.uninstall_hook
