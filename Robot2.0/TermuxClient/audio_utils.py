import os
import subprocess
from .config import RESPONSE_WAV, RECORDING_WAV, debug_enabled

def record_audio(filename: str, use_vad: bool = False, should_stop=None) -> str:
    """
    Usa termux-microphone-record para grabar un archivo WAV.
    Se detiene cuando pulsas ENTER (desde main).
    """
    print("[🎙️] Grabando... pulsa ENTER para cortar.")

    # lanza grabación en segundo plano
    proc = subprocess.Popen(
        ["termux-microphone-record", "-f", filename],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # espera hasta que should_stop() lo cancele
    try:
        while proc.poll() is None:
            if should_stop and should_stop():
                proc.terminate()
                break
    except KeyboardInterrupt:
        proc.terminate()

    return filename if os.path.exists(filename) else ""

def play_audio_file(path: str = RESPONSE_WAV):
    """Reproduce usando termux-media-player."""
    if not os.path.exists(path):
        print(f"[Audio] No existe {path}")
        return
    try:
        subprocess.run(["termux-media-player", "play", path])
    except Exception as e:
        print("[Audio] Error al reproducir:", e)
