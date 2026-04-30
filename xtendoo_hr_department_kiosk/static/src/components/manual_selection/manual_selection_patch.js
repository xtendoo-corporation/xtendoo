/** @odoo-module **/

import { KioskManualSelection } from "@hr_attendance/components/manual_selection/manual_selection";
import { patch } from "@web/core/utils/patch";

if (KioskManualSelection && KioskManualSelection.prototype) {
    patch(KioskManualSelection.prototype, {
        setup() {
            super.setup();
            
            // Forzamos el nombre del departamento en el estado inicial si tenemos el ID
            if (window.kiosk_department_id) {
                const departmentId = parseInt(window.kiosk_department_id);
                const dept = this.props.departments && this.props.departments.find(d => d.id === departmentId);
                if (dept) {
                    this.departmentName = dept.name;
                }
            }
        },

        async _fetchEmployeeData() {
            // Aseguramos que el dominio de departamento esté aplicado antes de cada carga de datos
            if (window.kiosk_department_id) {
                this.state.departmentDomain = [['department_id', '=', parseInt(window.kiosk_department_id)]];
            }
            return super._fetchEmployeeData(...arguments);
        }
    });
}
