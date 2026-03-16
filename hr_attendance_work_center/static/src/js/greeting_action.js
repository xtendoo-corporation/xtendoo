/** @odoo-module **/

import { Component } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class GreetingAction extends Component {
    static template = "hr_attendance_work_center.GreetingAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.formatDateTime = registry.category("formatters").get("datetime");
        this.formatFloatTime = registry.category("formatters").get("float_time");
    }

    get employeeData() {
        const action = this.props.action || {};
        return {
            ...(action.params || {}),
            ...action,
        };
    }

    get attendance() {
        return this.employeeData.attendance || {};
    }

    get isCheckOut() {
        return Boolean(this.attendance.check_out);
    }

    get greetingTitle() {
        return this.isCheckOut ? "Hasta luego" : "Bienvenido/a";
    }

    get actionLabel() {
        return this.isCheckOut ? "Salida registrada" : "Entrada registrada";
    }

    get actionTime() {
        const value = this.attendance.check_out || this.attendance.check_in;
        return value ? this.formatDateTime(deserializeDateTime(value)) : "";
    }

    get hoursToday() {
        return this.formatFloatTime(this.employeeData.hours_today || 0);
    }

    get overtimeToday() {
        return this.employeeData.overtime_today
            ? this.formatFloatTime(this.employeeData.overtime_today)
            : "";
    }

    get totalOvertime() {
        return this.employeeData.total_overtime
            ? this.formatFloatTime(this.employeeData.total_overtime)
            : "";
    }

    get workCenterName() {
        return (this.attendance.work_center_id && this.attendance.work_center_id[1]) || "";
    }

    get employeeAvatarUrl() {
        return this.employeeData.employee_avatar || "/web/static/img/placeholder.png";
    }

    async kioskReturn() {
        await this.actionService.doAction(
            this.employeeData.next_action || "hr_attendance_work_center.hr_attendance_work_center_action",
            { clearBreadcrumbs: true }
        );
    }
}

registry.category("actions").add("hr_attendance_greeting_message", GreetingAction);

