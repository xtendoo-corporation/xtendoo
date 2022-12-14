odoo.define('hr_attendance_work_center.my_attendances', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var field_utils = require('web.field_utils');

const session = require('web.session');

var WorkCenter = AbstractAction.extend({
    contentTemplate: 'HrAttendanceWorkCenter',
    events: {
        "click .o_hr_attendance_button_work_center": function() {
            this.do_action('hr_attendance_work_center.hr_partner_attendance_action_kanban', {
                additional_context: {'no_group_by': true},
            });
        },
        "click .o_hr_attendance_sign_in_out_icon": _.debounce(function() {
            this.update_attendance();
        }, 200, true),
       },


    willStart: function () {
        var self = this;
        var def = this._rpc({
                 model: 'hr.employee',
                method: 'search_read',
                args: [[['user_id', '=', this.getSession().uid]], ['attendance_state', 'name', 'hours_today']],
                context: session.user_context,
            })
            .then(function (res) {
                self.employee = res.length && res[0];
                if (res.length) {
                    self.hours_today = field_utils.format.float_time(self.employee.hours_today);
                    self.attendance_state = field_utils.format.float_time(self.employee.hours_today);
                }
            });

        return Promise.all([def, this._super.apply(this, arguments)]);
    },

    update_attendance: function () {
        var self = this;
        this._rpc({
                model: 'hr.employee',
                method: 'attendance_manual_work_center',
                args: [[self.employee.id], 'hr_attendance_work_center.hr_attendance_work_center_action'],
                context: session.user_context,
            })
            .then(function(result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.displayNotification({ title: result.warning, type: 'danger' });
                }
            });
    },
});

core.action_registry.add('hr_attendance_work_center_action', WorkCenter);

return WorkCenter;

});
