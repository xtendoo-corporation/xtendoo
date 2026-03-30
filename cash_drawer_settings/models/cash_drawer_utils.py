# -*- coding: utf-8 -*-
"""
Utility functions for the Cash Drawer Settings module.

Provides helpers to:
- Parse ESC/POS command byte strings
- Open a cash drawer via TCP network or local device
- Detect Docker network gateway
"""
import os
import re
import socket
import subprocess

# Default ESC/POS command: ESC p (pin 2, duration 25/250 ms)
CASH_DRAWER_COMMAND = bytes([0x1B, 0x70, 0x00, 0x19, 0xFA])

# Matches "host:port" or "ip:port" but NOT device paths like /dev/usb/lp0
TCP_RE = re.compile(r"^([^/:]+):(\d+)$")


def parse_command_bytes(command_str):
    """Parse a space-separated string of decimal byte values into bytes.

    If *command_str* is empty or None the default :data:`CASH_DRAWER_COMMAND`
    is returned.

    :param command_str: e.g. ``"27 112 0 25 250"``
    :returns: :class:`bytes`
    :raises ValueError: if any token is not a valid integer in range 0–255.
    """
    if not command_str:
        return CASH_DRAWER_COMMAND

    result = []
    for token in command_str.split():
        value = int(token)  # raises ValueError for non-integer tokens
        if value < 0 or value > 255:
            raise ValueError(
                "Byte value out of range (0-255): %d" % value
            )
        result.append(value)
    return bytes(result)


def open_cash_drawer(printer, command_bytes_str=None):
    """Send the cash-drawer pulse to *printer*.

    Supports two strategies:

    TCP
        If *printer* matches ``host:port`` (e.g. ``192.168.1.50:9100``) a raw
        TCP connection is opened and the command bytes are sent directly.

    Local device
        Otherwise *printer* is treated as a local path (e.g. ``/dev/usb/lp0``)
        or a CUPS printer name.  The function first attempts ``lp -d printer``
        and, if that fails, writes directly to the device path.

    :param printer: Printer address — ``host:port`` or device path.
    :param command_bytes_str: Space-separated decimal bytes (optional).
    :returns: ``True`` on success.
    :raises RuntimeError: on any failure.
    """
    command = parse_command_bytes(command_bytes_str)

    m = TCP_RE.match(printer)
    if m:
        host = m.group(1)
        port = int(m.group(2))
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                sock.sendall(command)
            return True
        except OSError as exc:
            raise RuntimeError(str(exc)) from exc

    # Local device / CUPS strategy
    # Try lp first (works with CUPS-managed printers)
    lp_result = subprocess.run(
        ["lp", "-d", printer, "-"],
        input=command,
        capture_output=True,
        timeout=10,
    )
    if lp_result.returncode == 0:
        return True

    # Fall back to direct device write
    if not os.path.exists(printer):
        raise RuntimeError(
            "Device not found and lp command failed for: %s" % printer
        )

    with open(printer, "wb") as fh:
        fh.write(command)
    return True


def get_docker_gateway():
    """Return the Docker bridge gateway IP address, or ``None``.

    Useful for reaching the host machine from inside a Docker container.
    Parses the output of ``ip route`` looking for the default gateway.

    :returns: IP address string or ``None``.
    """
    try:
        result = subprocess.run(
            ["ip", "route"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if "default via" in line:
                parts = line.split()
                idx = parts.index("via")
                return parts[idx + 1]
        return None
    except Exception:
        return None
