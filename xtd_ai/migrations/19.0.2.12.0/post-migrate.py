from odoo import SUPERUSER_ID, api

# Plazos antiguos (365 días) -> nuevos (RGPD art. 5.1.e). Regla: solo se actualiza
# el parámetro si falta o conserva el valor por defecto antiguo ("365"); cualquier
# otro valor lo puso el administrador a propósito y no se toca. Un administrador
# que eligió 365 expresamente es indistinguible del valor por defecto: tendrá que
# volver a fijarlo en Ajustes.
OLD_DEFAULT = "365"
NEW_DEFAULTS = {
    "xtd_ai.audit_retention_days": "180",
    "xtd_ai.conversation_retention_days": "90",
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    params = env["ir.config_parameter"]
    for key, new in NEW_DEFAULTS.items():
        current = (params.get_param(key) or "").strip()
        if current in ("", OLD_DEFAULT):
            params.set_param(key, new)
