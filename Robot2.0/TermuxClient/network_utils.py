# client/network_utils.py
# ====================================
# Funciones de red para comunicar con el servidor
# ====================================

import socket
import struct
import os
import traceback
from .config import (
    SERVER_HOST, SERVER_PORT,
    CONNECT_TIMEOUT_S, SEND_TIMEOUT_S, RECV_TIMEOUT_S,
    BUFFER_SIZE,
    debug_enabled,
)

def send_audio_and_get_reply(audio_path: str, save_path: str) -> bool:
    """
    Envía un archivo WAV al servidor y recibe la respuesta (también WAV).
    Devuelve True si todo fue bien, False en caso de error.
    """
    sock = None
    try:
        filesize = os.path.getsize(audio_path)
        if debug_enabled():
            print(f"[NET] Conectando con {SERVER_HOST}:{SERVER_PORT} (archivo {filesize} bytes)…")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CONNECT_TIMEOUT_S)

        # 1) CONEXIÓN
        sock.connect((SERVER_HOST, SERVER_PORT))
        if debug_enabled():
            print("[NET] Conectado.")

        # 2) ENVÍO CABECERA (tamaño)
        sock.settimeout(SEND_TIMEOUT_S)
        hdr = struct.pack("!Q", filesize)
        sock.sendall(hdr)
        if debug_enabled():
            print(f"[NET] Cabecera enviada ({len(hdr)} bytes). Enviando datos…")

        # 3) ENVÍO DATOS
        with open(audio_path, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                sock.sendall(chunk)
        if debug_enabled():
            print("[NET] Audio enviado. Esperando respuesta…")

        # 4) RECEPCIÓN CABECERA RESPUESTA
        sock.settimeout(RECV_TIMEOUT_S)
        raw_size = recvall(sock, 8)
        if not raw_size:
            print("[NET] No se recibió tamaño de respuesta (conexión cerrada).")
            return False
        resp_size = struct.unpack("!Q", raw_size)[0]
        if debug_enabled():
            print(f"[NET] Tamaño de respuesta: {resp_size} bytes")

        # 5) RECEPCIÓN DATOS RESPUESTA
        with open(save_path, "wb") as f:
            bytes_recv = 0
            while bytes_recv < resp_size:
                chunk = sock.recv(min(BUFFER_SIZE, resp_size - bytes_recv))
                if not chunk:
                    break
                f.write(chunk)
                bytes_recv += len(chunk)

        if bytes_recv != resp_size:
            print(f"[NET] Respuesta incompleta: {bytes_recv}/{resp_size} bytes")
            return False

        if debug_enabled():
            print(f"[NET] Respuesta recibida y guardada en {save_path}")
        return True

    except Exception as e:
        print("[NET] Error en comunicación:", e)
        if debug_enabled():
            traceback.print_exc()
        return False
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass


def recvall(sock: socket.socket, n: int) -> bytes:
    """Lee exactamente n bytes del socket o devuelve None si falla."""
    data = b""
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data
