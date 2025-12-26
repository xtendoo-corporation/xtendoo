/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Función utilitaria que abre una URL en un iframe oculto y llama a print().
 * Devuelve una promesa que se resuelve cuando la impresión termina o falla.
 */
export async function openUrlInHiddenPrintIframe(url) {
    return new Promise((resolve, reject) => {
        try {
            // Crear iframe oculto
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
                    // Esperar un tick para asegurarse de que el contenido esté listo
                    setTimeout(() => {
                        try {
                            // Intentar imprimir
                            iframe.contentWindow.focus();
                            const printed = iframe.contentWindow.print();
                            // No podemos detectar realmente si el usuario imprimió o canceló,
                            // así que resolvemos tras un pequeño delay.
                            setTimeout(() => {
                                // Remover iframe
                                try { iframe.remove(); } catch (e) { /* ignore */ }
                                resolve(true);
                            }, 500);
                        } catch (e) {
                            try { iframe.remove(); } catch (er) { /* ignore */ }
                            reject(e);
                        }
                    }, 50);
                } catch (e) {
                    try { iframe.remove(); } catch (er) { /* ignore */ }
                    reject(e);
                }
            };
            iframe.onerror = function(err) {
                try { iframe.remove(); } catch (e) { /* ignore */ }
                reject(err);
            };
            document.body.appendChild(iframe);
        } catch (e) {
            reject(e);
        }
    });
}

// Registro opcional en registry para poder inyectarlo desde otras partes si se desea
registry.category('utils').add('pos_print_iframe', openUrlInHiddenPrintIframe);

