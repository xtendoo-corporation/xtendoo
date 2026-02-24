# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    demand_factor_pct = fields.Float(
        string="Factor de demanda (%)",
        default=0.0,
        help="Porcentaje de ajuste aplicado sobre la demanda histórica.\n"
        "Ejemplo: 10.0 significa que la demanda sugerida será\n"
        "demanda_real × (1 + 10/100) = demanda_real × 1.10.\n"
        "Útil para añadir un margen de seguridad estacional.",
    )
