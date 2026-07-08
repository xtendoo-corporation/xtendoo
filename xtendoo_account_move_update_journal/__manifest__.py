# Copyright 2026 Xtendoo Software SLU
# License OPL-1 or later (https://www.odoo.com/documentation/19.0/legal/licenses.html#odoo-apps).

{
    "name": "Xtendoo - Editar Diario en Asientos Contables",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Xtendoo Software SLU",
    "website": "https://xtendoo.es",
    "license": "OPL-1",
    "summary": (
        "Permite reasignar el diario de asientos en borrador "
        "a usuarios autorizados"
    ),
    "description": """
Permite cambiar el diario de un asiento contable que ya fue contabilizado en el pasado
y posteriormente devuelto a borrador, siempre de forma controlada y solo para
usuarios expresamente autorizados.

Incluye:
- Grupo de seguridad específico para editores de diario.
- Ajuste quirúrgico sobre account.move para permitir el cambio de journal_id sin
  desactivar otras validaciones contables estándar.
- Auditoría en el chatter del asiento con usuario, diario anterior, diario nuevo y
  fecha/hora del cambio.

Riesgos y limitaciones:
- Este módulo debe usarse solo en asientos sin implicaciones fiscales críticas.
- No debe utilizarse para asientos protegidos por secuencia legal bloqueada,
  hash de integridad, SII, Veri*Factu o mecanismos equivalentes de inalterabilidad.
- El módulo bloquea explícitamente el cambio cuando detecta integridad fiscal
  protegida, pero la decisión funcional de habilitar este permiso sigue siendo
  responsabilidad de la administración.
""",
    "depends": ["account"],
    "data": [
        "security/security.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
