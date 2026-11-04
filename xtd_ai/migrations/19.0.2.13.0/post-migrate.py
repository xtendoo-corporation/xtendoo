from odoo import SUPERUSER_ID, api

from odoo.addons.xtd_ai.models.xtd_ai_policy import DEFAULT_DISCOUNT_THRESHOLD


def migrate(cr, version):
    """Política del agente (H2 y umbral a 0).

    - Fuera el límite de compra (``purchase_confirm_limit``): solo añadía un aviso
      a la tarjeta y no encaja con empresas de productos caros. Se borran la
      columna de la compañía y el parámetro (cargado con ``noupdate``).
    - El umbral de descuento vacío (o 0, que antes también significaba «usa el
      parámetro») pasa a guardar el valor que de hecho se aplicaba, para que 0
      quede libre como valor real («cualquier descuento pide tarjeta»).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        "ALTER TABLE res_company DROP COLUMN IF EXISTS xtd_ai_purchase_confirm_limit"
    )
    params = env["ir.config_parameter"]
    params.search([("key", "=", "xtd_ai.policy.purchase_confirm_limit")]).unlink()
    env["ir.model.data"].search(
        [
            ("module", "=", "xtd_ai"),
            ("name", "=", "param_policy_purchase_confirm_limit"),
        ]
    ).unlink()
    try:
        threshold = float(
            params.get_param("xtd_ai.policy.discount_threshold")
            or DEFAULT_DISCOUNT_THRESHOLD
        )
    except ValueError:
        threshold = DEFAULT_DISCOUNT_THRESHOLD
    if threshold < 0:
        threshold = DEFAULT_DISCOUNT_THRESHOLD
    cr.execute(
        """
        UPDATE res_company SET xtd_ai_discount_threshold = %s
         WHERE xtd_ai_discount_threshold IS NULL OR xtd_ai_discount_threshold = 0
        """,
        [threshold],
    )
