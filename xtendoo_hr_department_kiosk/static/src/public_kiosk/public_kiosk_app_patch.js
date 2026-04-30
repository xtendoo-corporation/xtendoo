/** @odoo-module **/

import kioskApp from "@hr_attendance/public_kiosk/public_kiosk_app";
import { patch } from "@web/core/utils/patch";

// Odoo 19 puede exportar de formas distintas dependiendo de la compilación
const cls = kioskApp?.kioskAttendanceApp || kioskApp?.default?.kioskAttendanceApp;

if (cls && cls.prototype) {
    patch(cls.prototype, {
        setup() {
            super.setup();
            if (window.kiosk_department_id) {
                this.state.active_display = 'manual';
            }
        }
    });
}
