# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools.safe_eval import safe_eval


class res_config_settings(models.TransientModel):
    """
    Overwrite to add mail routing settings
    """
    _inherit = "res.config.settings"

    notify_about_lost_messages = fields.Boolean(
        string="Lost messages notification",
        help="If checked, a notification by each lost message would be sent to chosen users",
    )
    notify_lost_user_ids = fields.Many2many(
        "res.users",
        "res_users_res_config_settings_rel_table",
        "res_users_id",
        "res_config_settings_id",
        string="Notify users",
    )
    lost_allowed_model_ids = fields.Many2many(
        "ir.model",
        "ir_model_res_config_settings_lost_models_rel_table",
        "ir_model_id",
        "res_config_settings_id",
        string="Lost messages allowed models",
    )

    @api.model
    def get_values(self):
        """
        Overwrite to add new system params
        """
        res = super(res_config_settings, self).get_values()
        Config = self.env['ir.config_parameter'].sudo()
        notify_about_lost_messages = safe_eval(Config.get_param("notify_about_lost_messages", "False"))
        notify_lost_user_ids =  safe_eval(Config.get_param("notify_lost_user_ids", "[]"))
        notify_lost_user_ids = self.env["res.users"].search([("id", "in", notify_lost_user_ids)]).ids
        lost_allowed_model_ids =  safe_eval(Config.get_param("lost_allowed_model_ids", "[]"))
        lost_allowed_model_ids = self.env["ir.model"].search([("id", "in", lost_allowed_model_ids)]).ids
        values = {
            "notify_about_lost_messages": notify_about_lost_messages,
            "notify_lost_user_ids": [(6, 0, notify_lost_user_ids)],
            "lost_allowed_model_ids": [(6, 0, lost_allowed_model_ids)],
        }
        res.update(values)
        return res

    @api.model
    def set_values(self):
        """
        Overwrite to add new system params
        """
        super(res_config_settings, self).set_values()
        Config = self.env['ir.config_parameter'].sudo()
        Config.set_param("notify_lost_user_ids", self.notify_lost_user_ids.ids)
        Config.set_param("notify_about_lost_messages", self.notify_about_lost_messages)
        Config.set_param("lost_allowed_model_ids", self.lost_allowed_model_ids.ids)
