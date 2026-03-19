/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import kioskAppModule from "@hr_attendance/public_kiosk/public_kiosk_app";

const { kioskAttendanceApp } = kioskAppModule;

patch(kioskAttendanceApp.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.workCenters = [];
        this.state.workCenterSearch = "";
        this.state.pendingEmployee = null;
        this.state.pendingPin = false;
    },

    switchDisplay(screen) {
        const displays = ["main", "greet", "manual", "pin", "settings", "work_center"];
        this.state.active_display = displays.includes(screen) ? screen : "main";
    },

    async fetchWorkCenters() {
        const result = await rpc("/hr_attendance/work_centers", { token: this.props.token });
        this.state.workCenters = result?.records || [];
    },

    async openWorkCenterScreen(employeeData, pinCode = false) {
        this.state.pendingEmployee = employeeData;
        this.state.pendingPin = pinCode;
        this.state.workCenterSearch = "";
        if (!this.state.workCenters.length) {
            await this.fetchWorkCenters();
        }
        this.switchDisplay("work_center");
    },

    get filteredWorkCenters() {
        const query = (this.state.workCenterSearch || "").trim().toLowerCase();
        if (!query) {
            return this.state.workCenters;
        }
        return this.state.workCenters.filter((center) => {
            const name = (center.display_name || "").toLowerCase();
            const city = (center.city || "").toLowerCase();
            return name.includes(query) || city.includes(query);
        });
    },

    async completeCheckInWithWorkCenter(workCenterId) {
        const employee = this.state.pendingEmployee;
        if (!employee?.employee_id) {
            this.displayNotification(_t("No employee selected."));
            return;
        }
        const result = await this.makeRpcWithGeolocation("/hr_attendance/manual_selection_work_center", {
            token: this.props.token,
            employee_id: employee.employee_id,
            work_center_id: workCenterId,
            pin_code: this.state.pendingPin,
        });
        if (result?.attendance) {
            this.employeeData = result;
            this.switchDisplay("greet");
            return;
        }
        this.displayNotification(_t("Could not register attendance."));
    },

    backToEmployeeSelection() {
        this.switchDisplay("manual");
    },

    async onManualSelection(employeeId, enteredPin) {
        const result = await this.makeRpcWithGeolocation("/hr_attendance/manual_selection", {
            token: this.props.token,
            employee_id: employeeId,
            pin_code: enteredPin,
        });

        if (result?.needs_work_center) {
            await this.openWorkCenterScreen(result, enteredPin);
            return;
        }

        if (result?.attendance) {
            this.employeeData = result;
            this.switchDisplay("greet");
            return;
        }

        if (enteredPin) {
            this.displayNotification(_t("Wrong Pin"));
        }
    },

    async onBarcodeScanned(barcode) {
        if (this.lockScanner || this.state.active_display !== "main") {
            return;
        }
        this.lockScanner = true;
        this.ui.block();

        try {
            const result = await rpc("/hr_attendance/attendance_barcode_scanned", {
                barcode,
                token: this.props.token,
            });

            if (result?.needs_work_center) {
                await this.openWorkCenterScreen(result, false);
            } else if (result?.attendance) {
                this.employeeData = result;
                this.switchDisplay("greet");
            } else {
                this.displayNotification(_t("No employee corresponding to Badge ID '%(barcode)s.'", { barcode }));
            }
        } catch (error) {
            this.displayNotification(error?.data?.message || _t("Unexpected error"));
        } finally {
            this.lockScanner = false;
            this.ui.unblock();
        }
    },
});

