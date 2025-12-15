/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, xml, useState } from "@odoo/owl";

/**
 * Acción cliente para imprimir el ticket/recibo POS desde el backend.
 * Esta acción es llamada cuando se valida y factura un pedido POS
 * desde la vista de formulario del backend.
 */
async function posPrintReceiptAction(env, action) {
    const orm = env.services.orm;
    const notification = env.services.notification;
    const actionService = env.services.action;

    const orderId = action.params?.order_id;
    const invoiceId = action.params?.invoice_id;
    const invoiceName = action.params?.invoice_name;

    if (!orderId) {
        notification.add("No se pudo identificar el pedido", { type: "danger" });
        return;
    }

    try {
        // Obtener datos del recibo
        const receiptData = await orm.call(
            "pos.order",
            "get_receipt_data",
            [[orderId]]
        );

        // Generar HTML del ticket
        const ticketHtml = generateTicketHtml(receiptData);

        // Abrir ventana de impresión
        printTicket(ticketHtml);

        // Mostrar notificación de éxito
        notification.add(
            `Factura ${invoiceName} creada. Imprimiendo ticket...`,
            { type: "success", sticky: false }
        );

        // Recargar la vista actual
        await actionService.doAction({
            type: 'ir.actions.client',
            tag: 'reload',
        });

    } catch (error) {
        console.error("Error al imprimir ticket:", error);
        notification.add(
            `Error al imprimir ticket: ${error.message || error}`,
            { type: "danger" }
        );
    }
}

/**
 * Genera el HTML del ticket POS con formato para impresora térmica (80mm)
 */
function generateTicketHtml(data) {
    const order = data.order;
    const company = data.company;
    const partner = data.partner;
    const lines = data.lines;
    const payments = data.payments;
    const invoice = data.invoice;

    // Formatear moneda
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('es-ES', {
            style: 'currency',
            currency: 'EUR'
        }).format(amount);
    };

    let linesHtml = '';
    for (const line of lines) {
        const lineTotal = formatCurrency(line.price_subtotal_incl);
        const unitPrice = formatCurrency(line.price_unit);
        linesHtml += `
            <tr>
                <td colspan="4" class="product-name">${line.product_name}</td>
            </tr>
            <tr class="line-details">
                <td class="qty">${line.qty}</td>
                <td class="unit-price">${unitPrice}</td>
                <td class="discount">${line.discount > 0 ? line.discount + '%' : ''}</td>
                <td class="line-total">${lineTotal}</td>
            </tr>
        `;
    }

    let paymentsHtml = '';
    for (const payment of payments) {
        paymentsHtml += `
            <tr>
                <td>${payment.payment_method}</td>
                <td class="amount">${formatCurrency(payment.amount)}</td>
            </tr>
        `;
    }

    const html = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Ticket POS - ${order.name}</title>
    <style>
        @page {
            size: 80mm auto;
            margin: 0;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            width: 80mm;
            padding: 5mm;
            background: white;
        }
        .header {
            text-align: center;
            margin-bottom: 10px;
            border-bottom: 1px dashed #000;
            padding-bottom: 10px;
        }
        .company-name {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .company-info {
            font-size: 10px;
            line-height: 1.4;
        }
        .invoice-info {
            text-align: center;
            margin: 10px 0;
            font-weight: bold;
            font-size: 14px;
        }
        .order-info {
            margin-bottom: 10px;
            font-size: 10px;
        }
        .order-info table {
            width: 100%;
        }
        .order-info td {
            padding: 2px 0;
        }
        .order-info .label {
            font-weight: bold;
        }
        .lines-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        .lines-table th {
            text-align: left;
            border-bottom: 1px solid #000;
            padding: 3px 0;
            font-size: 10px;
        }
        .lines-table td {
            padding: 2px 0;
            font-size: 11px;
        }
        .product-name {
            font-weight: bold;
        }
        .line-details td {
            font-size: 10px;
            color: #333;
        }
        .qty {
            width: 15%;
        }
        .unit-price {
            width: 25%;
        }
        .discount {
            width: 15%;
            text-align: center;
        }
        .line-total {
            width: 30%;
            text-align: right;
        }
        .totals {
            border-top: 1px dashed #000;
            margin-top: 10px;
            padding-top: 10px;
        }
        .totals table {
            width: 100%;
        }
        .totals td {
            padding: 3px 0;
        }
        .totals .label {
            text-align: left;
        }
        .totals .amount {
            text-align: right;
            font-weight: bold;
        }
        .total-row {
            font-size: 16px;
            font-weight: bold;
            border-top: 1px solid #000;
            margin-top: 5px;
            padding-top: 5px;
        }
        .payments {
            margin-top: 10px;
            border-top: 1px dashed #000;
            padding-top: 10px;
        }
        .payments-title {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .payments table {
            width: 100%;
        }
        .payments td {
            padding: 2px 0;
        }
        .payments .amount {
            text-align: right;
        }
        .footer {
            text-align: center;
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px dashed #000;
            font-size: 10px;
        }
        .footer .thanks {
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .customer-info {
            margin-top: 10px;
            font-size: 10px;
            border-top: 1px dashed #000;
            padding-top: 5px;
        }
        @media print {
            body {
                width: 80mm;
            }
            .no-print {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">${company.name}</div>
        <div class="company-info">
            ${company.vat ? `CIF: ${company.vat}<br>` : ''}
            ${company.street ? `${company.street}<br>` : ''}
            ${company.street2 ? `${company.street2}<br>` : ''}
            ${company.zip || company.city ? `${company.zip} ${company.city}<br>` : ''}
            ${company.phone ? `Tel: ${company.phone}<br>` : ''}
        </div>
    </div>

    ${invoice.name ? `<div class="invoice-info">FACTURA: ${invoice.name}</div>` : ''}

    <div class="order-info">
        <table>
            <tr>
                <td class="label">Ticket:</td>
                <td>${order.pos_reference || order.name}</td>
            </tr>
            <tr>
                <td class="label">Fecha:</td>
                <td>${order.date_order}</td>
            </tr>
        </table>
    </div>

    ${partner.name ? `
    <div class="customer-info">
        <strong>Cliente:</strong> ${partner.name}
        ${partner.vat ? `<br>NIF/CIF: ${partner.vat}` : ''}
    </div>
    ` : ''}

    <table class="lines-table">
        <thead>
            <tr>
                <th>Cant.</th>
                <th>P.Unit</th>
                <th>Dto.</th>
                <th style="text-align:right">Total</th>
            </tr>
        </thead>
        <tbody>
            ${linesHtml}
        </tbody>
    </table>

    <div class="totals">
        <table>
            <tr>
                <td class="label">Base imponible:</td>
                <td class="amount">${formatCurrency(order.amount_total - order.amount_tax)}</td>
            </tr>
            <tr>
                <td class="label">Impuestos:</td>
                <td class="amount">${formatCurrency(order.amount_tax)}</td>
            </tr>
            <tr class="total-row">
                <td class="label">TOTAL:</td>
                <td class="amount">${formatCurrency(order.amount_total)}</td>
            </tr>
        </table>
    </div>

    <div class="payments">
        <div class="payments-title">Forma de pago:</div>
        <table>
            ${paymentsHtml}
        </table>
        ${order.amount_return > 0 ? `
        <table>
            <tr>
                <td><strong>Cambio:</strong></td>
                <td class="amount"><strong>${formatCurrency(order.amount_return)}</strong></td>
            </tr>
        </table>
        ` : ''}
    </div>

    <div class="footer">
        <div class="thanks">¡Gracias por su compra!</div>
        <div>Conserve este ticket para cualquier reclamación</div>
    </div>
</body>
</html>
    `;

    return html;
}

/**
 * Abre una ventana de impresión con el ticket
 * Usa el mismo método que Odoo: renderiza en el DOM y llama a window.print()
 */
function printTicket(html) {
    // Crear un contenedor oculto para el ticket
    const printContainer = document.createElement('div');
    printContainer.id = 'pos-receipt-print-container';
    printContainer.innerHTML = html;

    // Estilos para ocultar el contenedor en pantalla pero mostrarlo en impresión
    const style = document.createElement('style');
    style.id = 'pos-receipt-print-style';
    style.textContent = `
        #pos-receipt-print-container {
            display: none;
        }
        @media print {
            @page {
                size: 80mm auto;
                margin: 0;
            }
            html, body {
                width: 80mm !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            body > *:not(#pos-receipt-print-container) {
                display: none !important;
            }
            #pos-receipt-print-container {
                display: block !important;
                position: relative;
                width: 80mm !important;
                margin: 0 auto !important;
                padding: 5mm !important;
            }
            #pos-receipt-print-container * {
                visibility: visible !important;
            }
        }
    `;

    document.head.appendChild(style);
    document.body.appendChild(printContainer);

    // Esperar a que las imágenes se carguen (si las hay)
    const images = printContainer.querySelectorAll('img');
    const imagePromises = Array.from(images).map(img => {
        if (img.complete) return Promise.resolve();
        return new Promise((resolve) => {
            img.onload = resolve;
            img.onerror = resolve;
        });
    });

    Promise.all(imagePromises).then(() => {
        // Pequeño delay para asegurar renderizado
        setTimeout(() => {
            window.print();

            // Limpiar después de imprimir
            setTimeout(() => {
                if (printContainer.parentNode) {
                    printContainer.parentNode.removeChild(printContainer);
                }
                if (style.parentNode) {
                    style.parentNode.removeChild(style);
                }
            }, 1000);
        }, 100);
    });
}

// Registrar la acción cliente
registry.category("actions").add("pos_print_receipt", posPrintReceiptAction);

