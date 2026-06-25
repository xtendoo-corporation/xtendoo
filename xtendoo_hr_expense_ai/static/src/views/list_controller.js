/** @odoo-module **/

import { ExpenseListController } from "@hr_expense/views/list";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ExpenseListController.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
    },
    async onClickImportAI() {
        await this.actionService.doAction("xtendoo_hr_expense_ai.action_hr_expense_ai_wizard", {
            onClose: async () => {
                await this.model.root.load();
                this.render(true);
            }
        });
    }
});
