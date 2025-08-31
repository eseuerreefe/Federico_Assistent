# client/main.py
# ====================================
# Cliente del asistente de voz
# ====================================

import os
import sys
import time
from .config import (
    RESPONSE_WAV, ACTIVATION_MODE, SERVER_HOST, SERVER_PORT,
    PRINT_LEVEL, debug_enabled, RECORDING_WAV
)
from . import audio_utils
from . import network_utils

def main():
    print("=== Cliente Asistente de Voz ===")
    print(f"Servidor destino: {SERVER_HOST}:{SERVER_PORT}")
    print(f"Log level: {PRINT_LEVEL}")
    print("Pulsa Ctrl+C para salir.\n")

    try:
        while True:
            # Esperar a que el usuario pulse ENTER
            input("👉 Pulsa ENTER para empezar a hablar…")

            # Grabar hasta detectar silencio
            print("[🎤] Grabando… habla, se detendrá cuando haya silencio.")
            user_wav = RECORDING_WAV
            audio_utils.record_audio(user_wav, use_vad=True)

            # Diagnóstico del tamaño
            try:
                size = os.path.getsize(user_wav)
            except Exception:
                size = 0
            if debug_enabled():
                print(f"[🎛️] WAV capturado: {user_wav} ({size} bytes)")

            # Si no hay audio, repetir
            if size == 0:
                print("⚠️ Grabación vacía. Reintentando…\n")
                time.sleep(0.2)
                continue

            # Enviar al servidor
            print("[NET] Enviando al servidor…")
            ok = network_utils.send_audio_and_get_reply(user_wav, RESPONSE_WAV)
            if not ok:
                print("⚠️ Error al comunicar con el servidor.\n")
                time.sleep(0.2)
                continue

            # Reproducir respuesta
            print("[Asistente] ▶ Reproduciendo respuesta…")
            audio_utils.play_audio_file(RESPONSE_WAV)
            print()  # separación

    except KeyboardInterrupt:
        print("\n👋 Cliente terminado.")
        sys.exit(0)


if __name__ == "__main__":
    main()
