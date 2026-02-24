# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Reaprovisionamiento por Intervalos y Estacionalidad",
    "summary": "Extiende reglas de reaprovisionamiento con intervalos de fecha "
    "y genera orderpoints mensuales basadas en demanda histórica.",
    "version": "19.0.1.0.0",
    "author": "Xtendoo Corporation",
    "website": "https://www.xtendoo.es",
    "category": "Warehouse",
    "depends": [
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_orderpoint_views.xml",
        "views/res_config_settings_views.xml",
        "views/seasonality_wizard_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "pre_init_hook": "pre_init_hook",
}
