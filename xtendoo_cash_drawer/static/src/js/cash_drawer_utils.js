/** @odoo-module **/
/**
 * Utilidades compartidas para la apertura del cajón portamonedas.
 *
 * Arquitectura: navegador → proxy Odoo → bridge local
 * ----------------------------------------------------
 * La llamada al bridge NO sale directamente desde el navegador. En su lugar,
 * el JS llama al controlador Odoo (/xtendoo_cash_drawer/open) que actúa como
 * proxy y reenvía la petición al bridge por IP LAN desde el servidor Python.
 *
 * Esto resuelve definitivamente el problema CORS:
 *   - Navegador → Odoo: mismo origen, CERO restricciones CORS.
 *   - Odoo Python → bridge: petición servidor-a-servidor, sin CORS.
 *
 * El bridge local puede estar en:
 *   - El propio PC del cajero (http://127.0.0.1:3210 o http://192.168.x.y:3210)
 *   - Cualquier equipo accesible desde el servidor Odoo por LAN
 *
 * El bridge NO necesita configurar cabeceras CORS con esta arquitectura.
 *
 * API esperada del bridge (la llama Odoo, no el navegador)
 * ---------------------------------------------------------
 *   GET /open-drawer?printer=<nombre>   → { "ok": true }  o  { "ok": false, "error": "..." }
 *   GET /health                         → { "status": "ok" }
 *   Header: x-api-key: <api_key>        (si el bridge requiere autenticación)
 *
 * Timeout por defecto: 8 segundos (incluye el round-trip Odoo + bridge).
 */

/** Tiempo máximo de espera a la respuesta del proxy Odoo (ms). */
const CASH_DRAWER_TIMEOUT_MS = 8000;

/**
 * Construye la URL completa del endpoint de apertura del bridge local.
 *
 * La URL base puede venir con o sin trailing slash y con o sin query string
 * ya definida. El nombre de impresora se añade como parámetro `printer`.
 *
 * Ejemplos de resultado:
 *   buildCashDrawerUrl({ cash_drawer_bridge_url: "http://127.0.0.1:3211", cash_drawer_printer_name: "POS-80C" })
 *   → "http://127.0.0.1:3211/open-drawer?printer=POS-80C"
 *
 *   buildCashDrawerUrl({ cash_drawer_bridge_url: "http://192.168.1.50:3211/open-drawer?printer=STAR" })
 *   → "http://192.168.1.50:3211/open-drawer?printer=STAR"  (ya tiene printer, se respeta)
 *
 * @param {object} config - Objeto pos.config (o equivalente con los campos del cajón)
 * @param {string} [config.cash_drawer_bridge_url]   - URL base del bridge local
 * @param {string} [config.cash_drawer_printer_name] - Nombre de la impresora
 * @returns {string} URL completa lista para usar en fetch()
 * @throws {Error} Si no hay URL base configurada
 */
export function buildCashDrawerUrl(config) {
    const base = (config.cash_drawer_bridge_url || "").trim();
    if (!base) {
        throw new Error(
            "No hay URL del bridge local configurada para el cajón portamonedas. " +
            "Configura 'URL del bridge local' en los ajustes del TPV."
        );
    }

    // Si la URL ya contiene el path /open-drawer, la usamos tal cual (permite
    // configuraciones avanzadas donde el usuario mete la URL completa).
    if (base.includes("/open-drawer")) {
        return base;
    }

    const normalizedBase = base.replace(/\/$/, "");
    const printerName = (config.cash_drawer_printer_name || "").trim();
    const printerParam = printerName
        ? `?printer=${encodeURIComponent(printerName)}`
        : "";
    return `${normalizedBase}/open-drawer${printerParam}`;
}

/**
 * Construye la URL del endpoint de health check del bridge local.
 *
 * @param {object} config - Objeto pos.config
 * @returns {string} URL del health check
 * @throws {Error} Si no hay URL base configurada
 */
export function buildCashDrawerHealthUrl(config) {
    const base = (config.cash_drawer_bridge_url || "").trim();
    if (!base) {
        throw new Error("No hay URL del bridge local configurada.");
    }
    return `${base.replace(/\/$/, "")}/health`;
}

/**
 * Realiza un fetch con timeout usando AbortController.
 *
 * @param {string} url            - URL a llamar
 * @param {RequestInit} options   - Opciones de fetch (method, headers, …)
 * @param {number} [timeoutMs]    - Timeout en milisegundos
 * @returns {Promise<Response>}
 * @throws {Error} Con mensaje descriptivo en caso de timeout o error de red
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = CASH_DRAWER_TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } catch (err) {
        if (err.name === "AbortError") {
            throw new Error(
                `Tiempo de espera agotado (${timeoutMs / 1000}s) esperando respuesta del servidor.`
            );
        }
        throw new Error(
            "No se pudo contactar con el servidor Odoo: " + (err.message || String(err))
        );
    } finally {
        clearTimeout(timeoutId);
    }
}

/**
 * Llamada JSONRPC al proxy Odoo para apertura o health check del bridge.
 *
 * El proxy Odoo (/xtendoo_cash_drawer/open o /xtendoo_cash_drawer/health)
 * recibe los parámetros y reenvía la petición al bridge desde Python.
 * Así el navegador nunca contacta el bridge directamente → sin CORS.
 *
 * @param {string} endpoint  - Ruta relativa Odoo: "/xtendoo_cash_drawer/open" o "/health"
 * @param {object} params    - Parámetros JSONRPC (url, api_key, …)
 * @returns {Promise<object>} - Campo `result` de la respuesta JSONRPC
 * @throws {Error} Con mensaje descriptivo
 */
async function callOdooProxy(endpoint, params) {
    const payload = {
        jsonrpc: "2.0",
        method: "call",
        id: Date.now(),
        params,
    };

    const response = await fetchWithTimeout(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload),
    });

    let json;
    try {
        json = await response.json();
    } catch {
        throw new Error(
            `El servidor Odoo devolvió una respuesta no válida (HTTP ${response.status}).`
        );
    }

    if (json.error) {
        const detail =
            json.error?.data?.message ||
            json.error?.message ||
            JSON.stringify(json.error);
        throw new Error("Error en el servidor Odoo: " + detail);
    }

    if (!json.result && json.result !== false) {
        throw new Error("Respuesta vacía del proxy Odoo.");
    }

    return json.result;
}

/**
 * Envía la señal de apertura al cajón portamonedas usando el proxy Odoo.
 *
 * Flujo:
 *   1. Construye la URL del bridge con buildCashDrawerUrl(config).
 *   2. Llama a POST /xtendoo_cash_drawer/open en Odoo (mismo origen, sin CORS).
 *   3. Odoo (Python) reenvía GET /open-drawer?printer=... al bridge con x-api-key.
 *   4. Devuelve { ok: true } o lanza Error descriptivo.
 *
 * @param {object} config - Objeto pos.config con los campos del cajón
 * @returns {Promise<{ok: boolean, raw?: object}>}
 * @throws {Error} Con mensaje legible si hay fallo de red, timeout o respuesta inválida
 */
export async function sendCashDrawerRequest(config) {
    const url = buildCashDrawerUrl(config);
    const apiKey = (config.cash_drawer_api_key || "").trim();

    console.log("[CashDrawer] Enviando apertura vía proxy Odoo → bridge:", url);

    const result = await callOdooProxy("/xtendoo_cash_drawer/open", {
        url,
        api_key: apiKey,
    });

    if (!result.success) {
        throw new Error(result.error || "El bridge rechazó la petición de apertura.");
    }

    return { ok: true, raw: result };
}

/**
 * Comprueba la disponibilidad del bridge llamando a GET /health via proxy Odoo.
 *
 * No lanza excepción: siempre devuelve { available: boolean, detail: string }.
 *
 * @param {object} config - Objeto pos.config con los campos del cajón
 * @returns {Promise<{available: boolean, detail: string}>}
 */
export async function checkCashDrawerHealth(config) {
    let url;
    try {
        url = buildCashDrawerHealthUrl(config);
    } catch (err) {
        return { available: false, detail: err.message };
    }

    try {
        const result = await callOdooProxy("/xtendoo_cash_drawer/health", { url });
        return {
            available: result.available ?? false,
            detail: result.detail || (result.available ? "Bridge disponible" : "Bridge no disponible"),
        };
    } catch (err) {
        return { available: false, detail: err.message };
    }
}
