# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DemoAccessRight(models.Model):
    """
     This will create an example model to show how the security rules work.
     You can easily see the difference by looking under Settings > Users & Companies > Groups
     or by creating two users and giving one user the 'User' rights and the other one the 'Manager' rights.
     Also look at 'security/ir.model.access.csv' where you can see the manager has full rights while the user can only
     view the records.
    """
    _name = 'demo.access.right'

    name = fields.Char(string='Name', required=True)
