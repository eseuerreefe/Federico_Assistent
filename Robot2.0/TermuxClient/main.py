import os
import sys
import threading
import time
from .config import RESPONSE_WAV, SERVER_HOST, SERVER_PORT, PRINT_LEVEL, debug_enabled, RECORDING_WAV
from . import audio_utils
from . import network_utils

state = {"active": False, "stop": False}

def key_listener():
    """Hilo que espera ENTER para alternar estado activo/inactivo."""
    while True:
        try:
            input()
            state["active"] = not state["active"]
            state["stop"] = True
            if state["active"]:
                print("\n🎤 ACTIVO. Habla... (ENTER para desactivar)")
            else:
                print("\n⏸️ INACTIVO. Pulsa ENTER para activar.")
        except EOFError:
            break

def main():
    print("=== Cliente Termux Asistente de Voz ===")
    print(f"Servidor destino: {SERVER_HOST}:{SERVER_PORT}")
    print(f"Log level: {PRINT_LEVEL}\n")

    # arranca hilo para detectar ENTER
    threading.Thread(target=key_listener, daemon=True).start()

    print("⏸️ INACTIVO. Pulsa ENTER para activar.")
    try:
        while True:
            if not state["active"]:
                time.sleep(0.2)
                continue

            # grabar hasta ENTER
            def should_stop():
                if state["stop"]:
                    state["stop"] = False
                    return True
                return False

            user_wav = RECORDING_WAV
            wav_path = audio_utils.record_audio(user_wav, use_vad=True, should_stop=should_stop)

            if not state["active"]:
                continue
            if not wav_path:
                print("⚠️ Grabación vacía.")
                continue

            print("[NET] Enviando al servidor...")
            ok = network_utils.send_audio_and_get_reply(user_wav, RESPONSE_WAV)
            if not ok:
                print("⚠️ Error al comunicar con el servidor.\n")
                continue

            print("[Asistente] ▶ Respuesta...")
            audio_utils.play_audio_file(RESPONSE_WAV)
            print()

    except KeyboardInterrupt:
        print("\n👋 Cliente terminado.")
        sys.exit(0)

if __name__ == "__main__":
    main()
