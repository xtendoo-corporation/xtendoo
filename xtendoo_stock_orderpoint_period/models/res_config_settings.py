# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    demand_factor_pct = fields.Float(
        related="company_id.demand_factor_pct",
        readonly=False,
        string="Factor de demanda (%)",
        help="Porcentaje de ajuste aplicado sobre la demanda histórica. "
        "demanda_sugerida = demanda_real × (1 + pct/100).",
    )
