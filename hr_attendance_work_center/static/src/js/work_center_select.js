/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class WorkCenterSelectAction extends Component {
    static template = "hr_attendance_work_center.WorkCenterSelectAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            workCenters: [],
            employeeId: this.props.action.params?.employee_id || null,
            employeeName: this.props.action.params?.employee_name || "",
            workCenterSearch: "", // <-- Añadido para búsqueda
        });

        onWillStart(async () => {
            await this.loadWorkCenters();
        });
    }

    async loadWorkCenters() {
        try {
            const workCenters = await this.orm.searchRead(
                "res.partner",
                [["is_work_center", "=", true]],
                ["id", "display_name", "city", "country_id", "avatar_128"],
                { limit: 0 }
            );
            this.state.workCenters = workCenters;
        } catch (error) {
            this.notification.add(_t("Error loading work centers"), { type: "danger" });
        }
        this.state.loading = false;
    }

    async goBack() {
        await this.actionService.doAction(
            "hr_attendance.hr_attendance_action_employee_attendance_kanban",
            { clearBreadcrumbs: true }
        );
    }

    async selectWorkCenter(workCenterId, workCenterName) {
        if (!this.state.employeeId) {
            this.notification.add(_t("Error: No employee selected"), { type: "danger" });
            return;
        }

        await this.actionService.doAction({
            type: 'ir.actions.client',
            name: 'Confirmar',
            tag: 'hr_attendance_work_center_confirm',
            params: {
                employee_id: this.state.employeeId,
                employee_name: this.state.employeeName,
                work_center_id: workCenterId,
                work_center_name: workCenterName,
            },
            target: 'main',
        });
    }

    get employeeAvatarUrl() {
        return this.state.employeeId
            ? `/web/image/hr.employee/${this.state.employeeId}/avatar_128`
            : "/web/static/img/placeholder.png";
    }

    get filteredWorkCenters() {
        const query = (this.state.workCenterSearch || "").trim().toLowerCase();
        if (!query) {
            return this.state.workCenters;
        }
        return this.state.workCenters.filter((center) => {
            const name = (center.display_name || "").toLowerCase();
            return name.includes(query);
        });
    }
}

registry.category("actions").add("hr_attendance_work_center_select_center", WorkCenterSelectAction);

