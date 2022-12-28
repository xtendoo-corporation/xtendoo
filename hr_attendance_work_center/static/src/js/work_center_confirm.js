odoo.define('hr_attendance_work_center.work_center_confirm', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var field_utils = require('web.field_utils');
var QWeb = core.qweb;
var Model = require('web.Model');


const session = require('web.session');


var WorkCenterConfirm = AbstractAction.extend({
    events: {
        "click .o_hr_attendance_back_button": function () { this.do_action(this.next_action, {clear_breadcrumbs: true}); },
        "click .o_hr_attendance_sign_in_out_icon": _.debounce(function () {
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 60000,
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    this._success.bind(self),
                    self._getPositionError.bind(self),
                    options
                );
            }
        }, 200, true),
        'click .o_hr_attendance_pin_pad_button_0': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 0); },
        'click .o_hr_attendance_pin_pad_button_1': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 1); },
        'click .o_hr_attendance_pin_pad_button_2': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 2); },
        'click .o_hr_attendance_pin_pad_button_3': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 3); },
        'click .o_hr_attendance_pin_pad_button_4': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 4); },
        'click .o_hr_attendance_pin_pad_button_5': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 5); },
        'click .o_hr_attendance_pin_pad_button_6': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 6); },
        'click .o_hr_attendance_pin_pad_button_7': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 7); },
        'click .o_hr_attendance_pin_pad_button_8': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 8); },
        'click .o_hr_attendance_pin_pad_button_9': function() { this.$('.o_hr_attendance_PINbox').val(this.$('.o_hr_attendance_PINbox').val() + 9); },
        'click .o_hr_attendance_pin_pad_button_C': function() { this.$('.o_hr_attendance_PINbox').val(''); },
        'click .o_hr_attendance_pin_pad_button_ok': _.debounce(function() {
            var self = this;
            this.$('.o_hr_attendance_pin_pad_button_ok').attr("disabled", "disabled");
            this._rpc({
                    model: 'hr.employee',
                    method: 'attendance_manual',
                    args: [[this.employee_id], this.next_action, this.$('.o_hr_attendance_PINbox').val()],
                    context: session.user_context,
                })
                .then(function(result) {
                    if (result.action) {
                        self.do_action(result.action);
                    } else if (result.warning) {
                        self.displayNotification({ title: result.warning, type: 'danger' });
                        self.$('.o_hr_attendance_PINbox').val('');
                        setTimeout( function() { self.$('.o_hr_attendance_pin_pad_button_ok').removeAttr("disabled"); }, 500);
                    }
                });
        }, 200, true),
    },
    _success: function (pos) {
        const crd = pos.coords;
        var self = this;
        self._rpc({
                model: 'hr.employee',
                method: 'attendance_manual_work_center',
                args: [[this.employee.id], 'hr_attendance_work_center.hr_attendance_work_center_action', this.work_center_id, null, [crd.latitude, crd.longitude]],
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
   _getPositionError: function (error) {
        console.warn("ERROR(" + error.code + "): " + error.message);
        var self = this;
         self._rpc({
                model: 'hr.employee',
                method: 'attendance_manual_work_center',
                args: [[this.employee.id], 'hr_attendance_work_center.hr_attendance_work_center_action', this.work_center_id, null, [0.0, 0.0]],
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
    init: function (parent, action) {
        this._super.apply(this, arguments);
        var self = this;
        this.location = (null, null);
        this.errorCode = null;
        this.next_action = 'hr_attendance_work_center.hr_attendance_work_center_action';
        this.work_center_id = action.work_center_id.value;
        this.work_center_name = action.work_center_name.value;
        this._rpc({
                    model: 'hr.attendance',
                    method: 'get_default_employee',
                    args: [],
                }, {
                    shadow: true,
                }).then(function (data) {
                    self.employee_id = data['id'];
                    self.employee_name = data['name'];
                });
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
                }
            });

        return Promise.all([def, this._super.apply(this, arguments)]);
    },

    start: function () {
        var self = this;
        this.getSession().user_has_group('hr_attendance.group_hr_attendance_use_pin').then(function(has_group){
            self.use_pin = has_group;
            self.$el.html(QWeb.render("HrAttendanceWorkCenterConfirm", {widget: self}));
            self.start_clock();
        });
        return self._super.apply(this, arguments);
    },

    start_clock: function () {
        this.clock_start = setInterval(function() {this.$(".o_hr_attendance_clock").text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));}, 500);
        // First clock refresh before interval to avoid delay
        this.$(".o_hr_attendance_clock").show().text(new Date().toLocaleTimeString(navigator.language, {hour: '2-digit', minute:'2-digit', second:'2-digit'}));
    },

    destroy: function () {
        clearInterval(this.clock_start);
        this._super.apply(this, arguments);
    },

});

core.action_registry.add('hr_attendance_work_center_confirm', WorkCenterConfirm);

return WorkCenterConfirm;

});
