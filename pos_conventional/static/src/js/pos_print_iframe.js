/** @odoo-module */

import { registry } from "@web/core/registry";

export async function openUrlInHiddenPrintIframe(url) {
    return new Promise((resolve, reject) => {
        try {
            const iframe = document.createElement('iframe');
            iframe.style.position = 'fixed';
            iframe.style.right = '0';
            iframe.style.bottom = '0';
            iframe.style.width = '1px';
            iframe.style.height = '1px';
            iframe.style.border = '0';
            iframe.style.opacity = '0';
            iframe.style.pointerEvents = 'none';
            iframe.src = url;
            iframe.onload = function() {
                try {
                    setTimeout(() => {
                        try {
                            iframe.contentWindow.focus();
                            const printed = iframe.contentWindow.print();
                            setTimeout(() => {
                                try { iframe.remove(); } catch (e) { }
                                resolve(true);
                            }, 500);
                        } catch (e) {
                            try { iframe.remove(); } catch (er) { }
                            reject(e);
                        }
                    }, 50);
                } catch (e) {
                    try { iframe.remove(); } catch (er) { }
                    reject(e);
                }
            };
            iframe.onerror = function(err) {
                try { iframe.remove(); } catch (e) { }
                reject(err);
            };
            document.body.appendChild(iframe);
        } catch (e) {
            reject(e);
        }
    });
}

registry.category('utils').add('pos_print_iframe', openUrlInHiddenPrintIframe);

const printIframeAction = async (env, action) => {
    const params = action.params || {};

    if (params.url) {
        try {
            await openUrlInHiddenPrintIframe(params.url);
        } catch (error) {
            console.error("Error al imprimir iframe:", error);
            env.services.notification.add("Error al imprimir el documento.", {
                type: "danger",
            });
        }
    }

    if (params.next_action) {
        return env.services.action.doAction(params.next_action);
    }

    return { type: "ir.actions.act_window_close" };
};

registry.category("actions").add("pos_conventional_print_iframe", printIframeAction);
