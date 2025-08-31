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

_TOGGLE_KEYS = ("\r", "\n")  # ENTER

def _size_or_zero(path: str) -> int:
    try:
        return os.path.getsize(path)
    except Exception:
        return 0

def _enter_pressed_nonblocking() -> bool:
    """True si se ha pulsado ENTER (no bloqueante)."""
    try:
        if platform.system() == "Windows":
            import msvcrt
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                # vacía el buffer para evitar rebotes
                while msvcrt.kbhit():
                    _ = msvcrt.getwch()
                return ch in _TOGGLE_KEYS
            return False
        else:
            import select
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                line = sys.stdin.readline()
                return line.endswith("\n")
            return False
    except Exception:
        return False

def _process_one_turn(active_flag_ref) -> bool:
    """
    Captura 1 locución (VAD), la envía al servidor y reproduce la respuesta.
    active_flag_ref: dict con {"active": bool} para poder desactivar desde el callback.
    """
    def should_stop_cb():
        # Si se pulsa ENTER durante la grabación -> desactivar y cortar ya
        if _enter_pressed_nonblocking():
            active_flag_ref["active"] = False
            return True
        return False

    user_wav = RECORDING_WAV
    wav_path = audio_utils.record_audio(user_wav, use_vad=True, should_stop=should_stop_cb)

    # Si nos desactivamos durante la grabación, no seguimos
    if not active_flag_ref.get("active", False):
        print("\n⏸️  Estado: INACTIVO. Pulsa ENTER para ACTIVAR la escucha.\n")
        return False

    if not wav_path:
        print("⚠️  Grabación vacía/cancelada. Reintentando…\n")
        time.sleep(0.2)
        return False

    size = _size_or_zero(user_wav)
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
    print()
    return True

def main():
    print("=== Cliente Asistente de Voz ===")
    print(f"Servidor: {SERVER_HOST}:{SERVER_PORT}")
    print(f"Log level: {PRINT_LEVEL}")
    print("Pulsa Ctrl+C para salir.\n")

    # Arranca en INACTIVO
    state = {"active": False}
    print("⏸️  Estado: INACTIVO. Pulsa ENTER para ACTIVAR la escucha.")

    try:
        last_toggle_ts = 0.0
        while True:
            # Toggle fuera de grabación
            if _enter_pressed_nonblocking():
                now = time.time()
                if now - last_toggle_ts > 0.25:  # antirrebotes
                    state["active"] = not state["active"]
                    last_toggle_ts = now
                    if state["active"]:
                        print("\n🎤 Estado: ACTIVO. Escuchando… (pulsa ENTER para desactivar)\n")
                    else:
                        print("\n⏸️  Estado: INACTIVO. Pulsa ENTER para ACTIVAR la escucha.\n")
                continue

            if not state["active"]:
                time.sleep(0.08)
                continue

            # Activo: un turno (captura -> envía -> reproduce).
            # Durante la captura también podrás pulsar ENTER para parar.
            _process_one_turn(state)

            # Si se desactivó durante la captura, ya imprimió el mensaje y aquí seguimos inactivos

    except KeyboardInterrupt:
        print("\n👋 Cliente terminado.")
        sys.exit(0)

if __name__ == "__main__":
    main()
