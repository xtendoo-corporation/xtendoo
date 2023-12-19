from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_open_label_layout(self):
        # flake8: noqa: E501
        if not self.env['ir.config_parameter'].sudo().get_param('garazd_product_label.replace_standard_wizard'):
            return super(ProductTemplate, self).action_open_label_layout()
        action = self.env['ir.actions.act_window']._for_xml_id('garazd_product_label.action_print_label_from_template')
        action['context'] = {'default_product_ids': self.ids}
        return action
