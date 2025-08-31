# server/utils_net.py
# ====================================
# Utilidades de red para el servidor (socket TCP)
# ====================================

from __future__ import annotations

import os
import socket
import struct

try:
    # cuando se ejecuta como paquete: python -m server.main
    from .config import BUFFER_SIZE, RECV_TIMEOUT_S, SEND_TIMEOUT_S, debug_enabled
except ImportError:
    # cuando se ejecuta como script: python server/main.py
    from config import BUFFER_SIZE, RECV_TIMEOUT_S, SEND_TIMEOUT_S, debug_enabled

HEADER_FMT = "!Q"  # uint64 big-endian (coincide con el cliente)

def recvall(sock: socket.socket, n: int) -> bytes | None:
    """Lee exactamente n bytes del socket o devuelve None si la conexión se corta."""
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def receive_file(sock: socket.socket, out_path: str) -> bool:
    """
    Recibe un archivo desde 'sock' y lo guarda en 'out_path'.
    Protocolo: primero 8 bytes de tamaño, luego 'size' bytes de datos.
    """
    try:
        sock.settimeout(RECV_TIMEOUT_S)

        # 1) Encabezado: tamaño
        raw = recvall(sock, struct.calcsize(HEADER_FMT))
        if not raw:
            if debug_enabled():
                print("[NET] No llegó el encabezado de tamaño.")
            return False
        total_size = struct.unpack(HEADER_FMT, raw)[0]
        if debug_enabled():
            print(f"[NET] Tamaño entrante: {total_size} bytes -> {out_path}")

        # 2) Datos
        bytes_recv = 0
        with open(out_path, "wb") as f:
            while bytes_recv < total_size:
                chunk = sock.recv(min(BUFFER_SIZE, total_size - bytes_recv))
                if not chunk:
                    break
                f.write(chunk)
                bytes_recv += len(chunk)

        ok = (bytes_recv == total_size)
        if debug_enabled():
            print(f"[NET] Archivo recibido: {bytes_recv}/{total_size} bytes (ok={ok})")
        return ok

    except Exception as e:
        print("[NET] Error recibiendo archivo:", e)
        return False

def send_file(sock: socket.socket, path: str) -> bool:
    """
    Envía el archivo 'path' por 'sock' usando el mismo protocolo (8 bytes tamaño + datos).
    """
    try:
        if not os.path.exists(path):
            print(f"[NET] Archivo no existe: {path}")
            return False

        size = os.path.getsize(path)
        if debug_enabled():
            print(f"[NET] Enviando {path} ({size} bytes)…")

        sock.settimeout(SEND_TIMEOUT_S)

        # 1) Encabezado: tamaño
        sock.sendall(struct.pack(HEADER_FMT, size))

        # 2) Datos en bloques
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
                sock.sendall(chunk)

        if debug_enabled():
            print("[NET] Envío completado.")
        return True

    except Exception as e:
        print("[NET] Error enviando archivo:", e)
        return False
