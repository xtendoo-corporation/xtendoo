/** @odoo-module **/
/**
 * Utilidades compartidas para la apertura del cajón portamonedas.
 *
 * Arquitectura: frontend directo al bridge local
 * -----------------------------------------------
 * La llamada sale DESDE EL NAVEGADOR del TPV hacia el bridge local que corre
 * en el propio PC del cajero (normalmente http://127.0.0.1:3211) o en la LAN
 * del cliente. Odoo no actúa como proxy: no hay llamada Python intermedia.
 *
 * Consideraciones CORS
 * --------------------
 * El bridge local recibe peticiones desde una web Odoo cloud (origen distinto),
 * por lo que DEBE responder con las cabeceras CORS adecuadas:
 *
 *   Access-Control-Allow-Origin: *            (o el origen exacto de Odoo)
 *   Access-Control-Allow-Headers: x-api-key, Content-Type
 *   Access-Control-Allow-Methods: GET, OPTIONS
 *
 * Si el bridge no tiene CORS configurado, el navegador bloqueará la respuesta
 * y la función lanzará un error de red. En ese caso el bridge debe actualizarse.
 *
 * API esperada del bridge
 * -----------------------
 *   GET /open-drawer?printer=<nombre>   → { "ok": true }  o  { "ok": false, "error": "..." }
 *   GET /health                         → { "status": "ok" }
 *   Header: x-api-key: <api_key>        (si el bridge requiere autenticación)
 *
 * Timeout por defecto: 5 segundos. Se usa AbortController.
 */

/** Tiempo máximo de espera a la respuesta del bridge (ms). */
const CASH_DRAWER_TIMEOUT_MS = 5000;

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
                `Tiempo de espera agotado (${timeoutMs / 1000}s) al conectar con el bridge del cajón en: ${url}`
            );
        }
        // Error de red / CORS: el navegador no puede alcanzar el bridge
        throw new Error(
            `No se pudo conectar con el bridge del cajón en: ${url}\n` +
            "Comprueba que el bridge está en ejecución y que tiene CORS habilitado. " +
            "Detalle técnico: " + (err.message || String(err))
        );
    } finally {
        clearTimeout(timeoutId);
    }
}

/**
 * Envía la señal de apertura al cajón portamonedas llamando DIRECTAMENTE
 * al bridge local desde el navegador del TPV.
 *
 * Flujo:
 *   1. Construye la URL con buildCashDrawerUrl(config).
 *   2. Realiza GET /open-drawer?printer=... con cabecera x-api-key.
 *   3. Parsea la respuesta JSON.
 *   4. Lanza Error descriptivo ante cualquier fallo.
 *
 * @param {object} config - Objeto pos.config con los campos del cajón
 * @returns {Promise<{ok: boolean, raw?: object}>}
 * @throws {Error} Con mensaje legible si hay fallo de red, CORS, timeout o respuesta inválida
 */
export async function sendCashDrawerRequest(config) {
    const url = buildCashDrawerUrl(config);
    const apiKey = (config.cash_drawer_api_key || "").trim();

    const headers = {};
    if (apiKey) {
        headers["x-api-key"] = apiKey;
    }

    console.log("[CashDrawer] Enviando petición directa al bridge →", url);

    const response = await fetchWithTimeout(url, { method: "GET", headers });

    // Intentamos parsear JSON independientemente del status HTTP
    let json;
    try {
        json = await response.json();
    } catch {
        // El bridge respondió algo no-JSON (HTML de error, texto plano, etc.)
        if (!response.ok) {
            throw new Error(
                `El bridge respondió HTTP ${response.status} con contenido no JSON. ` +
                "Verifica que la URL del bridge es correcta."
            );
        }
        // Status 2xx pero sin JSON: aceptamos como éxito (algunos bridges devuelven 200 vacío)
        console.warn("[CashDrawer] Respuesta sin JSON con status", response.status);
        return { ok: true };
    }

    if (!response.ok) {
        const errMsg = json?.error || json?.message || `HTTP ${response.status}`;
        throw new Error(`El bridge respondió con error: ${errMsg}`);
    }

    // El bridge devuelve { ok: true/false, ... }
    if (json.ok === false) {
        throw new Error(
            "El bridge rechazó la apertura del cajón: " +
            (json.error || json.message || "Sin detalles")
        );
    }

    return { ok: true, raw: json };
}

/**
 * Comprueba la disponibilidad del bridge local llamando a GET /health.
 *
 * Útil para mostrar el estado del bridge al cargar el POS o antes de una
 * operación importante. No lanza excepción: siempre devuelve un objeto
 * con { available: boolean, detail: string }.
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
        const response = await fetchWithTimeout(url, { method: "GET" }, 3000);
        if (!response.ok) {
            return {
                available: false,
                detail: `Bridge no disponible (HTTP ${response.status})`,
            };
        }
        // Intentamos leer JSON, pero aceptamos cualquier respuesta 2xx como OK
        let detail = "Bridge disponible";
        try {
            const json = await response.json();
            detail = json?.status
                ? `Bridge disponible (status: ${json.status})`
                : "Bridge disponible";
        } catch {
            // Respuesta 2xx sin JSON: bridge disponible igualmente
        }
        return { available: true, detail };
    } catch (err) {
        return { available: false, detail: err.message };
    }
}
