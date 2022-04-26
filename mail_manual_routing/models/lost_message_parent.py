#coding: utf-8

from odoo import fields, models

class lost_message_parent(models.Model):
    """
    The special model to attach lost messages (to overcome rights and let simple users work with those)
    """
    _name = "lost.message.parent"
    _inherit = ["mail.activity.mixin", "mail.thread"]
    _description = "Lost Message Parent"

    name = fields.Char(string="Name", default="Lost Messages")
