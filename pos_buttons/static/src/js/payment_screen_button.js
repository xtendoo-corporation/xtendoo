/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async mounted() {
        await this._super(...arguments);
        this.rpc = this.env.services.rpc;
        this.onClickPartialPayment = this.onClickPartialPayment.bind(this);
    },

    async onClickPartialPayment() {
        console.log('Partial Payment Triggered');
        console.log('Environment:', this.env);
        console.log('POS:', this.env ? this.env.pos : 'undefined');

        // Verifica que `this.env` y `this.env.pos` estén definidos
        if (!this.env || !this.env.pos) {
            console.error('Environment or POS is undefined');
            return;
        }

        const order = this.env.pos.get_order();
        if (!order) {
            console.error('No order found');
            return;
        }

        try {
            await this.rpc({
                model: 'pos.order',
                method: 'create_picking',
                args: [[order.id]],
            });
            this.showPopup('ConfirmPopup', {
                title: _t('Success'),
                body: _t('Delivery order created successfully.'),
            });
        } catch (error) {
            this.showPopup('ErrorPopup', {
                title: _t('Error'),
                body: _t('An error occurred while creating the delivery order.'),
            });
        }
    }
});
