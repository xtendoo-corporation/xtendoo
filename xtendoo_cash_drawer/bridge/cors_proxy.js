/**
 * Proxy CORS para bridge del cajón portamonedas — Windows
 * ========================================================
 * Úsalo si tu bridge ya funciona pero NO tiene CORS configurado.
 * Este proxy escucha en el puerto 3211, añade las cabeceras CORS
 * y reenvía las peticiones al bridge real en el puerto 3212.
 *
 * Instalación en Windows:
 *   1. Instala Node.js desde https://nodejs.org (LTS)
 *   2. Abre CMD en esta carpeta y ejecuta:
 *        npm install
 *   3. Cambia tu bridge original para que escuche en el puerto 3212
 *      (o cambia BRIDGE_REAL_PORT aquí si usa otro puerto)
 *   4. Arranca el proxy:
 *        node cors_proxy.js
 *
 * Para que arranque automáticamente con Windows:
 *   npm install -g pm2
 *   pm2 start cors_proxy.js --name cajón-proxy
 *   pm2 startup
 *   pm2 save
 */

const http = require("http");

const PROXY_PORT = parseInt(process.env.PROXY_PORT || "3211", 10);   // Puerto que ve Odoo
const BRIDGE_HOST = process.env.BRIDGE_HOST || "127.0.0.1";          // Donde corre el bridge real
const BRIDGE_REAL_PORT = parseInt(process.env.BRIDGE_REAL_PORT || "3212", 10); // Puerto del bridge real

const CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "x-api-key, Content-Type",
    "Access-Control-Max-Age": "86400",
};

const server = http.createServer((req, res) => {
    // Añadir CORS a TODAS las respuestas
    Object.entries(CORS_HEADERS).forEach(([k, v]) => res.setHeader(k, v));

    // Preflight OPTIONS: responder 200 directamente sin reenviar al bridge
    if (req.method === "OPTIONS") {
        res.writeHead(200);
        res.end();
        console.log(`[proxy] OPTIONS ${req.url} → 200 (preflight)`);
        return;
    }

    // Reenviar la petición al bridge real
    const options = {
        hostname: BRIDGE_HOST,
        port: BRIDGE_REAL_PORT,
        path: req.url,
        method: req.method,
        headers: req.headers,
    };

    const proxyReq = http.request(options, (proxyRes) => {
        // Copiar cabeceras del bridge + las CORS encima
        const responseHeaders = { ...proxyRes.headers, ...CORS_HEADERS };
        res.writeHead(proxyRes.statusCode, responseHeaders);
        proxyRes.pipe(res, { end: true });
        console.log(`[proxy] ${req.method} ${req.url} → ${proxyRes.statusCode}`);
    });

    proxyReq.on("error", (err) => {
        console.error(`[proxy] Error conectando al bridge real (${BRIDGE_HOST}:${BRIDGE_REAL_PORT}):`, err.message);
        res.writeHead(502, { "Content-Type": "application/json", ...CORS_HEADERS });
        res.end(JSON.stringify({
            ok: false,
            error: `Bridge no disponible en ${BRIDGE_HOST}:${BRIDGE_REAL_PORT} — ${err.message}`,
        }));
    });

    req.pipe(proxyReq, { end: true });
});

server.listen(PROXY_PORT, "0.0.0.0", () => {
    console.log(`[proxy] CORS proxy escuchando en http://0.0.0.0:${PROXY_PORT}`);
    console.log(`[proxy] Reenviando peticiones a http://${BRIDGE_HOST}:${BRIDGE_REAL_PORT}`);
    console.log("[proxy] Cabeceras CORS añadidas automáticamente a todas las respuestas");
});
