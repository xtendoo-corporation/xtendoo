/** @odoo-module */

import { registry } from "@web/core/registry";
import { openUrlInHiddenPrintIframe } from "./pos_print_iframe";

/**
 * Client action registered as 'pos_conventional.print_iframe'.
 * Expects action.params.url with the report HTML URL.
 */
async function printIframeAction(env, action) {
    const params = action.params || {};
    const url = params.url;
    if (!url) {
        env.services.notification.add('No se ha proporcionado URL para imprimir.', { type: 'warning' });
        return;
    }
    const absolute = new URL(url, window.location.origin).toString();
    try {
        await openUrlInHiddenPrintIframe(absolute + '?download=false');
        env.services.notification.add('Enviado a impresora.', { type: 'success' });
    } catch (err) {
        console.error('Error imprimiendo en iframe, intentando fallback window.open:', err);
        // Fallback: abrir en nueva ventana y llamar print()
        try {
            const w = window.open(absolute + '?download=false', '_blank');
            if (w) {
                // Intentar imprimir cuando cargue
                const onLoad = () => {
                    try { w.focus(); w.print(); } catch (e) { console.error(e); }
                    // opcional: no cerrar la ventana automáticamente para que el usuario confirme
                };
                w.addEventListener ? w.addEventListener('load', onLoad, { once: true }) : (w.onload = onLoad);
                env.services.notification.add('Informe abierto en pestaña nueva para imprimir.', { type: 'info' });
            } else {
                env.services.notification.add('El navegador bloqueó la apertura de la ventana de impresión.', { type: 'warning' });
            }
        } catch (e) {
            console.error('Fallback failed', e);
            env.services.notification.add('Error al imprimir: ' + (e.message || e), { type: 'danger' });
        }
    }

    // Tras la impresión (o fallback) intentamos cerrar/recargar la vista para que el pedido avance.
    try {
        const actionService = env.services.action;
        const controller = actionService.currentController;
        if (controller && controller.jsId) {
            // Restaurar el controlador actual para forzar refresh
            await actionService.restore(controller.jsId);
        } else {
            // Fallback: desencadenar una acción client 'reload' registrada en el core
            await actionService.doAction({ type: 'ir.actions.client', tag: 'reload' });
        }
    } catch (e) {
        console.error('Error al recargar/actualizar la vista tras impresión:', e);
    }
}

registry.category('actions').add('pos_conventional.print_iframe', printIframeAction, { force: true });
