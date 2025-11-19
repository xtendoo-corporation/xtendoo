# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from . import models
from . import hooks

# Exponemos las funciones de hooks a nivel del módulo
post_init_hook = hooks.post_init_hook
uninstall_hook = hooks.uninstall_hook

