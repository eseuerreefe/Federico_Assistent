# client/main.py
# ====================================
# Cliente del asistente de voz con toggle activo/inactivo (ENTER)
# ====================================

import os
import sys
import time
import platform

from .config import (
    RESPONSE_WAV, SERVER_HOST, SERVER_PORT,
    PRINT_LEVEL, debug_enabled, RECORDING_WAV
)
from . import audio_utils
from . import network_utils

# --- Tecla de toggle: ENTER (Windows y Linux/mac) ---
_TOGGLE_KEYS = ("\r", "\n")   # ENTER


def _size_or_zero(path: str) -> int:
    try:
        return os.path.getsize(path)
    except Exception:
        return 0


def _toggle_pressed() -> bool:
    """
    Devuelve True si se ha pulsado la tecla de toggle (ENTER).
    - En Windows usa msvcrt (no bloqueante).
    - En otros SO, comprueba stdin (requiere pulsar ENTER para enviar la línea).
    """
    try:
        if platform.system() == "Windows":
            import msvcrt
            if msvcrt.kbhit():
                ch = msvcrt.getwch()  # wide char
                # Limpia más teclas encadenadas rápidamente
                while msvcrt.kbhit():
                    _ = msvcrt.getwch()
                return ch in _TOGGLE_KEYS or ch == " "
            return False
        else:
            # POSIX: line-buffered; detectamos ENTER (devuelve línea)
            import select
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                line = sys.stdin.readline()
                return line.endswith("\n")
            return False
    except Exception:
        return False


def _process_one_turn() -> bool:
    """
    Captura 1 locución (con VAD), la envía al servidor y reproduce la respuesta.
    Devuelve True si todo fue bien; False si hubo error de red o la grabación salió vacía.
    """
    user_wav = RECORDING_WAV
    audio_utils.record_audio(user_wav, use_vad=True)

    size = _size_or_zero(user_wav)
    if size == 0:
        print("⚠️  Grabación vacía. Reintentando…\n")
        time.sleep(0.2)
        return False

    if debug_enabled():
        print(f"[🎛️] WAV capturado: {user_wav} ({size} bytes)")

    print("[NET] Enviando al servidor…")
    ok = network_utils.send_audio_and_get_reply(user_wav, RESPONSE_WAV)
    if not ok:
        print("⚠️  Error al comunicar con el servidor.\n")
        time.sleep(0.4)
        return False

    print("[Asistente] ▶ Reproduciendo respuesta…")
    audio_utils.play_audio_file(RESPONSE_WAV)
    print()  # separador visual
    return True


def main():
    print("=== Cliente Asistente de Voz ===")
    print(f"Servidor: {SERVER_HOST}:{SERVER_PORT}")
    print(f"Log level: {PRINT_LEVEL}")
    print("Pulsa Ctrl+C para salir.\n")

    # Arranca en INACTIVO
    active = False
    print("⏸️  Estado: INACTIVO. Pulsa ENTER para ACTIVAR la escucha.")

    try:
        last_toggle_ts = 0.0
        while True:
            # --- Toggle (con pequeña desactivación contra rebotes) ---
            if _toggle_pressed():
                now = time.time()
                if now - last_toggle_ts > 0.25:
                    active = not active
                    last_toggle_ts = now
                    if active:
                        print("\n🎤 Estado: ACTIVO. Escuchando… (pulsa ENTER para desactivar)\n")
                    else:
                        print("\n⏸️  Estado: INACTIVO. Pulsa ENTER para ACTIVAR la escucha.\n")
                # sigue al siguiente ciclo
                continue

            if not active:
                # Inactivo: reposo ligero para no comer CPU
                time.sleep(0.08)
                continue

            # Activo: hacemos 1 turno (captura -> envía -> reproduce)
            _process_one_turn()

            # tras cada turno, el bucle sigue activo (seguirá escuchando)
            # el usuario puede pulsar ENTER entre turnos para desactivar

    except KeyboardInterrupt:
        print("\n👋 Cliente terminado.")
        sys.exit(0)


if __name__ == "__main__":
    main()
