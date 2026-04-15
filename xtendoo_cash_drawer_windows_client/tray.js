'use strict';

const path = require('path');
const http = require('http');
const https = require('https');
const SysTray = require('systray2').default;

// Cuando corre como exe compilado, los assets estan junto al ejecutable
const baseDir = process.pkg ? path.dirname(process.execPath) : __dirname;

const ICON_GREEN = path.join(baseDir, 'icon-green.ico');
const ICON_RED   = path.join(baseDir, 'icon-red.ico');

// Iniciar el servidor Express (no auto-arranca por require.main !== module)
const { startServer, PORT, HOST } = require('./server.js');

// --- Utils ---
function pingServer() {
  return new Promise((resolve) => {
    const proto = process.env.CERT_KEY ? https : http;
    const opts = {
      hostname: HOST || '127.0.0.1',
      port: PORT || 3210,
      path: '/ping',
      method: 'GET',
      timeout: 2000,
      rejectUnauthorized: false   // cert local autofirmado con mkcert
    };
    const req = proto.request(opts, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.end();
  });
}

function openBrowser(url) {
  const { spawn } = require('child_process');
  spawn('cmd', ['/c', 'start', '', url], { windowsHide: true, detached: true }).unref();
}

// --- Menu ---
let itemStatus = {
  title: 'Iniciando...',
  tooltip: 'Comprobando estado del servicio',
  enabled: false,
  checked: false
};

let itemOpenBrowser = {
  title: 'Abrir en navegador',
  tooltip: 'Abre la URL del servicio en el navegador',
  enabled: true,
  checked: false
};

let itemExit = {
  title: 'Salir',
  tooltip: 'Cerrar el servicio y el icono de bandeja',
  enabled: true,
  checked: false
};

const systray = new SysTray({
  menu: {
    icon: ICON_RED,
    title: '',
    tooltip: 'Cash Drawer Service',
    items: [itemStatus, SysTray.separator, itemOpenBrowser, SysTray.separator, itemExit]
  },
  debug: false,
  copyDir: true   // copia el binario Go a %USERPROFILE%/.cache/node-systray (necesario en pkg)
});

let currentIcon = ICON_RED;

function setIcon(iconPath) {
  if (iconPath === currentIcon) return;
  currentIcon = iconPath;
  systray.sendAction({
    type: 'update-menu',
    menu: {
      icon: iconPath,
      title: '',
      tooltip: 'Cash Drawer Service',
      items: [itemStatus, SysTray.separator, itemOpenBrowser, SysTray.separator, itemExit]
    }
  });
}

// --- Clicks ---
systray.onClick((action) => {
  if (action.item === itemOpenBrowser || action.item.title === itemOpenBrowser.title) {
    const proto = process.env.CERT_KEY ? 'https' : 'http';
    openBrowser(`${proto}://${HOST || '127.0.0.1'}:${PORT || 3210}/ping`);
  }
  if (action.item === itemExit || action.item.title === itemExit.title) {
    systray.kill(true);
  }
});

// --- Health check loop ---
async function updateStatus() {
  const running = await pingServer();
  const proto = process.env.CERT_KEY ? 'https' : 'http';
  const url = `${proto}://${HOST || '127.0.0.1'}:${PORT || 3210}`;

  itemStatus.title   = running ? `Corriendo en ${url}` : 'Servicio no disponible';
  itemStatus.tooltip = running ? `Servicio activo en ${url}` : 'El servidor no responde';

  setIcon(running ? ICON_GREEN : ICON_RED);

  systray.sendAction({ type: 'update-item', item: itemStatus });
}

// --- Arrancar ---
systray.onReady(async () => {
  // Arrancar el servidor Express en el mismo proceso
  await startServer();

  // Primera comprobacion inmediata
  await updateStatus();

  // Comprobar cada 5 segundos
  setInterval(updateStatus, 5000);
});

systray.onError((err) => {
  console.error('[TRAY] Error:', err.message);
});

systray.onExit((code, signal) => {
  console.log(`[TRAY] Saliendo (code=${code}, signal=${signal})`);
  process.exit(0);
});
