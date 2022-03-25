# © <2012> <Israel Cruz Argil, Argil Consulting>
# © <2016> <Jarsa Sistemas, S.A. de C.V.>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class TmsExtradataType(models.Model):
    _name = "tms.extradata.type"
    _description = "Extra Data for TMS"

    name = fields.Char(required=True)
    type = fields.Selection([
        ('char', 'Text'),
        ('integer', 'Numeric'),
        ('float', 'Numeric with decimals'),
        ('date', 'Date'),
        ('datetime', 'Datetime')],
        required=True,
    )
    apply_on = fields.Selection([
        ('waybill', 'Waybill'),
        ('unit', 'Unit'), ], required=True, readonly=True
    )

    @api.model
    def default_get(self, field):
        res = super(TmsExtradataType, self).default_get(
            field)
        active_model = self.env.context['active_model']
        if active_model == 'fleet.vehicle':
            res['apply_on'] = 'unit'
        elif active_model == 'tms.waybill':
            res['apply_on'] = 'waybill'
        return res
