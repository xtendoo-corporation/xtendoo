# -*- coding: utf-8 -*-
# Copyright 2016-2019 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('last', 'Last Purchase Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')],
        string='Costing Method',
        company_dependent=True,
        copy=True,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
        Average Cost (AVCO): The products are valued at weighted average cost.
        First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
        Last Purchase Price: The products are valued same as 'Standard Price' Method, But standard price defined on the product will be updated automatically with last purchase price."""
    )


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('last', 'Last Purchase Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)')],
        string='Costing Method',
        company_dependent=True,
        copy=True,
        help="""Standard Price: The products are valued at their standard cost defined on the product.
            Average Cost (AVCO): The products are valued at weighted average cost.
            First In First Out (FIFO): The products are valued supposing those that enter the company first will also leave it first.
            Last Purchase Price: The products are valued same as 'Standard Price' Method, But standard price defined on the product will updated automatically with last purchase price."""
    )
