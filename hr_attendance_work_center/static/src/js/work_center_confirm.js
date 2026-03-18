/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { session } from "@web/session";

class WorkCenterConfirm extends Component {
    static template = "hr_attendance_work_center.WorkCenterConfirm";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.floatTimeFormatter = registry.category("formatters").get("float_time");
        this.state = useState({
            loading: true,
            employee: null,
            checkedIn: false,
            hoursToday: "0:00",
            workCenterId: this.props.action.params?.work_center_id || false,
            workCenterName: this.props.action.params?.work_center_name || "",
            employeeId: this.props.action.params?.employee_id || null,
        });

        onWillStart(async () => {
            await this.loadEmployeeData();
        });
    }

    async loadEmployeeData() {
        if (!this.state.employeeId) {
            // Fallback to loading from session.uid if no employee_id provided
            const employees = await this.orm.searchRead(
                "hr.employee",
                [["user_id", "=", session.uid]],
                ["name", "attendance_state", "hours_today"]
            );
            this.state.employee = employees.length ? employees[0] : null;
        } else {
            // Load the specific employee provided
            const employees = await this.orm.searchRead(
                "hr.employee",
                [["id", "=", this.state.employeeId]],
                ["name", "attendance_state", "hours_today"]
            );
            this.state.employee = employees.length ? employees[0] : null;
        }

        this.state.checkedIn = this.state.employee?.attendance_state === "checked_in";
        this.state.hoursToday = this.state.employee
            ? this.floatTimeFormatter(this.state.employee.hours_today || 0)
            : "0:00";
        this.state.loading = false;
    }

    async goBack() {
        // Go back to employee selection kanban
        await this.actionService.doAction(
            "hr_attendance.hr_attendance_action_employee_attendance_kanban",
            { clearBreadcrumbs: true }
        );
    }

    async signInOut() {
        if (!this.state.employee || !this.state.workCenterId) {
            this.notification.add(this.errorMessage, { type: "danger" });
            return;
        }
        const location = await this.getLocation();
        const result = await this.orm.call(
            "hr.employee",
            "attendance_manual_work_center_force",
            [
                [this.state.employee.id],
                "hr_attendance.hr_attendance_action_employee_attendance_kanban",
                this.state.workCenterId,
                location,
            ]
        );
        if (result?.action) {
            await this.actionService.doAction(result.action);
            return;
        }
        if (result?.warning) {
            this.notification.add(result.warning, { type: "danger" });
        }
    }

    async getLocation() {
        if (!navigator.geolocation) {
            return [0.0, 0.0];
        }
        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                ({ coords }) => resolve([coords.latitude, coords.longitude]),
                () => resolve([0.0, 0.0]),
                { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
            );
        });
    }

    get errorMessage() {
        return _t("Error: could not find corresponding employee.");
    }

    get employeeAvatarUrl() {
        const employeeId = this.state.employee?.id;
        return employeeId
            ? `/web/image/hr.employee/${employeeId}/avatar_128`
            : "/web/static/img/placeholder.png";
    }
}

registry.category("actions").add("hr_attendance_work_center_confirm", WorkCenterConfirm);
