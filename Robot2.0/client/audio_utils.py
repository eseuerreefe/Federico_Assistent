# client/audio_utils.py
# ====================================
# Utilidades de grabación y reproducción de audio
# ====================================

import time
import numpy as np
import sounddevice as sd
import wave
import os
from typing import Callable, Optional

from .config import (
    SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH, CHUNK, INPUT_DEVICE_INDEX,
    RECORD_MAX_SECONDS, RESPONSE_WAV, PLAYBACK_BACKEND,
    VAD_RMS_THRESHOLD, VAD_MIN_TALK_MS, VAD_SILENCE_TAIL_MS,
    debug_enabled
)

# ========================
# Grabación de audio (push-to-talk o VAD simple)
# ========================

def _rms(audio_chunk: np.ndarray) -> float:
    """Devuelve el RMS de un bloque de audio (0.0–1.0)."""
    if len(audio_chunk) == 0:
        return 0.0
    audio = audio_chunk.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(np.square(audio))))

def record_audio(filename: str, use_vad: bool = False,
                 should_stop: Optional[Callable[[], bool]] = None) -> str:
    """
    Graba audio desde el micro y lo guarda en WAV PCM16.
    - use_vad=True: corta por silencio (VAD simple).
    - should_stop(): función opcional que, si devuelve True, cancela de inmediato.
    Devuelve la ruta del WAV o cadena vacía si se canceló sin datos.
    """
    msg_lim = f"máx {RECORD_MAX_SECONDS} s" if not use_vad else "corta por silencio"
    print(f"[🎙️] Empieza a hablar ({msg_lim})…")

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16",
        blocksize=CHUNK, device=INPUT_DEVICE_INDEX
    )
    frames = []
    with stream:
        start_time = time.time()
        voiced = False
        silence_ms = 0
        talk_ms = 0

        while True:
            # Cancelación inmediata por tecla (ENTER) u otro trigger
            if should_stop and should_stop():
                print("\n[🎙️] Grabación cancelada por el usuario.")
                frames = []  # no guardamos nada
                break

            data, _ = stream.read(CHUNK)
            frames.append(data.copy())

            if use_vad:
                level = _rms(data)
                if debug_enabled():
                    bars = int(min(50, level * 60))
                    print(f"[VUM] |{'#'*bars}{'.'*(50-bars)}| lvl={level:.4f}", end="\r")

                # Voz / silencio
                if level > VAD_RMS_THRESHOLD:
                    talk_ms += (CHUNK / SAMPLE_RATE) * 1000
                    silence_ms = 0
                    voiced = True
                else:
                    if voiced:
                        silence_ms += (CHUNK / SAMPLE_RATE) * 1000

                # Fin por silencio si ya hubo voz
                if voiced and silence_ms > VAD_SILENCE_TAIL_MS:
                    print("\n[🎙️] Fin de la locución (silencio detectado).")
                    break

                # Seguridad: límite de tiempo duro
                if time.time() - start_time > RECORD_MAX_SECONDS:
                    print("\n[🎙️] Fin por tiempo máximo.")
                    break
            else:
                # Modo push-to-talk: solo cortamos por tiempo o cancelación
                if time.time() - start_time > RECORD_MAX_SECONDS:
                    print("\n[🎙️] Fin por tiempo máximo.")
                    break

    # Si no hay muestras, devolvemos vacío (cancelado o fallo)
    if not frames:
        return ""

    # Convertimos a WAV
    wav_path = filename
    wf = wave.open(wav_path, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(SAMPLE_WIDTH)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b"".join([f.tobytes() for f in frames]))
    wf.close()

    return wav_path

# ========================
# Reproducción de audio
# ========================

def play_audio_file(path: str = RESPONSE_WAV):
    """Reproduce un archivo WAV con simpleaudio, playsound o fallback."""
    if not os.path.exists(path):
        print(f"[Audio] No existe el archivo {path}")
        return

    backend = PLAYBACK_BACKEND.lower()
    if backend == "simpleaudio" or backend == "auto":
        try:
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(path)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            return
        except Exception as e:
            if backend == "simpleaudio":
                print("[Audio] Error con simpleaudio:", e)

    if backend == "playsound" or backend == "auto":
        try:
            from playsound import playsound
            playsound(path)
            return
        except Exception as e:
            if backend == "playsound":
                print("[Audio] Error con playsound:", e)

    # Último recurso: system call
    try:
        if os.name == "posix":
            os.system(f"aplay {path}")
        else:
            os.system(f'start "" "{path}"')
    except Exception as e:
        print("[Audio] No se pudo reproducir:", e)
