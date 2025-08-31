# audio_utils.py
# ====================================
# Utilidades de grabación y reproducción de audio (Termux friendly)
# ====================================

import os
import time
import wave
import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None  # en termux suele estar

# ---- Config ----
from config import (
    SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH, CHUNK, INPUT_DEVICE_INDEX,
    RECORD_MAX_SECONDS, RESPONSE_WAV, PLAYBACK_BACKEND,
    VAD_RMS_THRESHOLD, VAD_MIN_TALK_MS, VAD_SILENCE_TAIL_MS,
    debug_enabled
)

# ========================
# Helpers de VAD
# ========================

def _rms(int16_block: np.ndarray) -> float:
    if int16_block is None or len(int16_block) == 0:
        return 0.0
    x = int16_block.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(np.square(x))))


def _calibrate_threshold(stream, ms=700) -> float:
    """
    Lee ~ms de audio para estimar ruido de fondo y calcular un umbral.
    Umbral final = max(ruido*2.0, VAD_RMS_THRESHOLD, 0.05 en móviles).
    """
    if debug_enabled():
        print(f"[VAD] Calibrando ruido {ms} ms… (block={CHUNK})")

    total_samples = int(SAMPLE_RATE * (ms/1000.0))
    acc = []
    got = 0
    while got < total_samples:
        data, _ = stream.read(min(CHUNK, total_samples - got))
        mono = data[:, 0] if (hasattr(data, "ndim") and data.ndim > 1) else data
        acc.append(mono.copy())
        got += len(mono)

    noise = _rms(np.concatenate(acc, axis=0))
    # En móviles el ruido suele ser bajísimo; imponemos un mínimo sensato (0.05)
    thr = max(noise * 2.0, float(VAD_RMS_THRESHOLD), 0.05)
    if debug_enabled():
        print(f"[VAD] Ruido={noise:.4f} | Umbral dinámico={thr:.4f} (min={max(float(VAD_RMS_THRESHOLD),0.05):.4f})")
    return thr


# ========================
# Grabación (con VAD mejorado)
# ========================

def record_audio(filename: str,
                 use_vad: bool = True,
                 force_recalibrate: bool = True,
                 pre_silence_ms: int = 350) -> str:
    """
    Graba audio desde el micro y lo guarda en WAV PCM16.

    - Si use_vad=True: detecta inicio de voz solo si ha habido
      'pre_silence_ms' de silencio previo (anti-eco del TTS).
    - force_recalibrate=True: recalibra el umbral antes de cada toma.

    Devuelve la ruta del WAV (o el mismo filename si vacío en error).
    """
    if sd is None:
        print("[Audio] sounddevice no disponible.")
        return filename

    if use_vad:
        print(f"[🎙️] Iniciando grabación (use_vad=True)")

    # Abrimos stream
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=CHUNK,
        device=INPUT_DEVICE_INDEX
    )

    frames = []
    with stream:
        # Umbrales
        thr_on = _calibrate_threshold(stream, 700) if (use_vad and force_recalibrate) else float(VAD_RMS_THRESHOLD)
        thr_off = thr_on * 0.70  # histéresis
        if debug_enabled():
            print(f"[🎙️] Iniciando grabación (use_vad={use_vad}) | thr_on={thr_on:.4f} thr_off={thr_off:.4f}")

        start_time = time.time()

        if not use_vad:
            # grabación fija por tiempo máx
            while True:
                data, _ = stream.read(CHUNK)
                frames.append(data.copy())
                if time.time() - start_time > RECORD_MAX_SECONDS:
                    break

        else:
            # --- VAD con pre-silencio + cola de silencio ---
            voiced = False
            silence_ms = 0.0
            talk_ms = 0.0
            pre_sil_ms = 0.0  # silencio acumulado antes de permitir arranque

            while True:
                data, _ = stream.read(CHUNK)
                mono = data[:, 0] if (hasattr(data, "ndim") and data.ndim > 1) else data
                level = _rms(mono)
                frames.append(mono.copy())

                # VUM
                if debug_enabled():
                    bars = int(min(47, level * 3000))
                    print(f"[VUM] |{'#'*bars}{'.'*(47-bars)}| lvl={level:.4f}", end="\r")

                # acumuladores de tiempos
                dt_ms = (len(mono) / SAMPLE_RATE) * 1000.0

                if not voiced:
                    # requerimos pre-silencio antes de permitir arranque
                    if level < thr_off:
                        pre_sil_ms += dt_ms
                    else:
                        pre_sil_ms = max(0.0, pre_sil_ms - dt_ms)  # ruido → “rompe” pre-silencio

                    if pre_sil_ms >= pre_silence_ms and level > thr_on:
                        # Inicio de voz permitido
                        if debug_enabled():
                            print("\n[VAD] >>> INICIO de voz (pre-sil OK) <<<")
                        voiced = True
                        talk_ms = 0.0
                        silence_ms = 0.0
                else:
                    # ya dentro de locución
                    talk_ms += dt_ms
                    if level >= thr_off:
                        silence_ms = max(0.0, silence_ms - dt_ms/2)  # baja lentamente
                    else:
                        silence_ms += dt_ms

                    # Fin por cola de silencio
                    if silence_ms >= VAD_SILENCE_TAIL_MS and talk_ms >= VAD_MIN_TALK_MS:
                        print("\n[🎙️] Fin de la locución (silencio detectado).")
                        break

                # Fin por tiempo máximo
                if (time.time() - start_time) > RECORD_MAX_SECONDS:
                    print("\n[🎙️] Fin por tiempo máximo.")
                    break

    # Exportar WAV
    if len(frames) == 0:
        return filename

    # Unir en int16
    if isinstance(frames[0], np.ndarray):
        audio = np.concatenate(frames, axis=0).astype(np.int16)
    else:
        # por si viniera ya en bytes
        audio = np.frombuffer(b"".join(frames), dtype=np.int16)

    # Guardar
    wav_path = filename
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)  # 2 bytes (16-bit)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    return wav_path


# ========================
# Reproducción de audio
# ========================

def _termux_media_player_available() -> bool:
    return os.system("command -v termux-media-player >/dev/null 2>&1") == 0

def play_audio_file(path: str = RESPONSE_WAV):
    """
    Reproduce un WAV en Termux. Prioriza termux-media-player (silencia eco en muchos dispositivos).
    Alternativas mínimas si no está disponible.
    """
    if not os.path.exists(path):
        print(f"[Audio] No existe el archivo {path}")
        return

    # 1) Termux media player
    if _termux_media_player_available():
        # reset -> play -> info (solo logging)
        os.system("termux-media-player stop >/dev/null 2>&1")
        os.system(f"termux-media-player play '{path}' >/dev/null 2>&1")
        print(f"Now Playing: {os.path.basename(path)}")
        # bloqueamos hasta terminar:
        # termux-media-player no tiene “wait”; hacemos un busy-wait por duración del archivo
        try:
            import wave as _w
            wf = _w.open(path, "rb")
            nframes = wf.getnframes()
            rate = wf.getframerate()
            wf.close()
            duration = max(0.1, nframes / float(rate))
        except Exception:
            duration = 2.0
        time.sleep(duration + 0.1)
        return

    # 2) Fallback muy simple: intentar 'am' (Android)
    if os.system("command -v am >/dev/null 2>&1") == 0:
        os.system(f"am start -a android.intent.action.VIEW -d 'file://{os.path.abspath(path)}' >/dev/null 2>&1")
        return

    # 3) Último recurso: aplay/start (puede no existir en Termux)
    try:
        if os.name == "posix":
            os.system(f"aplay '{path}'")
        else:
            os.system(f"start {path}")
    except Exception as e:
        print("[Audio] No se pudo reproducir:", e)
