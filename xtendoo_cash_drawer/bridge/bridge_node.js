/**
 * Bridge local para apertura de cajón portamonedas — Node.js + Express
 * ======================================================================
 * Instala las dependencias:
 *   npm install express serialport @serialport/parser-readline
 *
 * Arranca el bridge:
 *   node bridge_node.js
 *
 * Variables de entorno (opcionales):
 *   BRIDGE_PORT=3211
 *   BRIDGE_API_KEY=mi_clave_secreta   (vacío = sin autenticación)
 *   PRINTER_PORT=/dev/ttyUSB0         (o COM3 en Windows)
 */

const express = require("express");
const { SerialPort } = require("serialport");

const app = express();
app.use(express.json({ limit: "1mb" }));

const BRIDGE_PORT = parseInt(process.env.BRIDGE_PORT || "3211", 10);
const API_KEY = process.env.BRIDGE_API_KEY || "";

// Mapa nombre_impresora → puerto serie
const PRINTER_PORTS = {
    "POS-80C": process.env.PRINTER_PORT || "/dev/ttyUSB0",
    "EPSON": process.env.PRINTER_PORT_EPSON || "/dev/ttyUSB0",
    // "STAR": "COM3",
};

// Comando ESC/POS de apertura de cajón: ESC p <pin> <on-time> <off-time>
const OPEN_DRAWER_CMD = Buffer.from([0x1b, 0x70, 0x00, 0x19, 0xfa]);

// ── CORS ──────────────────────────────────────────────────────────────────────
// Necesario para que el navegador del TPV (Odoo en cloud) pueda llamar al bridge LAN
app.use((req, res, next) => {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "x-api-key, Content-Type");
    // Preflight: responder 200 inmediatamente, sin pasar por auth
    if (req.method === "OPTIONS") {
        return res.sendStatus(200);
    }
    next();
});

// ── Middleware de autenticación ───────────────────────────────────────────────
function checkApiKey(req, res, next) {
    if (!API_KEY) return next(); // sin auth configurada
    const key = req.headers["x-api-key"] || "";
    if (key !== API_KEY) {
        return res.status(401).json({ ok: false, error: "Unauthorized" });
    }
    next();
}

// ── Función de apertura serie ─────────────────────────────────────────────────
function openDrawerSerial(portPath) {
    return new Promise((resolve, reject) => {
        const port = new SerialPort({ path: portPath, baudRate: 9600, autoOpen: false });
        port.open((err) => {
            if (err) return reject(err);
            port.write(OPEN_DRAWER_CMD, (writeErr) => {
                port.close();
                if (writeErr) return reject(writeErr);
                resolve();
            });
        });
    });
}

function sendRawSerial(portPath, rawBytes) {
    return new Promise((resolve, reject) => {
        const port = new SerialPort({ path: portPath, baudRate: 9600, autoOpen: false });
        port.open((err) => {
            if (err) return reject(err);
            port.write(rawBytes, (writeErr) => {
                port.close();
                if (writeErr) return reject(writeErr);
                resolve();
            });
        });
    });
}

function getPrinterPort(printer) {
    let portPath = PRINTER_PORTS[printer];
    if (!portPath) {
        const fallback = Object.values(PRINTER_PORTS)[0];
        if (!fallback) {
            throw new Error(`Impresora '${printer}' no configurada en el bridge`);
        }
        console.warn(`[bridge] Impresora '${printer}' no encontrada, usando: ${fallback}`);
        portPath = fallback;
    }
    return portPath;
}

// ── Endpoints ─────────────────────────────────────────────────────────────────

app.get("/health", (req, res) => {
    res.json({ status: "ok" });
});

app.get("/open-drawer", checkApiKey, async (req, res) => {
    const printer = (req.query.printer || "").trim();
    console.log(`[bridge] Solicitud de apertura — impresora: "${printer}"`);

    let portPath;
    try {
        portPath = getPrinterPort(printer);
    } catch (err) {
        return res.status(404).json({ ok: false, error: err.message });
    }

    try {
        await openDrawerSerial(portPath);
        res.json({ ok: true });
    } catch (err) {
        console.error(`[bridge] Error abriendo cajón en ${portPath}:`, err.message);
        res.status(500).json({ ok: false, error: err.message });
    }
});

app.post("/print-raw", checkApiKey, async (req, res) => {
    const printer = String(req.body?.printer || "").trim();
    const hexBytes = String(req.body?.hex_bytes || "").trim();
    console.log(`[bridge] Solicitud de impresion RAW — impresora: "${printer}"`);

    if (!hexBytes) {
        return res.status(400).json({ ok: false, error: "Falta el campo hex_bytes" });
    }

    let portPath;
    try {
        portPath = getPrinterPort(printer);
    } catch (err) {
        return res.status(404).json({ ok: false, error: err.message });
    }

    try {
        const rawBytes = Buffer.from(
            hexBytes.split(",").map((item) => parseInt(item.trim(), 16))
        );
        await sendRawSerial(portPath, rawBytes);
        res.json({ ok: true, printer, bytesSent: rawBytes.length });
    } catch (err) {
        console.error(`[bridge] Error imprimiendo RAW en ${portPath}:`, err.message);
        res.status(500).json({ ok: false, error: err.message });
    }
});

// ── Arranque ──────────────────────────────────────────────────────────────────
app.listen(BRIDGE_PORT, "0.0.0.0", () => {
    console.log(`[bridge] Escuchando en http://0.0.0.0:${BRIDGE_PORT}`);
    console.log(`[bridge] API_KEY: ${API_KEY ? "configurada" : "sin autenticación"}`);
    console.log(`[bridge] Impresoras:`, PRINTER_PORTS);
});
