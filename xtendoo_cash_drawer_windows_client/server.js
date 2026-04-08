const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { spawn } = require('child_process');

const baseDir = process.pkg ? path.dirname(process.execPath) : __dirname;

// Cargar .env desde la carpeta del .exe o desde la carpeta del proyecto
dotenv.config({ path: path.join(baseDir, '.env') });

const app = express();

const PORT = parseInt(process.env.PORT || '3210', 10);
const HOST = process.env.HOST || '127.0.0.1';
const API_KEY = process.env.API_KEY || '';
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || '')
  .split(',')
  .map(s => s.trim())
  .filter(Boolean);
const CERT_KEY_PATH = process.env.CERT_KEY ? path.join(baseDir, process.env.CERT_KEY) : null;
const CERT_CERT_PATH = process.env.CERT_CERT ? path.join(baseDir, process.env.CERT_CERT) : null;
const DEFAULT_PRINTER = process.env.DEFAULT_PRINTER || '';

if (!API_KEY) {
  console.error('[ERROR] Falta API_KEY en .env');
  process.exit(1);
}

// --- CORS ---
const corsOptions = {
  origin: function (origin, callback) {
    // Permitir peticiones sin origin (ej: curl, Postman)
    if (!origin) return callback(null, true);
    if (ALLOWED_ORIGINS.length === 0 || ALLOWED_ORIGINS.includes(origin)) {
      return callback(null, true);
    }
    return callback(new Error('CORS: origen no permitido: ' + origin));
  },
  methods: ['GET', 'OPTIONS'],
  allowedHeaders: ['x-api-key', 'Content-Type'],
  optionsSuccessStatus: 204
};

app.use(cors(corsOptions));

// Chrome Private Network Access: necesario para HTTPS publico -> 127.0.0.1
app.options('*', (req, res) => {
  if (req.headers['access-control-request-private-network']) {
    res.setHeader('Access-Control-Allow-Private-Network', 'true');
  }
  res.status(204).send('');
});

// --- Logging de peticiones ---
app.use((req, res, next) => {
  const startedAt = Date.now();
  res.on('finish', () => {
    const ms = Date.now() - startedAt;
    const ts = new Date().toISOString();
    const url = req.url;
    const method = req.method;
    const status = res.statusCode;
    const ip = req.ip || req.socket.remoteAddress || '-';
    console.log(`[${ts}] ${method} ${url} <- ${ip} -> ${status} (${ms}ms)`);
  });
  next();
});

function validateApiKey(req, res, next) {
  const apiKey =
    req.header('x-api-key') ||
    req.query.api_key ||
    req.query.apikey;

  if (!apiKey || apiKey !== API_KEY) {
    return res.status(401).json({
      ok: false,
      error: 'API key invalida'
    });
  }

  next();
}

function getPowerShellScriptPath() {
  const scriptPath = path.join(baseDir, 'send-raw.ps1');

  if (!fs.existsSync(scriptPath)) {
    throw new Error(`No se encontro send-raw.ps1 en: ${scriptPath}`);
  }

  return scriptPath;
}

function sendDrawerPulse(printerName) {
  return new Promise((resolve, reject) => {
    let scriptPath;

    try {
      scriptPath = getPowerShellScriptPath();
    } catch (err) {
      return reject(err);
    }

    // ESC p m t1 t2
    // 1B 70 00 19 FA
    const hexBytes = '1B,70,00,19,FA';

    const args = [
      '-NoProfile',
      '-ExecutionPolicy', 'Bypass',
      '-File', scriptPath,
      '-HexBytes', hexBytes
    ];

    if (printerName && String(printerName).trim()) {
      args.push('-PrinterName', String(printerName).trim());
    }

    const child = spawn('powershell.exe', args, {
      windowsHide: true
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('error', (err) => {
      reject(err);
    });

    child.on('close', (code) => {
      if (code !== 0) {
        return reject(new Error((stderr || `PowerShell termino con codigo ${code}`).trim()));
      }

      try {
        const parsed = JSON.parse(stdout.trim());
        resolve(parsed);
      } catch (e) {
        reject(new Error(`Salida invalida de PowerShell: ${stdout}`));
      }
    });
  });
}

app.get('/ping', (req, res) => {
  res.status(200).send('OK');
});

app.get('/open-drawer', validateApiKey, async (req, res) => {
  try {
    const requestedPrinter = req.query.printer || DEFAULT_PRINTER || '';
    const result = await sendDrawerPulse(requestedPrinter);

    return res.status(200).json({
      ok: true,
      message: 'Comando enviado correctamente',
      printer: result.printer,
      bytesSent: result.bytesSent
    });
  } catch (error) {
    return res.status(500).json({
      ok: false,
      error: error.message || 'Error enviando comando RAW'
    });
  }
});

function getDefaultPrinterName() {
  return new Promise((resolve) => {
    const ps = spawn('powershell.exe', [
      '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
      "(Get-CimInstance Win32_Printer | Where-Object { $_.Default -eq $true }).Name"
    ], { windowsHide: true });
    let out = '';
    ps.stdout.on('data', d => { out += d.toString(); });
    ps.on('close', () => resolve(out.trim() || '(no configurada)'));
    ps.on('error', () => resolve('(no disponible)'));
  });
}

function printBanner(proto, printerName) {
  const pkg = (() => { try { return require('./package.json'); } catch { return { name: 'impresora-service', version: '?' }; } })();
  const mode = process.pkg ? '[EXE]' : '[DEV]';
  const maskedKey = API_KEY.length > 4 ? API_KEY.slice(0, 4) + '****' : '****';
  const originsStr = ALLOWED_ORIGINS.length > 0 ? ALLOWED_ORIGINS.join(', ') : '(cualquiera)';
  const url = `${proto}://${HOST}:${PORT}`;

  console.log('');
  console.log('============================================================');
  console.log(`  ${pkg.name}  v${pkg.version}  ${mode}`);
  console.log('============================================================');
  console.log(`  URL        : ${url}`);
  console.log(`  API_KEY    : ${maskedKey}`);
  console.log(`  Impresora  : ${printerName}`);
  console.log(`  Def.Printer: ${DEFAULT_PRINTER || '(impresora del sistema)'}`);
  console.log(`  CORS       : ${originsStr}`);
  console.log(`  BaseDir    : ${baseDir}`);
  console.log('------------------------------------------------------------');
  console.log(`  GET ${url}/ping`);
  console.log(`  GET ${url}/open-drawer?api_key=<KEY>[&printer=<NOMBRE>]`);
  console.log('============================================================');
  console.log('');
}

async function startServer() {
  const printerName = await getDefaultPrinterName();

  let hasCerts = false;
  let sslOpts = {};

  if (CERT_KEY_PATH && CERT_CERT_PATH) {
    if (fs.existsSync(CERT_KEY_PATH) && fs.existsSync(CERT_CERT_PATH)) {
      sslOpts = {
        key: fs.readFileSync(CERT_KEY_PATH),
        cert: fs.readFileSync(CERT_CERT_PATH)
      };
      hasCerts = true;
    } else {
      console.warn('[AVISO] Rutas de certificado en .env no encontradas. Arrancando en HTTP.');
    }
  }

  // Siempre levantar HTTP (para Odoo backend Python y herramientas internas)
  http.createServer(app).listen(PORT, HOST, () => {
    printBanner('http', printerName);
    if (!hasCerts) {
      console.warn('[AVISO] Sin certificados SSL. El navegador (Odoo cloud) bloqueara las peticiones.');
      console.warn('[AVISO] Ejecuta install.ps1 para configurar mkcert y HTTPS local.');
      console.log('');
    }
  });

  // Si hay certs, levantar HTTPS tambien en PORT+1 (para navegador desde Odoo cloud)
  if (hasCerts) {
    const HTTPS_PORT = PORT + 1;
    https.createServer(sslOpts, app).listen(HTTPS_PORT, HOST, () => {
      const url = `https://${HOST === '0.0.0.0' ? '192.168.18.7' : HOST}:${HTTPS_PORT}`;
      console.log(`[HTTPS] Tambien escuchando en ${url} (para navegador/Odoo cloud)`);
    });
  }
}

// Solo arrancar automaticamente si este fichero es el punto de entrada
if (require.main === module) {
  startServer();
}

module.exports = { startServer, app, PORT, HOST };