# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.fields import Domain
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

    def _get_overlapping_domain(self):
        """Dominio de las reglas automáticas que se solapan con ésta.

        Una fecha vacía significa "sin límite" por ese lado, igual que en
        ``is_active_today``.  Dos reglas solapan si ninguna termina antes de
        que empiece la otra.
        """
        self.ensure_one()
        return self._overlap_domain(
            self.product_id.id,
            self.location_id.id,
            self.company_id.id,
            self.date_start,
            self.date_end,
            exclude_ids=self.ids,
        )

    @api.model
    def _overlap_domain(
        self, product_id, location_id, company_id, date_start, date_end, exclude_ids=()
    ):
        domain = [
            ("product_id", "=", product_id),
            ("location_id", "=", location_id),
            ("company_id", "=", company_id),
            ("trigger", "=", "auto"),
        ]
        if exclude_ids:
            domain.append(("id", "not in", list(exclude_ids)))
        if date_end:
            domain = Domain.AND(
                [
                    domain,
                    Domain("date_start", "=", False)
                    | Domain("date_start", "<=", date_end),
                ]
            )
        if date_start:
            domain = Domain.AND(
                [
                    domain,
                    Domain("date_end", "=", False)
                    | Domain("date_end", ">=", date_start),
                ]
            )
        return Domain(domain)

    @api.constrains(
        "date_start",
        "date_end",
        "product_id",
        "location_id",
        "company_id",
        "trigger",
        "active",
    )
    def _check_no_overlapping_rules(self):
        """Evita dos reglas automáticas vigentes a la vez para el mismo
        producto y ubicación: el scheduler procesaría ambas y pediría el
        doble.  Las reglas manuales (informe de reposición) no cuentan, ya
        que solo ordenan cuando el usuario pulsa el botón.
        """
        for rec in self.filtered(lambda r: r.trigger == "auto" and r.active):
            other = self.with_context(active_test=True).search(
                rec._get_overlapping_domain(), limit=1
            )
            if other:
                raise ValidationError(
                    _(
                        "La regla de %(product)s en %(location)s se solapa con "
                        "%(other)s (%(start)s – %(end)s).  Ajusta las fechas: "
                        "solo puede haber una regla automática vigente por "
                        "producto y ubicación.",
                        product=rec.product_id.display_name,
                        location=rec.location_id.display_name,
                        other=other.display_name,
                        start=other.date_start or _("sin inicio"),
                        end=other.date_end or _("sin fin"),
                    )
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

        Odoo 19 normaliza ``('campo', '=', True)`` a ``('campo', 'in', [True])``
        (y ``'!='`` a ``'not in'``), así que hay que admitir ambas formas.
        """
        if operator not in ("=", "!=", "in", "not in"):
            raise NotImplementedError(
                _("Operador no soportado para 'Activa hoy': %s", operator)
            )
        # con 'in'/'not in' Odoo pasa un OrderedSet; con '='/'!=' un booleano
        raw = value if operator in ("in", "not in") else [value]
        values = {bool(v) for v in raw}
        if operator in ("=", "in"):
            wants_active = True in values
            matches_all = values == {True, False}
        else:
            wants_active = True not in values
            matches_all = False
        if matches_all:
            return [(1, "=", 1)]
        if not values:
            return [(0, "=", 1)] if operator in ("=", "in") else [(1, "=", 1)]

        today = fields.Date.context_today(self)
        if wants_active:
            # sin fecha inicio O inicio <= hoy  Y  sin fecha fin O fin >= hoy
            return [
                "&",
                "|",
                ("date_start", "=", False),
                ("date_start", "<=", today),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", today),
            ]
        # Negación: aún no ha empezado O ya ha terminado
        return [
            "|",
            "&",
            ("date_start", "!=", False),
            ("date_start", ">", today),
            "&",
            ("date_end", "!=", False),
            ("date_end", "<", today),
        ]

    # ── Reposición: las reglas fuera de período no ordenan nada ───────────
    @api.depends("date_start", "date_end")
    def _compute_qty_to_order_computed(self):
        """La cantidad a pedir de una regla fuera de período es 0.

        Sin esto, el informe de reposición estándar mostraría "a pedir" para
        reglas caducadas o futuras, aunque el cron y el botón las ignoren.
        ``is_active_today`` depende del día, por lo que este cálculo se
        refresca cada vez que Odoo recalcula las cantidades (apertura del
        informe de reposición y scheduler).
        """
        super()._compute_qty_to_order_computed()
        for orderpoint in self.filtered(lambda o: not o.is_active_today):
            orderpoint.qty_to_order_computed = 0.0

    def action_replenish(self, force_to_max=False):
        """Reabastece solo las reglas vigentes hoy.

        Las que están fuera de período se omiten y se avisa al usuario en
        lugar de no hacer nada en silencio.
        """
        active_today = self.filtered("is_active_today")
        skipped = self - active_today
        if not active_today:
            return self._notify_skipped_out_of_period(skipped)
        result = super(StockWarehouseOrderpoint, active_today).action_replenish(
            force_to_max=force_to_max,
        )
        if skipped and not result:
            return self._notify_skipped_out_of_period(skipped)
        return result

    def _notify_skipped_out_of_period(self, skipped):
        if not skipped:
            return {}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Reglas fuera de período"),
                "message": _(
                    "%(count)d regla(s) no se han reabastecido porque no están "
                    "vigentes hoy: %(names)s",
                    count=len(skipped),
                    names=", ".join(
                        skipped[:5].mapped(
                            lambda o: "%s (%s)" % (o.product_id.display_name, o.name)
                        )
                    )
                    + ("…" if len(skipped) > 5 else ""),
                ),
                "type": "warning",
                "sticky": False,
            },
        }
