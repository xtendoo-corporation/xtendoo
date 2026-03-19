/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { rpc } from "@web/core/network/rpc";
import { isIosApp } from "@web/core/browser/feature_detection";

const LAST_EMPLOYEE_STORAGE_KEY = "hr_attendance_work_center.last_employee_id";

class WorkCenterAction extends Component {
    static template = "hr_attendance_work_center.WorkCenterAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.notification = useService("notification");
        this.floatTimeFormatter = registry.category("formatters").get("float_time");

        this.state = useState({
            loading: true,
            requiresEmployeeSelection: false,
            employee: null,
            employees: [],
            selectedEmployeeId: false,
            employeeSearch: "",
            enteredPin: "",
            pendingAttendance: null,
            step: "employee",
            workCenters: [],
            attendanceResult: null,
            selectedWorkCenter: null,
        });

        onWillStart(async () => {
            await this.loadBootstrap();
        });
    }

    async loadBootstrap() {
        const data = await rpc("/hr_attendance/internal/bootstrap", {});
        this.state.requiresEmployeeSelection = data.requires_employee_selection;
        this.state.workCenters = data.work_centers || [];
        this.state.employee = data.employee || null;

        if (this.state.requiresEmployeeSelection) {
            await this.loadEmployees();
            const restored = this.restoreRememberedEmployee();
            if (restored) {
                this.state.step = this.getStepAfterEmployeeSelection();
            } else {
                this.state.step = "employee";
            }
        } else {
            this.state.step = this.isCheckedIn ? "checkout" : "work_center";
        }
        this.state.loading = false;
    }

    async loadEmployees() {
        const result = await rpc("/hr_attendance/internal/employees", {});
        this.state.employees = result.records || [];
    }

    selectEmployee(employee) {
        if (!employee.has_pin) {
            this.notification.add(
                "El empleado no tiene PIN configurado.",
                { type: "danger" }
            );
            return;
        }

        this.state.employee = employee;
        this.state.selectedEmployeeId = employee.id;
        this.rememberEmployee(employee.id);
        this.state.enteredPin = "";
        this.state.pendingAttendance = null;
        this.state.step = 'pin';
    }

    async confirmPin() {
        if (!this.state.enteredPin) {
            this.notification.add(_t("Debe introducir el PIN."), { type: "danger" });
            return;
        }
        if (this.state.pendingAttendance) {
            await this.submitAttendance(this.state.pendingAttendance.workCenterId);
            return;
        }
        this.state.step = this.getAttendanceStep();
    }

    askConfirmWorkCenter(center) {
        this.state.selectedWorkCenter = center;
        this.state.step = 'confirm_work_center';
    }

    async confirmWorkCenter() {
        const center = this.state.selectedWorkCenter;
        if (!center) {
            return;
        }

        this.state.loading = true; // Evita que aparezca el warning momentáneo
        try {
            await this.registerCheckIn(center.id);
        } finally {
            this.state.loading = false;
            this.state.selectedWorkCenter = null;
        }
    }

    backToEmployees() {
        this.clearRememberedEmployee();
        this.state.employee = null;
        this.state.selectedEmployeeId = false;
        this.state.employeeSearch = "";
        this.state.enteredPin = "";
        this.state.pendingAttendance = null;
        this.state.step = "employee";
    }

    async registerCheckOut() {
        await this.submitAttendance(false);
    }

    async registerCheckIn(workCenterId) {
        if (!workCenterId) {
            this.notification.add(_t("Debe seleccionar un centro de trabajo."), { type: "danger" });
            return;
        }
        await this.submitAttendance(workCenterId);
    }

    async submitAttendance(workCenterId) {
        if (!this.state.employee?.id) {
            return;
        }

        const params = {
            employee_id: this.state.employee.id,
            pin_code: this.state.requiresEmployeeSelection ? this.state.enteredPin : false,
            work_center_id: workCenterId,
        };

        try {
            const result = await this.makeRpcWithGeolocation("/hr_attendance/internal/attendance_action", params);
            this.state.attendanceResult = result;
            this.state.pendingAttendance = null;
            if (this.state.employee) {
                this.state.employee.attendance_state = result?.attendance?.check_out ? "checked_out" : "checked_in";
                this.state.employee.work_center_name = result?.work_center_name || "";
            }
            this.state.step = "greet";
        } catch (error) {
            const errorMessage = error?.data?.message || error?.message || _t("No se pudo registrar la asistencia.");
            if (
                this.state.requiresEmployeeSelection &&
                ["Debe introducir el PIN.", "PIN incorrecto."].includes(errorMessage)
            ) {
                if (this.state.employee) {
                    this.state.employee.has_pin = true;
                }
                this.state.pendingAttendance = { workCenterId };
                this.state.enteredPin = "";
                this.state.step = "pin";
            }
            this.notification.add(errorMessage, { type: "danger" });
        }
    }

    async resetFlow() {
        this.state.attendanceResult = null;
        if (this.state.requiresEmployeeSelection) {
            if (this.state.employee) {
                this.state.enteredPin = "";
                this.state.pendingAttendance = null;
                this.state.step = this.getStepAfterEmployeeSelection();
            } else {
                this.state.step = "employee";
            }
            return;
        }
        this.state.loading = true;
        await this.loadBootstrap();
    }

    rememberEmployee(employeeId) {
        window.localStorage.setItem(LAST_EMPLOYEE_STORAGE_KEY, String(employeeId));
    }

    clearRememberedEmployee() {
        window.localStorage.removeItem(LAST_EMPLOYEE_STORAGE_KEY);
    }

    restoreRememberedEmployee() {
        const rememberedId = window.localStorage.getItem(LAST_EMPLOYEE_STORAGE_KEY);
        if (!rememberedId) {
            return false;
        }
        const employee = this.state.employees.find((item) => item.id === Number(rememberedId));
        if (!employee) {
            this.clearRememberedEmployee();
            return false;
        }
        this.state.employee = employee;
        this.state.selectedEmployeeId = employee.id;
        this.state.enteredPin = "";
        this.state.pendingAttendance = null;
        return true;
    }

    async makeRpcWithGeolocation(route, params) {
        if (!navigator.geolocation) {
            return rpc(route, { ...params });
        }
        if (!isIosApp()) {
            return new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    async ({ coords: { latitude, longitude } }) => {
                        const result = await rpc(route, { ...params, latitude, longitude });
                        resolve(result);
                    },
                    async () => {
                        const result = await rpc(route, { ...params });
                        resolve(result);
                    },
                    { enableHighAccuracy: true }
                );
            });
        }
        return rpc(route, { ...params });
    }

    get isCheckedIn() {
        return this.state.employee?.attendance_state === "checked_in";
    }

    get requiresPinForSelectedEmployee() {
        return Boolean(this.state.requiresEmployeeSelection && this.state.employee?.has_pin);
    }

    getAttendanceStep() {
        return this.isCheckedIn ? "checkout" : "work_center";
    }

    getStepAfterEmployeeSelection() {
        return this.requiresPinForSelectedEmployee ? "pin" : this.getAttendanceStep();
    }

    get hoursToday() {
        return this.floatTimeFormatter(this.state.employee?.hours_today || 0);
    }

    get workCenterName() {
        return this.state.employee?.work_center_name || "";
    }

    get noEmployeeMessage() {
        return _t(
            "Warning : Your user should be linked to an employee to use attendance. Please contact your administrator."
        );
    }

    get filteredEmployees() {
        const query = (this.state.employeeSearch || "").trim().toLowerCase();
        if (!query) {
            return this.state.employees;
        }
        return this.state.employees.filter((employee) =>
            (employee.name || "").toLowerCase().includes(query)
        );
    }

    get employeeAvatarUrl() {
        return this.state.employee?.avatar_url
            ? this.state.employee.avatar_url
            : "/web/static/img/placeholder.png";
    }
}

registry.category("actions").add("hr_attendance_work_center_action", WorkCenterAction);
