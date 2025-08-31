# main.py
import os, sys, time, select
from config import SERVER_HOST, SERVER_PORT, PRINT_LEVEL, debug_enabled, RECORDING_WAV, RESPONSE_WAV
import audio_utils
import network_utils

def _file_size(p):
    try: return os.path.getsize(p)
    except: return 0

def main():
    print("===============================")
    print("  Lanzando Cliente Asistente")
    print("===============================")
    print("=== Cliente Termux Asistente de Voz ===")
    print(f"Servidor destino: {SERVER_HOST}:{SERVER_PORT}")
    print(f"Log level: {PRINT_LEVEL}\n")

    active = False
    try:
        while True:
            if not active:
                print("⏸️  INACTIVO. Pulsa ENTER para activar.")
                try: input()
                except KeyboardInterrupt:
                    print("\n👋 Cliente terminado."); return
                active = True
                continue

            print("🎤 ACTIVO. Habla... (ENTER para desactivar)")
            user_wav = RECORDING_WAV
            # >>> VAD con pre-silencio y recalibración en cada turno <<<
            wav_path = audio_utils.record_audio(
                user_wav,
                use_vad=True,
                force_recalibrate=True,
                pre_silence_ms=350
            )

            if not wav_path or _file_size(wav_path) == 0:
                i, _, _ = select.select([sys.stdin], [], [], 0.5)
                if i:
                    _ = sys.stdin.readline()
                    active = False
                continue

            print("[NET] Enviando al servidor…")
            ok = network_utils.send_audio_and_get_reply(wav_path, RESPONSE_WAV)
            if not ok:
                print("⚠️  Error al comunicar con el servidor.")
                i, _, _ = select.select([sys.stdin], [], [], 0.8)
                if i:
                    _ = sys.stdin.readline()
                    active = False
                continue

            print("[Asistente] ▶ Respuesta...")
            audio_utils.play_audio_file(RESPONSE_WAV)

            # === anti-eco: espera corta tras reproducir ===
            time.sleep(0.6)

            print("Pulsa ENTER para desactivar (o espera para seguir hablando)...")
            i, _, _ = select.select([sys.stdin], [], [], 1.5)
            if i:
                _ = sys.stdin.readline()
                active = False

    except KeyboardInterrupt:
        print("\n👋 Cliente terminado.")
        sys.exit(0)

if __name__ == "__main__":
    main()
