/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, useState, useRef, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";

class MockOrderLine {
    constructor(data, order) {
        this.data = data;
        this.order = order;
        this.id = data.id || Math.random();
        this.order_id = true;
        this.full_product_name = data.product_id[1];
        this.qty = data.qty;
        this.price = data.price_unit;
        this.discount = data.discount;
        this.price_unit = data.price_unit;
        this.price_subtotal = data.price_subtotal;
        this.price_subtotal_incl = data.price_subtotal_incl;
        this.currency = order.currency;
        this.customer_note = data.customer_note || "";
        this.customerNote = data.customer_note || ""; // Alias for xtendoo_pos_receipt
        this.product_id = {
            id: data.product_id[0],
            name: data.product_id[1],
            display_name: data.product_id[1],
            getImageUrl: () => false,
            tracking: "none",
            taxes_id: [],
            uom_id: { name: _t("Units") }
        };
        this.combo_parent_id = false;
        this.combo_line_ids = [];
        this.taxGroupLabels = false;
        this.packLotLines = [];
        
        this.currencyDisplayPrice = formatCurrency(data.price_subtotal_incl, order.currency.id);
        this.currencyDisplayPriceUnit = formatCurrency(data.price_unit, order.currency.id);
        this.displayPriceNoDiscount = data.price_unit * data.qty;
        this.displayPriceUnit = data.price_unit;
        this.displayPriceUnitNoDiscount = data.price_unit;
        this.priceIncl = data.price_subtotal_incl;
        this.priceExcl = data.price_subtotal;
        
        this.orderDisplayProductName = {
             name: data.product_id[1],
             attributeString: ""
        };
    }

    getQuantityStr() {
        const qty = this.qty;
        return {
            unitPart: Math.floor(qty).toString(),
            decimalPart: (qty % 1) > 0 ? (qty % 1).toFixed(2).split(".")[1] : "",
            decimalPoint: (qty % 1) > 0 ? "," : "",
        };
    }

    getDiscountStr() {
        return this.discount > 0 ? this.discount.toString() : "0";
    }

    isSelected() { return false; }
    getDisplayClasses() { return {}; }
    getQuantity() { return this.qty; }
    displayDiscountPolicy() { return "with_discount"; }
}

class MockOrder {
    constructor(data) {
        this.data = data;
        this.name = data.pos_reference; // Alias for xtendoo_pos_receipt
        this.company = {
             ...data.company,
             logo: data.company.logo,
             point_of_sale_use_ticket_qr_code: true,
             point_of_sale_ticket_portal_url_display_mode: 'qr_code',
             country_id: data.company.country_id || { vat_label: "VAT" },
        };
        this.config = {
            name: data.pos_reference,
            receipt_header: data.receipt_header,
            receipt_footer: data.receipt_footer,
            receiptLogoUrl: data.company.logo ? "/web/image?model=res.company&id=" + data.company.id + "&field=logo" : false,
            _base_url: window.location.origin,
            _IS_VAT: true,
            displayTrackingNumber: false,
            displayBigTrackingNumber: false,
        };
        this.currency = { 
            id: data.currency_id[0],
            symbol: data.currency_id[1],
            position: data.currency_id[2],
            decimal_places: data.currency_id[3],
            round: (val) => Math.round(val * 100) / 100,
            format: (val) => formatCurrency(val, data.currency_id[0]),
            isZero: (val) => Math.abs(val) < 0.001,
        };
        this.amount_total = data.amount_total;
        this.amount_return = data.amount_return;
        this.amount_tax = data.amount_tax;
        this.pos_reference = data.pos_reference;
        this.access_token = data.access_token;
        this.ticket_code = data.ticket_code;
        this.date_order = data.date_order;
        this.finalized = true;
        this.isSynced = true;
        
        this.lines = data.lines.map(l => new MockOrderLine(l, this));
        this.orderlines = this.lines; // Alias for xtendoo_pos_receipt
        
        this.prices = {
            taxDetails: data.tax_details
        };
        
        this.priceExcl = data.tax_details.base_amount;
        this.priceIncl = data.amount_total;
        this.currencyDisplayPriceIncl = formatCurrency(data.amount_total, this.currency.id);
        this.totalDue = data.amount_total;
        this.change = data.amount_return;
        this.showChange = data.amount_return > 0;
        this.appliedRounding = 0;

        this.payment_ids = (data.payment_ids || []).map(p => ({
            is_change: false,
            amount: p.amount,
            payment_method_id: { name: p.payment_method_id[1], is_cash_count: false },
            getAmount: () => p.amount,
            isDone: () => true,
        }));
        
        if (this.amount_return > 0) {
            this.payment_ids.push({ 
                is_change: true, 
                amount: -this.amount_return, 
                payment_method_id: { name: _t("Change"), is_cash_count: true },
                getAmount: () => -this.amount_return,
                isDone: () => true,
            });
        }
        
        this.partner_id = data.partner ? {
            ...data.partner,
            pos_contact_address: data.partner.address || "",
            parent_name: false
        } : false;
    }

    getCashierName() {
        return this.data.user_id ? this.data.user_id[1].split(" ")[0] : "";
    }
    
    getTotalDiscount() {
        return this.lines.reduce((acc, line) => acc + (line.displayPriceNoDiscount - line.price_subtotal_incl), 0);
    }
    
    formatDateOrTime(fieldName, type = 'datetime') {
        const val = this[fieldName] || this.data[fieldName];
        if (!val) return "";
        return val;
    }
}

export class PosReceiptClientAction extends Component {
    static components = { OrderReceipt };
    static template = xml`
        <div class="o_pos_receipt_client_action h-100 w-100 d-flex flex-column align-items-center justify-content-center bg-view">
             <div class="o_loader" t-if="state.loading">
                <i class="fa fa-spinner fa-spin fa-3x mb-3 text-primary"/>
                <p class="h4">Generando ticket...</p>
                <div t-if="state.message" class="mt-2 text-muted italic">
                    <t t-esc="state.message"/>
                </div>
            </div>
            
            <!-- Contenedor para renderizado (oculto en pantalla) -->
            <div t-if="state.order" t-ref="receipt" class="pos-receipt-container" style="position: absolute; left: -9999px; width: 300px; padding: 10px;">
                <div class="render-container" style="display: block !important;">
                    <OrderReceipt order="state.order" />
                </div>
            </div>
            
            <div t-if="!state.loading" class="text-center p-5 rounded shadow-sm bg-surface">
                <i class="fa fa-check-circle fa-5x text-success mb-4"/>
                <h2 class="fw-bold mb-3">Impresión del documento realizada</h2>
                <div class="d-flex gap-2 justify-content-center">
                    <button class="btn btn-primary btn-lg px-5" t-on-click="closeAction">Cerrar</button>
                    <button class="btn btn-outline-secondary btn-lg" t-on-click="reprint">Volver a Imprimir</button>
                </div>
            </div>
        </div>
    `;

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({ loading: true, order: null, message: "" });
        this.receiptRef = useRef("receipt");

        onMounted(async () => {
             const params = this.props.action.params;
             const orderId = params.order_id;
             console.log("PosReceiptClientAction (Custom Overrides) for order:", orderId);
             
             try {
                 if (orderId) {
                     this.state.message = "Cargando datos del pedido...";
                     const orderData = await this.orm.call("pos.order", "get_order_receipt_data", [orderId]);
                     
                     this.state.message = "Aplicando plantillas personalizadas...";
                     this.state.order = new MockOrder(orderData);
                     
                     await new Promise(resolve => setTimeout(resolve, 1000));
                     
                     if (this.receiptRef.el) {
                         const content = this.receiptRef.el.querySelector('.pos-receipt');
                         if (content && content.innerHTML.trim().length > 0) {
                             await this.printReceipt();
                         } else {
                             throw new Error("El ticket personalizado se ha generado vacío.");
                         }
                     }
                 }
             } catch (error) {
                 console.error("Error generating customized receipt:", error);
                 this.notification.add("Error: " + error.message, { type: "danger" });
             } finally {
                 this.state.loading = false;
             }
        });
    }

    closeAction() {
        const params = this.props.action.params;
        if (params.next_action) {
            this.actionService.doAction(params.next_action);
        } else {
            this.actionService.doAction({type: 'ir.actions.act_window_close'});
        }
    }

    reprint() {
        this.printReceipt();
    }

    async printReceipt() {
        if (!this.receiptRef.el) return;
        const receiptEl = this.receiptRef.el.querySelector('.pos-receipt');
        if (!receiptEl) return;
        
        const receiptHtml = receiptEl.outerHTML;
        
        const iframe = document.createElement('iframe');
        iframe.style.position = 'fixed';
        iframe.style.left = '-2000px';
        iframe.style.width = '300px'; 
        document.body.appendChild(iframe);
        
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        
        // Copiar todos los estilos del backend
        const links = document.querySelectorAll('link[rel="stylesheet"], style');
        links.forEach(link => {
            iframeDoc.head.appendChild(link.cloneNode(true));
        });

        const style = iframeDoc.createElement('style');
        style.textContent = `
            @page { margin: 0; size: auto; }
            
            @media print {
                body, html { 
                    display: block !important; 
                    visibility: visible !important; 
                    background: white !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }
                body > * { 
                    display: none !important; 
                }
                body > .pos-receipt-print-wrapper { 
                    display: block !important; 
                    visibility: visible !important; 
                }
            }
            
            body { 
                background: white !important; 
                color: black !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", "Helvetica Neue", Arial, sans-serif !important;
                font-size: 14px !important;
                line-height: normal !important;
            }

            .pos-receipt-print-wrapper {
                width: 100%;
                display: block !important;
                visibility: visible !important;
            }

            .render-container {
                display: block !important;
                visibility: visible !important;
                margin: 0 auto !important;
                width: 300px !important;
            }

            .pos-receipt {
                width: 100% !important;
                display: block !important;
                visibility: visible !important;
                padding: 10px !important;
                box-sizing: border-box !important;
                background: white !important;
            }

            /* Asegurar que las reglas de alineación de Odoo y Xtendoo funcionen */
            .pos-receipt-right-align {
                float: right !important;
            }
            
            .pos-receipt * {
                visibility: visible !important;
            }

            .pos-receipt img { 
                max-width: 50% !important; 
                height: auto; 
                display: block; 
                margin: 0 auto 10px; 
            }
            
            .pos-receipt-qrcode {
                width: 100px !important;
                height: 100px !important;
                margin: 15px auto !important;
            }

            .d-none, .d-print-none { display: none !important; }
            
            /* Estilos específicos de Lucida Console para el diseño de Xtendoo */
            .custom-header, .pos-receipt-container {
                font-family: 'Lucida Console', 'DejaVu Sans Mono', monospace !important;
            }
        `;
        iframeDoc.head.appendChild(style);

        iframeDoc.body.innerHTML = `
            <div class="pos-receipt-print-wrapper">
                <div class="render-container">
                    ${receiptHtml}
                </div>
            </div>
        `;
        
        // Esperar imágenes
        const images = iframeDoc.querySelectorAll('img');
        const imagePromises = Array.from(images).map(img => {
            if (img.complete) return Promise.resolve();
            return new Promise(resolve => {
                img.onload = resolve;
                img.onerror = resolve;
            });
        });
        await Promise.all(imagePromises);
        
        setTimeout(() => {
            iframe.contentWindow.focus();
            iframe.contentWindow.print();
            
            setTimeout(() => {
                iframe.remove();
            }, 6000);
        }, 500);
    }
}

registry.category("actions").add("pos_conventional.print_receipt_client", PosReceiptClientAction);
