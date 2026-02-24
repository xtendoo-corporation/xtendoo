# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class StockRule(models.Model):
    _inherit = "stock.rule"

    @api.model
    def _get_orderpoint_domain(self, company_id=False):
        """Extiende el dominio del scheduler para incluir solo orderpoints
        activos hoy.

        FLUJO CRON (Odoo 19):
          run_scheduler → _run_scheduler_tasks → _get_orderpoint_domain
            → search(domain) → _procure_orderpoint_confirm

        Al añadir el dominio de is_active_today aquí, tanto el CRON como
        cualquier llamada interna que use este dominio filtrarán
        correctamente.

        VERIFY IN SOURCE – Este método se define en:
          odoo/addons/stock/models/stock_rule.py  línea ~742
        Si en futuras versiones el punto de entrada cambiara, buscar
        'def _get_orderpoint_domain' o 'def _run_scheduler_tasks'.
        """
        domain = super()._get_orderpoint_domain(company_id=company_id)
        today = fields.Date.context_today(self)
        # Orderpoints sin intervalo definido (siempre activos) O dentro del rango
        domain += [
            "|",
            ("date_start", "=", False),
            ("date_start", "<=", today),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", today),
        ]
        # El dominio necesita un '&' implícito entre las dos condiciones.
        # Odoo interpreta dominios como AND por defecto entre elementos de
        # nivel superior, pero los operadores OR ya agrupan sus operandos.
        # Resultado: trigger=auto AND product_id.active=True
        #            AND (date_start vacío O date_start<=hoy)
        #            AND (date_end vacío O date_end>=hoy)
        return domain
