/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { session } from "@web/session";

class WorkCenterAction extends Component {
    static template = "hr_attendance_work_center.WorkCenterAction";
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
            workCenterName: "",
        });

        onWillStart(async () => {
            await this.loadEmployeeData();
        });
    }

    async loadEmployeeData() {
        const employees = await this.orm.searchRead(
            "hr.employee",
            [["user_id", "=", session.uid]],
            ["name", "attendance_state", "hours_today", "last_attendance_id"]
        );
        const employee = employees.length ? employees[0] : null;
        this.state.employee = employee;
        this.state.checkedIn = employee?.attendance_state === "checked_in";
        this.state.hoursToday = employee
            ? this.floatTimeFormatter(employee.hours_today || 0)
            : "0:00";

        if (employee?.last_attendance_id?.[0]) {
            const attendance = await this.orm.read(
                "hr.attendance",
                [employee.last_attendance_id[0]],
                ["work_center_id"]
            );
            this.state.workCenterName = attendance[0]?.work_center_id?.[1] || "";
        }
        this.state.loading = false;
    }

    async openWorkCenters() {
        await this.actionService.doAction(
            "hr_attendance_work_center.hr_partner_attendance_action_kanban",
            { additionalContext: { no_group_by: true } }
        );
    }

    async signInOut() {
        if (!this.state.employee) {
            return;
        }
        const location = await this.getLocation();
        const result = await this.orm.call(
            "hr.employee",
            "attendance_manual_work_center_force",
            [
                [this.state.employee.id],
                "hr_attendance_work_center.hr_attendance_work_center_action",
                null,
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

    get noEmployeeMessage() {
        return _t(
            "Warning : Your user should be linked to an employee to use attendance. Please contact your administrator."
        );
    }

    get employeeAvatarUrl() {
        const employeeId = this.state.employee?.id;
        return employeeId
            ? `/web/image/hr.employee/${employeeId}/avatar_128`
            : "/web/static/img/placeholder.png";
    }
}

registry.category("actions").add("hr_attendance_work_center_action", WorkCenterAction);
