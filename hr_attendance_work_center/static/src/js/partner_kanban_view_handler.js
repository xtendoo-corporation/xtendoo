
odoo.define('hr_attendance_work_center.partner_kanban_view_handler', function(require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'res.partner' && this.$el.parents('.o_res_partner_attendance_kanban').length) {
                                            // needed to diffentiate : check in/out kanban view of employees <-> standard employee kanban view
            var action = {
                type: 'ir.actions.client',
                name: 'Confirm',
                tag: 'hr_attendance_work_center_confirm',
                work_center_id: this.record.id,
                work_center_name: this.record.display_name,
            };
            this.do_action(action);
        } else {
            this._super.apply(this, arguments);
        }
    }
});

});
