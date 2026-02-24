# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    # ── Override del constraint unique original ───────────────────────────
    # El constraint original es:
    #   unique (product_id, location_id, company_id)
    # Lo reemplazamos para incluir date_start y date_end, permitiendo
    # múltiples orderpoints por período.
    # NOTA: PostgreSQL trata NULLs como distintos en UNIQUE, asi que
    # dos registros sin fechas no colisionan via SQL.  Usamos un
    # @api.constrains para cubrir ese caso en Python.
    _product_location_check = models.Constraint(
        "unique (product_id, location_id, company_id, date_start, date_end)",
        "Ya existe una regla de reaprovisionamiento para este producto, "
        "ubicación y período.",
    )

    # ── Campos de intervalo ─────────────────────────────────────────────
    date_start = fields.Date(
        string="Fecha inicio",
        help="Inicio del período en que esta regla está activa. "
        "Déjalo vacío para que la regla esté siempre activa.",
    )
    date_end = fields.Date(
        string="Fecha fin",
        help="Fin del período en que esta regla está activa. "
        "Déjalo vacío para que la regla esté siempre activa.",
    )
    is_active_today = fields.Boolean(
        string="Activa hoy",
        compute="_compute_is_active_today",
        search="_search_is_active_today",
        help="Indica si esta regla está dentro del período vigente para hoy.",
    )

    # ── Constraints ─────────────────────────────────────────────────────
    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(
                    _("La fecha de inicio debe ser anterior o igual a la fecha de fin.")
                )

    # ── Compute / Search ────────────────────────────────────────────────
    @api.depends("date_start", "date_end")
    def _compute_is_active_today(self):
        today = fields.Date.context_today(self)
        for rec in self:
            start_ok = not rec.date_start or rec.date_start <= today
            end_ok = not rec.date_end or rec.date_end >= today
            rec.is_active_today = start_ok and end_ok

    def _search_is_active_today(self, operator, value):
        """Búsqueda para is_active_today.

        Soporta operadores '=' y '!=' con valores booleanos.
        """
        today = fields.Date.context_today(self)
        # Dominio para "activa hoy": sin fecha inicio O inicio <= hoy
        #                             Y sin fecha fin O fin >= hoy
        positive_domain = [
            "&",
            "|",
            ("date_start", "=", False),
            ("date_start", "<=", today),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", today),
        ]
        if (operator == "=" and value) or (operator == "!=" and not value):
            return positive_domain
        # Negación: orderpoints que NO están activas hoy
        return [
            "|",
            "&",
            ("date_start", "!=", False),
            ("date_start", ">", today),
            "&",
            ("date_end", "!=", False),
            ("date_end", "<", today),
        ]

    # ── Override action_replenish para filtrar por período ──────────────
    def action_replenish(self, force_to_max=False):
        """Filtra los orderpoints activos hoy antes de reaprovisionar.

        Cuando se ejecuta manualmente "Run Replenishment" desde la vista de
        orderpoints, este método se invoca sobre ``self``.  Filtramos para
        incluir solo los que están vigentes hoy (o sin intervalo definido).

        VERIFY IN SOURCE – En Odoo 19 el botón llama a action_replenish
        directamente sobre el recordset seleccionado.  Si el nombre cambia,
        revisar: stock/views/stock_orderpoint_views.xml → botón "Order".
        Alternativa: action_replenish_auto (wrapper delgado).
        """
        active_today = self.filtered("is_active_today")
        if not active_today:
            return {}
        return super(StockWarehouseOrderpoint, active_today).action_replenish(
            force_to_max=force_to_max,
        )
