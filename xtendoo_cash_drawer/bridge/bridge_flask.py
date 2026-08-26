"""
Bridge local para apertura de cajón portamonedas — Python Flask
================================================================
Instala las dependencias:
    pip install flask flask-cors pyserial escpos

Arranca el bridge:
    python bridge_flask.py

El bridge escucha en http://0.0.0.0:3211 y abre el cajón enviando
el comando ESC/POS de apertura de cajón (ESC p 0 25 250) a la
impresora configurada.

Configuración:
    - PRINTER_NAME : nombre de la impresora (igual que en Odoo)
    - PRINTER_PORT : puerto serie, p.ej. /dev/ttyUSB0 o COM3
    - API_KEY      : clave de autenticación (vacío = sin auth)
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cash_drawer_bridge")

app = Flask(__name__)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Permite peticiones desde cualquier origen (necesario para Odoo cloud → bridge LAN)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["x-api-key", "Content-Type"],
    methods=["GET", "POST", "OPTIONS"],
)

# ── Configuración ─────────────────────────────────────────────────────────────
API_KEY = os.environ.get("BRIDGE_API_KEY", "")  # vacío = sin autenticación
PORT = int(os.environ.get("BRIDGE_PORT", "3211"))

# Mapa nombre_impresora → puerto serie.
# Añade tantas entradas como impresoras tengas.
PRINTER_PORTS = {
    "POS-80C": os.environ.get("PRINTER_PORT", "/dev/ttyUSB0"),
    "EPSON": os.environ.get("PRINTER_PORT_EPSON", "/dev/ttyUSB0"),
    # "STAR": "COM3",
}

# Comando ESC/POS de apertura de cajón (estándar).
# ESC p <pin> <on-time> <off-time>
OPEN_DRAWER_CMD = bytes([0x1B, 0x70, 0x00, 0x19, 0xFA])


def _check_api_key():
    """Devuelve None si la auth es correcta, o una respuesta de error."""
    if not API_KEY:
        return None  # sin auth configurada
    key = request.headers.get("x-api-key", "")
    if key != API_KEY:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    return None


def _open_drawer_serial(port: str) -> dict:
    """Envía el comando de apertura al puerto serie."""
    try:
        import serial  # pyserial
        with serial.Serial(port, baudrate=9600, timeout=2) as ser:
            ser.write(OPEN_DRAWER_CMD)
        logger.info("Cajón abierto vía serie en %s", port)
        return {"ok": True}
    except ImportError:
        return {"ok": False, "error": "pyserial no instalado. Ejecuta: pip install pyserial"}
    except Exception as exc:
        logger.error("Error abriendo cajón en %s: %s", port, exc)
        return {"ok": False, "error": str(exc)}


def _send_raw_serial(port: str, raw_bytes: bytes) -> dict:
    """Envía bytes RAW a la impresora serie."""
    try:
        import serial  # pyserial

        with serial.Serial(port, baudrate=9600, timeout=2) as ser:
            ser.write(raw_bytes)
        logger.info("Trabajo RAW enviado vía serie en %s", port)
        return {"ok": True, "bytesSent": len(raw_bytes)}
    except ImportError:
        return {
            "ok": False,
            "error": "pyserial no instalado. Ejecuta: pip install pyserial",
        }
    except Exception as exc:
        logger.error("Error enviando bytes RAW en %s: %s", port, exc)
        return {"ok": False, "error": str(exc)}


def _resolve_printer_port(printer: str):
    port = PRINTER_PORTS.get(printer)
    if not port:
        port = next(iter(PRINTER_PORTS.values()), None)
        if not port:
            return None, (
                jsonify(
                    {
                        "ok": False,
                        "error": f"Impresora '{printer}' no configurada en el bridge",
                    }
                ),
                404,
            )
        logger.warning(
            "Impresora '%s' no encontrada, usando puerto por defecto: %s",
            printer,
            port,
        )
    return port, None


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    return jsonify({"status": "ok"})


@app.route("/open-drawer", methods=["GET", "OPTIONS"])
def open_drawer():
    # El preflight OPTIONS no lleva auth, debe responder siempre 200
    if request.method == "OPTIONS":
        return "", 200

    auth_error = _check_api_key()
    if auth_error:
        return auth_error

    printer = request.args.get("printer", "").strip()
    logger.info("Solicitud de apertura — impresora: %r", printer)

    port, error_response = _resolve_printer_port(printer)
    if error_response:
        return error_response

    result = _open_drawer_serial(port)
    status = 200 if result["ok"] else 500
    return jsonify(result), status


@app.route("/print-raw", methods=["POST", "OPTIONS"])
def print_raw():
    if request.method == "OPTIONS":
        return "", 200

    auth_error = _check_api_key()
    if auth_error:
        return auth_error

    payload = request.get_json(silent=True) or {}
    printer = str(payload.get("printer", "")).strip()
    hex_bytes = str(payload.get("hex_bytes", "")).strip()
    if not hex_bytes:
        return jsonify({"ok": False, "error": "Falta el campo hex_bytes"}), 400

    port, error_response = _resolve_printer_port(printer)
    if error_response:
        return error_response

    try:
        raw_bytes = bytes(int(chunk.strip(), 16) for chunk in hex_bytes.split(",") if chunk.strip())
    except ValueError:
        return jsonify({"ok": False, "error": "hex_bytes contiene valores no válidos"}), 400

    result = _send_raw_serial(port, raw_bytes)
    status = 200 if result["ok"] else 500
    return jsonify(result), status


if __name__ == "__main__":
    logger.info("Bridge del cajón iniciando en http://0.0.0.0:%d", PORT)
    logger.info("API_KEY: %s", "configurada" if API_KEY else "sin autenticación")
    logger.info("Impresoras configuradas: %s", list(PRINTER_PORTS.keys()))
    app.run(host="0.0.0.0", port=PORT, debug=False)
