/** @odoo-module **/
/**
 * Utilidades compartidas para la apertura del cajón portamonedas.
 *
 * Arquitectura: navegador → bridge local
 * --------------------------------------
 * La llamada al bridge sale directamente desde el navegador del usuario.
 * Esto permite que un Odoo cloud controle un bridge instalado en la LAN del
 * cliente, siempre que el navegador pueda llegar a la IP/URL configurada.
 *
 * Requisitos del bridge para esta arquitectura:
 *   - Debe devolver CORS para el origen de Odoo.
 *   - Si Odoo carga por HTTPS, el bridge debe exponerse también por HTTPS
 *     para evitar el bloqueo por mixed content del navegador.
 *
 * El bridge local puede estar en:
 *   - El propio PC del cajero (http://127.0.0.1:3210 o http://192.168.x.y:3210)
 *   - Cualquier equipo accesible desde el navegador del cajero por LAN
 *
 * API esperada del bridge
 * -----------------------
 *   GET /open-drawer?printer=<nombre>   → { "ok": true }  o  { "ok": false, "error": "..." }
 *   GET /health                         → { "status": "ok" }
 *   Header: x-api-key: <api_key>        (si el bridge requiere autenticación)
 *
 * Timeout por defecto: 8 segundos.
 */

/** Tiempo máximo de espera a la respuesta del bridge local (ms). */
const CASH_DRAWER_TIMEOUT_MS = 8000;

function getUrlProtocol(url) {
    try {
        return new URL(url, window.location.href).protocol;
    } catch {
        return "";
    }
}

function ensureBrowserCanReachBridge(url) {
    const pageProtocol = window.location.protocol;
    const bridgeProtocol = getUrlProtocol(url);

    if (pageProtocol === "https:" && bridgeProtocol === "http:") {
        throw new Error(
            "La web de Odoo está abierta por HTTPS pero el bridge está configurado en HTTP. " +
            "El navegador bloqueará la petición por seguridad (mixed content). " +
            "Configura el bridge con HTTPS, por ejemplo https://IP_DEL_PC:3212."
        );
    }
}

async function readResponsePayload(response) {
    const rawText = await response.text();
    if (!rawText) {
        return null;
    }

    try {
        return JSON.parse(rawText);
    } catch {
        return rawText;
    }
}

function extractBridgeError(payload, fallbackMessage) {
    if (payload && typeof payload === "object") {
        if (payload.error) {
            return payload.error;
        }
        if (payload.detail) {
            return payload.detail;
        }
        if (payload.message) {
            return payload.message;
        }
    }

    if (typeof payload === "string" && payload.trim()) {
        return payload.trim();
    }

    return fallbackMessage;
}

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
    ensureBrowserCanReachBridge(url);

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
            "No se pudo contactar con el bridge local. " +
            "Revisa conectividad, CORS, certificado HTTPS y que la URL del bridge sea accesible desde este navegador. " +
            (err.message || String(err))
        );
    } finally {
        clearTimeout(timeoutId);
    }
}

/**
 * Envía la señal de apertura al cajón portamonedas directamente al bridge.
 *
 * @param {object} config - Objeto pos.config con los campos del cajón
 * @returns {Promise<{ok: boolean, raw?: object}>}
 * @throws {Error} Con mensaje legible si hay fallo de red, timeout o respuesta inválida
 */
export async function sendCashDrawerRequest(config) {
    const url = buildCashDrawerUrl(config);
    const apiKey = (config.cash_drawer_api_key || "").trim();
    const headers = {};

    if (apiKey) {
        headers["x-api-key"] = apiKey;
    }

    console.log("[CashDrawer] Enviando apertura directa al bridge:", url);

    const response = await fetchWithTimeout(url, {
        method: "GET",
        mode: "cors",
        headers,
    });

    const payload = await readResponsePayload(response);

    if (!response.ok) {
        throw new Error(
            extractBridgeError(payload, `El bridge devolvió HTTP ${response.status}.`)
        );
    }

    if (payload && typeof payload === "object" && payload.ok === false) {
        throw new Error(payload.error || "El bridge rechazó la petición de apertura.");
    }

    return { ok: true, raw: payload ?? { status: response.status } };
}

/**
 * Envía la señal de apertura del cajón a través del proxy Odoo.
 *
 * Arquitectura: navegador → Odoo (proxy Python) → bridge local
 * -------------------------------------------------------------
 * Al ir por Odoo, la petición sale del SERVIDOR, eliminando cualquier
 * problema de CORS o de mixed-content HTTPS/HTTP en el navegador.
 * Es el canal recomendado para el TPV en producción.
 *
 * Endpoint usado: POST /xtendoo_cash_drawer/open  (JSON-RPC)
 *
 * @param {object} config - Objeto pos.config con los campos del cajón
 * @returns {Promise<{ok: boolean, raw?: object}>}
 * @throws {Error} Con mensaje legible si hay fallo de red, proxy o bridge
 */
export async function sendCashDrawerViaProxy(config) {
    let drawerUrl;
    try {
        drawerUrl = buildCashDrawerUrl(config);
    } catch (err) {
        throw new Error(err.message);
    }
    const apiKey = (config.cash_drawer_api_key || "").trim();

    let response;
    try {
        response = await fetch("/xtendoo_cash_drawer/open", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                id: null,
                params: { url: drawerUrl, api_key: apiKey },
            }),
        });
    } catch (err) {
        throw new Error(
            "No se pudo contactar con el servidor Odoo para abrir el cajón. " +
            (err.message || String(err))
        );
    }

    if (!response.ok) {
        throw new Error(`Error HTTP ${response.status} al contactar el servidor Odoo.`);
    }

    let data;
    try {
        data = await response.json();
    } catch {
        throw new Error("Respuesta inesperada del servidor Odoo (no es JSON).");
    }

    if (data.error) {
        const msg =
            data.error?.data?.message ||
            data.error?.message ||
            "Error del servidor Odoo.";
        throw new Error(msg);
    }

    const result = data.result;
    if (!result || !result.success) {
        throw new Error(result?.error || "El cajón no pudo abrirse vía proxy.");
    }

    return { ok: true, raw: result };
}

export async function checkCashDrawerHealth(config) {
    let url;
    try {
        url = buildCashDrawerHealthUrl(config);
    } catch (err) {
        return { available: false, detail: err.message };
    }

    try {
        const response = await fetchWithTimeout(url, {
            method: "GET",
            mode: "cors",
        });
        const payload = await readResponsePayload(response);

        if (!response.ok) {
            return {
                available: false,
                detail: extractBridgeError(payload, `Bridge no disponible (HTTP ${response.status})`),
            };
        }

        const detail =
            payload && typeof payload === "object" && payload.status
                ? `Bridge disponible (status: ${payload.status})`
                : "Bridge disponible";

        return {
            available: true,
            detail,
        };
    } catch (err) {
        return { available: false, detail: err.message };
    }
}
