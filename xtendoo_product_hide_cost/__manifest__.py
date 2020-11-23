#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################
#
# Difusión Visual Interactivo S.L.
# Copyright (C) Difusión Visual Interactivo S.L.
# all rights reserved
# http://difusionvisual.com
# contacto@difusionvisual.com
#
# Xtendoo-Corporation
# https://xtendoo.es
#
###############################################
{
    "name": "Xtendoo Product Hide Cost",
    "summary": """
        This module hide product cost and sale""",
    # 'description': put the module description in README.rst
    "author": " Xtendoo-DDL, Difusión Visual Interactivo S.L.",
    "website": "https://xtendo.es",
    "category": "Extra Rights",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["base", "product",],
    "data": ["views/product_hide_cost.xml", "security/security.xml",],
}
