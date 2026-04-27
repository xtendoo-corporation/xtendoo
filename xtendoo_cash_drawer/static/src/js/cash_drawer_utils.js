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

/**
 * Reintentos automáticos cuando `fetch` lanza TypeError ("Failed to fetch").
 *
 * Este error genérico del navegador agrupa varias causas transitorias que
 * típicamente desaparecen al recargar la pestaña con CTRL+F5:
 *  - Caché de fallo de preflight CORS de la sesión anterior.
 *  - Heurística de Private Network Access (PNA) en Chrome que rechaza la
 *    primera petición desde un origen público a una IP privada.
 *  - Conexiones HTTP/2 reusadas que ya estaban cerradas en el otro extremo.
 *  - Bridge local recién arrancado tras un cambio de red/DHCP.
 *
 * Reintentar una sola vez con un pequeño backoff cubre la inmensa mayoría
 * de los casos sin penalizar al usuario en caso de fallo real (timeout
 * efectivo: 8s + 250ms + 8s ≈ 16s en el peor caso).
 */
const CASH_DRAWER_FETCH_RETRIES = 1;
const CASH_DRAWER_RETRY_DELAY_MS = 250;

function _isTransientFetchError(err) {
    // `fetch` lanza TypeError tanto para "Failed to fetch" (Chrome) como para
    // "NetworkError when attempting to fetch resource." (Firefox).
    return err && err.name === "TypeError";
}

function _delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

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

    let lastError = null;
    for (let attempt = 0; attempt <= CASH_DRAWER_FETCH_RETRIES; attempt++) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        try {
            return await fetch(url, { ...options, signal: controller.signal });
        } catch (err) {
            lastError = err;
            if (err.name === "AbortError") {
                throw new Error(
                    `Tiempo de espera agotado (${timeoutMs / 1000}s) esperando respuesta del servidor.`
                );
            }
            // Solo reintentamos errores transitorios y mientras queden intentos.
            if (
                !_isTransientFetchError(err) ||
                attempt >= CASH_DRAWER_FETCH_RETRIES
            ) {
                break;
            }
            console.warn(
                `[CashDrawer] Fetch transitorio fallido (intento ${attempt + 1}), reintentando…`,
                err.message || err
            );
            await _delay(CASH_DRAWER_RETRY_DELAY_MS);
        } finally {
            clearTimeout(timeoutId);
        }
    }

    throw new Error(
        "No se pudo contactar con el bridge local. " +
        "Revisa conectividad, CORS, certificado HTTPS y que la URL del bridge sea accesible desde este navegador. " +
        "Si el problema solo ocurre al abrir el TPV y se resuelve recargando con CTRL+F5, " +
        "es probable que el navegador haya cacheado un fallo previo o que el bridge no estuviera disponible al iniciar la sesión. " +
        (lastError?.message || String(lastError))
    );
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
