/** @odoo-module **/

import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { patch } from "@web/core/utils/patch";

patch(KanbanRecord.prototype, {
    /**
     * Override _openRecord to intercept employee selection in hr_attendance kanban
     */
    async _openRecord() {
        // Check if this is an hr.employee record
        if (this.modelName === "hr.employee") {
            // Get the action service to check the current action
            const actionService = this.env.services.action;
            const currentAction = actionService.currentController?.action;

            // Check if the current action is the attendance kanban action
            // The attendance kanban action has "attendance" in the name or XML id
            const isAttendanceAction = currentAction?.name?.toLowerCase().includes("attendance") ||
                currentAction?.xml_id === "hr_attendance.hr_attendance_action_employee_attendance_kanban" ||
                currentAction?.res_id === "hr_attendance.hr_attendance_action_employee_attendance_kanban";

            // Also check by looking at the view element for any hr_attendance specific classes
            const element = this.element?.closest('[data-view-type="kanban"]');
            const hasAttendanceClass = element?.classList.toString().includes('o_hr_attendance') ||
                element?.classList.toString().includes('attendance');

            if (isAttendanceAction || hasAttendanceClass) {
                // Redirect to work center selection with this employee
                await actionService.doAction({
                    type: 'ir.actions.client',
                    name: 'Seleccionar Centro de Trabajo',
                    tag: 'hr_attendance_work_center_select_center',
                    params: {
                        employee_id: this.record.id,
                        employee_name: this.record.data?.name || this.record.name,
                    },
                    target: 'main',
                });
                return;
            }
        }

        // Fall back to original behavior for other models or non-attendance actions
        return super._openRecord();
    },
});



