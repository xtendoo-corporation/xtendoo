# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.tools import pycompat

class Partner(models.Model):
    _inherit = ['res.partner']
    _name = "res.partner"


    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('import_file'):
            self._check_import_consistency(vals_list)
        for vals in vals_list:
            if vals.get('website'):
                vals['website'] = self._clean_website(vals['website'])
            if vals.get('parent_id'):
                vals['company_name'] = False
            if vals.get('customer'):
                vals['customer'] = False
            # compute default image in create, because computing gravatar in the onchange
            # cannot be easily performed if default images are in the way
            if not vals.get('image'):
                vals['image'] = self._get_default_image(vals.get('type'), vals.get('is_company'), vals.get('parent_id'))
            tools.image_resize_images(vals, sizes={'image': (1024, None)})
        partners = super(Partner, self).create(vals_list)

        if self.env.context.get('_partners_skip_fields_sync'):
            return partners

        for partner, vals in pycompat.izip(partners, vals_list):
            partner._fields_sync(vals)
            partner._handle_first_contact_creation()
        return partners
