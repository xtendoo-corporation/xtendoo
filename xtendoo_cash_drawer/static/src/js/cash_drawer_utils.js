/** @odoo-module **/
/**
 * Utilidades compartidas para la apertura del cajón portamonedas.
 *
 * Estrategia de envío
 * -------------------
 * Se usa el endpoint proxy de Odoo (/xtendoo_cash_drawer/open) para evitar
 * restricciones CORS. El navegador llama a Odoo (mismo origen → sin CORS) y
 * Odoo realiza la petición al cajón desde Python con la cabecera x-api-key.
 *
 * Requisito de red
 * ----------------
 * La URL configurada debe apuntar a una IP accesible desde el servidor Odoo
 * (no a 127.0.0.1 del cliente). Ejemplo: http://192.168.18.7:3210/open-drawer?printer=POS-80C
 */
/**
 * Envía la señal de apertura al cajón a través del proxy de Odoo.
 *
 * @param {string}       baseUrl - URL configurada en pos.config
 * @param {string|false} apiKey  - API key configurada en pos.config
 * @returns {Promise<{success: boolean, status_code: number|null, error: string|null}>}
 */
export async function sendCashDrawerRequest(baseUrl, apiKey) {
    if (!baseUrl) {
        throw new Error("No hay URL configurada para el cajón portamonedas.");
    }
    console.log("[CashDrawer] Enviando petición vía proxy Odoo →", baseUrl);
    const response = await fetch("/xtendoo_cash_drawer/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: { url: baseUrl, api_key: apiKey || "" },
        }),
    });
    if (!response.ok) {
        throw new Error(`Error HTTP del proxy Odoo: ${response.status}`);
    }
    const json = await response.json();
    if (json.error) {
        throw new Error(json.error.data?.message || json.error.message || "Error en proxy Odoo");
    }
    return json.result || { success: false, error: "Respuesta vacía del proxy" };
}
/**
 * Construye la URL con la API key como query-param (uso interno/legacy).
 */
export function buildCashDrawerUrl(baseUrl, apiKey) {
    if (!apiKey) return baseUrl;
    const separator = baseUrl.includes("?") ? "&" : "?";
    return `${baseUrl}${separator}x-api-key=${encodeURIComponent(apiKey)}`;
}
