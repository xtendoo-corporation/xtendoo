/** @odoo-module */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    setup() {
        super.setup();
        console.log("=== OrderReceipt Props ===");
        console.log("Full props:", this.props);
        console.log("Props data:", this.props.data);
        console.log("Orderlines:", this.props.data?.orderlines);

        // Mostrar cada línea individualmente
        if (this.props.data?.orderlines) {
            this.props.data.orderlines.forEach((line, index) => {
                console.log(`Line ${index}:`, line);
                console.log(`  - qty:`, line.qty);
                console.log(`  - qty_int:`, line.qty_int);
                console.log(`  - productName:`, line.productName);
            });
        }
    },
    getQtyInt(line) {
        // Convertir "1,00" a número entero
        const qtyStr = line.qty || "0";
        const qtyNum = parseFloat(qtyStr.replace(",", "."));
        return Math.floor(qtyNum);
    }
});
