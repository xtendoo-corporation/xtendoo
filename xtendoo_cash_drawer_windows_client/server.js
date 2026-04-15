const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { spawn } = require('child_process');

const baseDir = process.pkg ? path.dirname(process.execPath) : __dirname;
const logsDir = path.join(baseDir, 'logs');

if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

const serviceLogPath = path.join(logsDir, 'service.log');
let requestCounter = 0;

function safeSerialize(value) {
  try {
    return JSON.stringify(value);
  } catch {
    return '[unserializable]';
  }
}

function appendLogLine(level, message, meta) {
  const ts = new Date().toISOString();
  const suffix = meta ? ` ${safeSerialize(meta)}` : '';
  const line = `[${ts}] [${level}] ${message}${suffix}`;

  try {
    fs.appendFileSync(serviceLogPath, line + '\n', 'utf8');
  } catch (error) {
    console.error(`[LOGGER] No se pudo escribir en ${serviceLogPath}: ${error.message}`);
  }

  if (level === 'ERROR') {
    console.error(line);
    return;
  }

  if (level === 'WARN') {
    console.warn(line);
    return;
  }

  console.log(line);
}

function logInfo(message, meta) {
  appendLogLine('INFO', message, meta);
}

function logWarn(message, meta) {
  appendLogLine('WARN', message, meta);
}

function logError(message, meta) {
  appendLogLine('ERROR', message, meta);
}

function maskApiKey(value) {
  if (!value) {
    return undefined;
  }

  const key = String(value);
  return key.length > 4 ? `${key.slice(0, 4)}****` : '****';
}

function sanitizeQuery(query) {
  const sanitized = { ...query };

  if (sanitized.api_key) {
    sanitized.api_key = maskApiKey(sanitized.api_key);
  }

  if (sanitized.apikey) {
    sanitized.apikey = maskApiKey(sanitized.apikey);
  }

  return sanitized;
}

function getClientIp(req) {
  return req.ip || req.socket.remoteAddress || '-';
}

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
  logError('Falta API_KEY en .env', { envPath: path.join(baseDir, '.env') });
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
  const requestId = ++requestCounter;
  const startedAt = Date.now();

  req.requestId = requestId;

  logInfo('Peticion recibida', {
    requestId,
    method: req.method,
    url: req.originalUrl || req.url,
    ip: getClientIp(req),
    origin: req.headers.origin || null,
    userAgent: req.headers['user-agent'] || null,
    query: sanitizeQuery(req.query || {})
  });

  res.on('finish', () => {
    const ms = Date.now() - startedAt;
    logInfo('Peticion completada', {
      requestId,
      method: req.method,
      url: req.originalUrl || req.url,
      status: res.statusCode,
      durationMs: ms,
      ip: getClientIp(req)
    });
  });

  next();
});

function validateApiKey(req, res, next) {
  const apiKey =
    req.header('x-api-key') ||
    req.query.api_key ||
    req.query.apikey;

  if (!apiKey || apiKey !== API_KEY) {
    logWarn('API key invalida', {
      requestId: req.requestId,
      ip: getClientIp(req),
      origin: req.headers.origin || null,
      received: maskApiKey(apiKey)
    });

    return res.status(401).json({
      ok: false,
      error: 'API key invalida'
    });
  }

  logInfo('API key validada', {
    requestId: req.requestId,
    ip: getClientIp(req)
  });

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

    logInfo('Lanzando PowerShell para abrir cajon', {
      printerName: printerName || null,
      scriptPath,
      command: 'powershell.exe',
      args
    });

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
      logError('Fallo al lanzar PowerShell', {
        printerName: printerName || null,
        error: err.message
      });
      reject(err);
    });

    child.on('close', (code) => {
      logInfo('PowerShell finalizado', {
        printerName: printerName || null,
        exitCode: code,
        stdout: stdout.trim() || null,
        stderr: stderr.trim() || null
      });

      if (code !== 0) {
        return reject(new Error((stderr || `PowerShell termino con codigo ${code}`).trim()));
      }

      try {
        const parsed = JSON.parse(stdout.trim());
        logInfo('Cajon abierto correctamente', {
          printerName: parsed.printer,
          bytesSent: parsed.bytesSent
        });
        resolve(parsed);
      } catch (e) {
        logError('Salida invalida de PowerShell', {
          printerName: printerName || null,
          stdout: stdout.trim() || null,
          error: e.message
        });
        reject(new Error(`Salida invalida de PowerShell: ${stdout}`));
      }
    });
  });
}

app.get('/ping', (req, res) => {
  logInfo('Ping solicitado', { requestId: req.requestId, ip: getClientIp(req) });
  res.status(200).send('OK');
});

app.get('/health', (req, res) => {
  logInfo('Health solicitado', { requestId: req.requestId, ip: getClientIp(req) });
  res.status(200).json({ status: 'ok' });
});

app.get('/open-drawer', validateApiKey, async (req, res) => {
  try {
    const requestedPrinter = req.query.printer || DEFAULT_PRINTER || '';
    logInfo('Solicitud de apertura de cajon', {
      requestId: req.requestId,
      requestedPrinter: requestedPrinter || '(predeterminada del sistema)'
    });

    const result = await sendDrawerPulse(requestedPrinter);

    return res.status(200).json({
      ok: true,
      message: 'Comando enviado correctamente',
      printer: result.printer,
      bytesSent: result.bytesSent
    });
  } catch (error) {
    logError('Error al abrir cajon', {
      requestId: req.requestId,
      requestedPrinter: req.query.printer || DEFAULT_PRINTER || null,
      error: error.message || 'Error desconocido'
    });

    return res.status(500).json({
      ok: false,
      error: error.message || 'Error enviando comando RAW'
    });
  }
});

app.use((req, res) => {
  logWarn('Ruta no encontrada', {
    requestId: req.requestId,
    method: req.method,
    url: req.originalUrl || req.url,
    ip: getClientIp(req)
  });

  res.status(404).json({
    ok: false,
    error: 'Ruta no encontrada'
  });
});

app.use((err, req, res, next) => {
  const statusCode = err && err.message && err.message.startsWith('CORS:') ? 403 : 500;

  if (statusCode === 403) {
    logWarn('Peticion bloqueada por CORS', {
      requestId: req && req.requestId,
      method: req && req.method,
      url: req && (req.originalUrl || req.url),
      ip: req && getClientIp(req),
      origin: req && req.headers ? req.headers.origin || null : null,
      error: err.message
    });
  } else {
    logError('Error no controlado en middleware HTTP', {
      requestId: req && req.requestId,
      method: req && req.method,
      url: req && (req.originalUrl || req.url),
      ip: req && getClientIp(req),
      error: err && err.message,
      stack: err && err.stack
    });
  }

  if (res.headersSent) {
    return next(err);
  }

  return res.status(statusCode).json({
    ok: false,
    error: statusCode === 403 ? 'Origen no permitido por CORS' : 'Error interno del servicio'
  });
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
  console.log(`  LogFile    : ${serviceLogPath}`);
  console.log('------------------------------------------------------------');
  console.log(`  GET ${url}/ping`);
  console.log(`  GET ${url}/open-drawer?api_key=<KEY>[&printer=<NOMBRE>]`);
  console.log('============================================================');
  console.log('');

  logInfo('Servicio iniciado', {
    protocol: proto,
    host: HOST,
    port: PORT,
    printerName,
    defaultPrinter: DEFAULT_PRINTER || '(impresora del sistema)',
    origins: ALLOWED_ORIGINS,
    baseDir,
    logFile: serviceLogPath,
    mode
  });
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
      logInfo('Certificados SSL detectados', {
        keyPath: CERT_KEY_PATH,
        certPath: CERT_CERT_PATH
      });
    } else {
      logWarn('Rutas de certificado en .env no encontradas. Arrancando en HTTP.', {
        keyPath: CERT_KEY_PATH,
        certPath: CERT_CERT_PATH
      });
    }
  }

  // Siempre levantar HTTP (para Odoo backend Python y herramientas internas)
  http.createServer(app).listen(PORT, HOST, () => {
    printBanner('http', printerName);
    if (!hasCerts) {
      logWarn('Sin certificados SSL. El navegador (Odoo cloud) bloqueara las peticiones.');
      logWarn('Ejecuta install.ps1 para configurar mkcert y HTTPS local.');
      console.log('');
    }
  });

  // Si hay certs, levantar HTTPS tambien en PORT+1 (para navegador desde Odoo cloud)
  if (hasCerts) {
    const HTTPS_PORT = PORT + 1;
    https.createServer(sslOpts, app).listen(HTTPS_PORT, HOST, () => {
      const url = `https://${HOST === '0.0.0.0' ? '192.168.18.7' : HOST}:${HTTPS_PORT}`;
      logInfo('HTTPS habilitado', {
        url,
        host: HOST,
        port: HTTPS_PORT
      });
    });
  }
}

process.on('uncaughtException', (error) => {
  logError('uncaughtException', {
    error: error.message,
    stack: error.stack
  });
});

process.on('unhandledRejection', (reason) => {
  logError('unhandledRejection', {
    reason: reason instanceof Error ? { message: reason.message, stack: reason.stack } : reason
  });
});

// Solo arrancar automaticamente si este fichero es el punto de entrada
if (require.main === module) {
  startServer();
}

module.exports = { startServer, app, PORT, HOST };
