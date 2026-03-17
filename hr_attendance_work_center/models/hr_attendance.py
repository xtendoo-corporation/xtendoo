# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _, fields

import pytz
from odoo import models, fields, api, exceptions, _
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    responsible_id = fields.Many2one('res.users', string='Responsable', tracking=True,)
    note = fields.Text('Note', trackking=True)


    coste_total = fields.Float('Coste total', tracking=True, store=True)
    coste = fields.Float('Coste', tracking=True,  store=True)

    # check_in_latitude = fields.Float(digits="Location", readonly=True)
    # check_in_latitude_text = fields.Char(
    #     "Check-in Latitude", compute="_compute_check_in_latitude_text"
    # )
    # check_in_longitude = fields.Float(digits="Location", readonly=True)
    # check_in_longitude_text = fields.Char(
    #     "Check-in Longitude", compute="_compute_check_in_longitude_text"
    # )
    # check_out_latitude = fields.Float(digits="Location", readonly=True)
    # check_out_latitude_text = fields.Char(
    #     "Check-out Latitude", compute="_compute_check_out_latitude_text"
    # )
    # check_out_longitude = fields.Float(digits="Location", readonly=True)
    # check_out_longitude_text = fields.Char(
    #     "Check-out Longitude", compute="_compute_check_out_longitude_text"
    # )

    work_center_id = fields.Many2one('res.partner', string="Centro de trabajo", required=True, ondelete='cascade',
                                     index=True)

    # def check_in_geolocation(self):
    #     if self.check_in_latitude_text and self.check_in_longitude_text:
    #         return {
    #             'type': 'ir.actions.act_url',
    #             'url': 'https://maps.google.com/?q=%s,%s' % (self.check_in_latitude, self.check_in_longitude),
    #             'target': 'new',
    #         }
    #     else:
    #         raise UserError(_("No existe Latitud y/o Longitud"))
    #
    # def check_out_geolocation(self):
    #     if self.check_out_latitude_text and self.check_out_latitude_text:
    #         return {
    #             'type': 'ir.actions.act_url',
    #             'url': 'https://maps.google.com/?q=%s,%s' % (self.check_out_latitude, self.check_out_longitude),
    #             'target': 'new',
    #         }
    #     else:
    #         raise UserError(_("No existe Latitud y/o Longitud"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                vals['coste'] = employee.hourly_cost
        return super().create(vals_list)

    @api.onchange('check_out')
    def _onchange_check_out(self):
        for record in self:
            record.coste_total = record.coste * record.worked_hours

    @api.model
    def get_default_employee(self):
        data = {}
        if self.env.user.employee_id:
            data['id'] = self.env.user.employee_id.id
            data['name'] = self.env.user.employee_id.name
        return data

    # def _get_raw_value_from_geolocation(self, dd):
    #     d = int(dd)
    #     m = int((dd - d) * 60)
    #     s = (dd - d - m / 60) * 3600.00
    #     z = round(s, 2)
    #     return "%sº %s' %s'" % (abs(d), abs(m), abs(z))
    #
    # def _get_latitude_raw_value(self, dd):
    #     return "%s %s" % (
    #         "N" if int(dd) >= 0 else "S",
    #         self._get_raw_value_from_geolocation(dd),
    #     )
    #
    # def _get_longitude_raw_value(self, dd):
    #     return "%s %s" % (
    #         "E" if int(dd) >= 0 else "W",
    #         self._get_raw_value_from_geolocation(dd),
    #     )
    #
    # @api.depends("check_in_latitude")
    # def _compute_check_in_latitude_text(self):
    #     for item in self:
    #         item.check_in_latitude_text = (
    #             self._get_latitude_raw_value(item.check_in_latitude)
    #             if item.check_in_latitude
    #             else False
    #         )
    #
    # @api.depends("check_in_longitude")
    # def _compute_check_in_longitude_text(self):
    #     for item in self:
    #         item.check_in_longitude_text = (
    #             self._get_longitude_raw_value(item.check_in_longitude)
    #             if item.check_in_longitude
    #             else False
    #         )
    #
    # @api.depends("check_out_latitude")
    # def _compute_check_out_latitude_text(self):
    #     for item in self:
    #         item.check_out_latitude_text = (
    #             self._get_latitude_raw_value(item.check_out_latitude)
    #             if item.check_out_latitude
    #             else False
    #         )
    #
    # @api.depends("check_out_longitude")
    # def _compute_check_out_longitude_text(self):
    #     for item in self:
    #         item.check_out_longitude_text = (
    #             self._get_longitude_raw_value(item.check_out_longitude)
    #             if item.check_out_longitude
    #             else False
    #         )
