# -*- coding: utf-8 -*-
import socket
import time
import re

try:
    import serial  # pyserial
except Exception:
    serial = None


class MatrixScaleClient:
    """
    Cliente para indicador Matrix II en modo DEMAND.
    Soporta:
      - TCP (conversor TCP<->RS a IP:PUERTO)
      - Serie local (USB-RS232) si se instala pyserial
    Comando por defecto: PF16 (devuelve estado + modo + valor + unidad)
    TERMINATION debe coincidir con el configurado en el equipo: CR (\r) o CRLF (\r\n).
    """
    def __init__(
        self,
        mode="tcp",
        host="192.168.1.50",
        port=4001,
        serial_port="/dev/ttyUSB0",
        baudrate=9600,
        bytesize=8,
        parity="N",
        stopbits=1,
        terminator="\r",
        command="PF16",
        timeout=2.0,
        retries=1,
    ):
        self.mode = mode
        self.host = host
        self.port = port
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.terminator = terminator
        self.command = command
        self.timeout = timeout
        self.retries = retries

    def read_weight(self):
        last_exc = None
        for _ in range(self.retries + 1):
            try:
                line = self._ask(self.command)
                parsed = self._parse_line(line)
                return parsed
            except Exception as e:
                last_exc = e
                time.sleep(0.1)
        raise last_exc or Exception("No se pudo leer peso")

    def _ask(self, cmd):
        if self.mode == "tcp":
            return self._ask_tcp(cmd)
        elif self.mode == "serial":
            return self._ask_serial(cmd)
        else:
            raise ValueError("Modo no soportado: %s" % self.mode)

    def _ask_tcp(self, cmd):
        buf = b""
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.sendall((cmd + self.terminator).encode("latin1"))
            s.settimeout(self.timeout)
            end = self.terminator.encode("latin1")
            while True:
                chunk = s.recv(1024)
                if not chunk:
                    break
                buf += chunk
                if end in buf:
                    break
        line = buf.split(self.terminator.encode("latin1"))[0].decode("latin1", errors="ignore")
        line = line.replace("\x02", "")
        return line.strip()

    def _ask_serial(self, cmd):
        if serial is None:
            raise RuntimeError("pyserial no instalado. Instala 'pyserial' para usar modo serie.")
        parity_map = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}
        stop_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}
        with serial.Serial(
            port=self.serial_port,
            baudrate=self.baudrate,
            bytesize=self.bytesize,
            parity=parity_map.get(self.parity, serial.PARITY_NONE),
            stopbits=stop_map.get(self.stopbits, serial.STOPBITS_ONE),
            timeout=self.timeout,
            write_timeout=self.timeout,
        ) as ser:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.write((cmd + self.terminator).encode("latin1"))
            line = self._read_until(ser, self.terminator.encode("latin1"), self.timeout)
            line = line.decode("latin1", errors="ignore").replace("\x02", "")
            return line.strip()

    @staticmethod
    def _read_until(ser, terminator, timeout):
        buf = b""
        end_time = time.time() + timeout
        while time.time() < end_time:
            b = ser.read(1)
            if b:
                buf += b
                if buf.endswith(terminator):
                    break
            else:
                time.sleep(0.01)
        return buf

    def _parse_line(self, line):
        raw = line.strip()
        m = re.match(r"^(S|N)\s+(GS|NT)\s+([+\-]?\d+(?:[.,]\d+)?)\s+([A-Za-z]+)$", raw)
        if m:
            stable = m.group(1) == "S"
            mode = m.group(2)
            value = float(m.group(3).replace(",", "."))
            unit = m.group(4)
            return {"stable": stable, "mode": mode, "value": value, "unit": unit, "raw": raw}

        m2 = re.match(r"^(S|N)\s+(\d+)$", raw)
        if m2:
            stable = m2.group(1) == "S"
            digits = m2.group(2)
            return {"stable": stable, "mode": None, "value": float(digits), "unit": None, "raw": raw}

        return {"stable": None, "mode": None, "value": None, "unit": None, "raw": raw}