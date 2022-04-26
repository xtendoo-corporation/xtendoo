# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class mail_attach_wizard(models.TransientModel):
    """
    The wizard to select target object for wizard
    """
    _name = "mail.message.attach.wizard"
    _description = "Attach Message"

    @api.model
    def _selection_res_reference(self):
        """
        The method to return available for this user models which have message_post methods
        """
        Config = self.env["ir.config_parameter"].sudo()
        lost_allowed_model_ids = safe_eval(Config.get_param("lost_allowed_model_ids", "[]"))
        if not lost_allowed_model_ids:
            model_ids =  self.env["ir.model"].sudo().search([
                ("access_ids.group_id.users", "=", self.env.uid),
                ("transient", "=", False),
                ("is_mail_thread", "=", True),
            ])
        else:
            model_ids =  self.env["ir.model"].sudo().search([
                ("id", "in", lost_allowed_model_ids),
                ("access_ids.group_id.users", "=", self.env.uid),
            ])            
        return model_ids.mapped(lambda rec: (rec.model, rec.name))

    res_reference = fields.Reference(
        selection="_selection_res_reference",
        string="Parent Object",
    )
    message_ids = fields.Many2many(
        "mail.message",
        "mail_message_mail_attach_wizard_rel_table",
        "mail_message_id",
        "mail_attach_wizard_id",
        string="Messages",
    )

    def action_attach_mail_message(self):
        """
        The method to route message to a proper record

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        query = """UPDATE mail_message
                   SET is_unattached = FALSE,
                       res_id = %s,
                       model = %s,
                       record_name = %s,
                       subtype_id = %s
                   WHERE id IN %s
                """
        subtype_id = self.env.ref("mail.mt_comment").id
        self._cr.execute(query, (
            self.res_reference.id, 
            self.res_reference._name, 
            self.res_reference.display_name, 
            subtype_id,
            tuple(self.message_ids.ids),
        ))
        attchments = self.message_ids.mapped("attachment_ids")
        if attchments:
            a_query = """UPDATE ir_attachment
                         SET res_id = %s,
                             res_model = %s                        
                         WHERE id IN %s
                    """        
            self._cr.execute(a_query, (
                self.res_reference.id, 
                self.res_reference._name, 
                tuple(attchments.ids),
            ))
        self._cr.commit()  
