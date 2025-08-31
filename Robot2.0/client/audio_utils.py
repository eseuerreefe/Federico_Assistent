# client/audio_utils.py
# ====================================
# Utilidades de grabación y reproducción de audio (con calibración + VAD)
# ====================================

import os
import time
import wave
import numpy as np
import sounddevice as sd

from .config import (
    SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH, CHUNK, INPUT_DEVICE_INDEX,
    RECORD_MAX_SECONDS, RESPONSE_WAV, PLAYBACK_BACKEND,
    VAD_RMS_THRESHOLD, VAD_MIN_TALK_MS, VAD_SILENCE_TAIL_MS,
    PRINT_LEVEL, debug_enabled
)

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def _rms(x: np.ndarray) -> float:
    """RMS de audio int16 normalizado a [-1, 1]."""
    if x is None or len(x) == 0:
        return 0.0
    x = x.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(np.square(x))))

def _dbg(msg: str):
    if debug_enabled():
        print(msg, flush=True)

def _frame_ms() -> float:
    """Duración (ms) de un bloque 'CHUNK' a SAMPLE_RATE."""
    return (CHUNK / float(SAMPLE_RATE)) * 1000.0

# -------------------------------------------------
# Calibración de ruido = mismo enfoque que el "que te iba"
# -------------------------------------------------

def _calibrate_noise(stream, seconds: float = 1.0) -> float:
    print("[VAD] Calibrando ruido ambiente…")
    frames_needed = int(seconds * SAMPLE_RATE)
    buf = []
    samples_acc = 0

    # Leemos en pasos de ~50ms para tener resolución razonable
    step = int(SAMPLE_RATE * 0.05)
    while samples_acc < frames_needed:
        data, _ = stream.read(step)
        buf.append(data.copy())
        samples_acc += data.shape[0] if hasattr(data, "shape") else len(data)
        if len(buf) % 2 == 0 and debug_enabled():
            audio_partial = np.concatenate(buf, axis=0).flatten()
            _dbg(f"[VAD] Calibración progreso: {samples_acc}/{frames_needed} muestras, RMS parcial={_rms(audio_partial):.4f}")

    audio = np.concatenate(buf, axis=0).flatten()
    baseline = _rms(audio)
    # mismo criterio: umbral por defecto mínimo 0.008 o 2x el ruido
    threshold = max(0.008, baseline * 2.0)
    print(f"[VAD] Ruido: {baseline:.4f} | Umbral: {threshold:.4f}")
    return float(threshold)

# -------------------------------------------------
# Captura por VAD con histéresis y corte por silencio
# (idéntica idea al código que te funcionaba)
# -------------------------------------------------

def _collect_utterance(stream, threshold: float) -> np.ndarray | None:
    """Devuelve np.array(int16) con la locución o None si no hay voz durante ~5s."""
    frame_len = CHUNK  # leemos en bloques de CHUNK frames
    frame_ms = _frame_ms()
    # nº de frames de "cola de silencio" necesarios para cortar
    silence_limit_frames = int(max(1, VAD_SILENCE_TAIL_MS / frame_ms))
    # límite duro por duración máxima de locución
    max_frames = int(max(1, (RECORD_MAX_SECONDS * 1000.0) / frame_ms))

    th_on = float(threshold)
    th_off = float(threshold * 0.6)  # histéresis

    _dbg(f"[VAD] Esperando voz: frame_ms={frame_ms:.1f}, "
         f"silence_limit_frames={silence_limit_frames}, "
         f"max_frames={max_frames}, threshold_on={th_on:.4f}, threshold_off={th_off:.4f}")

    voiced = False
    voiced_frames = []
    silence_count = 0
    frame_count = 0
    start_time = time.time()

    while True:
        data, _ = stream.read(frame_len)
        mono = data[:, 0] if (hasattr(data, "ndim") and data.ndim > 1) else data
        level = _rms(mono)
        frame_count += 1

        if frame_count % 5 == 0 and debug_enabled():
            bars = int(min(30, level * 2000))
            _dbg(f"[VUM] |{'#'*bars}{'.'*(30-bars)}| lvl={level:.4f} thr_on={th_on:.4f} thr_off={th_off:.4f}")

        if not voiced:
            if level > th_on:
                _dbg("[VAD] >>> DETECTADO INICIO DE VOZ <<<")
                voiced = True
                voiced_frames.append(mono.copy())
                silence_count = 0
        else:
            # dentro de locución
            if level >= th_off:
                silence_count = max(0, silence_count - 1)  # reduce “cola de silencio” si hay voz
            else:
                silence_count += 1
            voiced_frames.append(mono.copy())

            if silence_count >= silence_limit_frames:
                _dbg("[VAD] Silencio suficientemente largo. Fin de locución.")
                break

        if len(voiced_frames) >= max_frames:
            _dbg("[VAD] Cortado por duración máxima de locución.")
            break

        # Si jamás arrancó la voz, a los 5s devolvemos None para recalibrar
        if not voiced and (time.time() - start_time) > 5.0:
            _dbg("[VAD] 5s sin voz detectable. Devolviendo None para recalibrar.")
            return None

    if not voiced_frames:
        return None

    audio = np.concatenate(voiced_frames, axis=0).astype(np.int16)
    _dbg(f"[VAD] Locución capturada: {len(audio)} muestras ({len(audio)/SAMPLE_RATE:.2f} s)")
    return audio

# -------------------------------------------------
# API pública: grabar con/ sin VAD (pero ambos cortan por silencio)
# -------------------------------------------------

def record_audio(filename: str, use_vad: bool = True) -> str:
    """
    Graba desde el micro y guarda un WAV PCM16 en `filename`.
    Si `use_vad=True` -> calibra ruido y usa VAD con histéresis y cola de silencio.
    Si `use_vad=False` -> aún así corta por silencio (mismo VAD) pero sin recalibrar al “no detectar”.
    """
    if use_vad:
        print("🎤 Escuchando… habla y se cortará cuando haya silencio.")
    else:
        print(f"🎤 Empieza a hablar (máx {RECORD_MAX_SECONDS}s)… Se cortará al detectar silencio.")

    # abrimos stream
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=CHUNK,
        device=INPUT_DEVICE_INDEX
    )

    # buffer final (para el modo sin calibración extra si hiciera falta)
    audio_np = None

    with stream:
        threshold = _calibrate_noise(stream, seconds=1.0)

        if use_vad:
            # Igual que el “que te iba”: si no se detecta voz tras ~5s,
            # recalibra y vuelve a intentar.
            while True:
                utt = _collect_utterance(stream, threshold)
                if utt is not None:
                    audio_np = utt
                    break
                print("[VAD] No hubo voz. Recalibrando umbral…")
                threshold = _calibrate_noise(stream, seconds=1.0)
        else:
            # push-to-talk con mismo VAD (una sola pasada, sin recalibración en bucle)
            audio_np = _collect_utterance(stream, threshold)
            if audio_np is None:
                print("⚠️  No se captó voz. Reintentando con una calibración corta…")
                threshold = _calibrate_noise(stream, seconds=0.5)
                audio_np = _collect_utterance(stream, threshold)
                if audio_np is None:
                    # último recurso: graba un bloque vacío para no romper el flujo
                    audio_np = np.zeros(int(SAMPLE_RATE * 0.2), dtype=np.int16)

    # Guardar WAV
    _write_wav_int16(filename, audio_np)
    return filename

def _write_wav_int16(path: str, audio_np: np.ndarray):
    wf = wave.open(path, "wb")
    try:
        wf.setnchannels(CHANNELS)
        # SAMPLE_WIDTH viene en bytes — normalmente 2 (16-bit)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        # si por algún motivo llega 2D, aplanamos
        if audio_np.ndim > 1:
            audio_np = audio_np.reshape(-1)
        wf.writeframes(audio_np.tobytes())
    finally:
        wf.close()

# -------------------------------------------------
# Reproducción de audio (igual que tenías, con fallback)
# -------------------------------------------------

def play_audio_file(path: str = RESPONSE_WAV):
    """Reproduce un WAV con simpleaudio, playsound o fallback de sistema."""
    if not os.path.exists(path):
        print(f"[Audio] No existe el archivo {path}")
        return

    backend = (PLAYBACK_BACKEND or "auto").lower()

    if backend in ("simpleaudio", "auto"):
        try:
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(path)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            return
        except Exception as e:
            if backend == "simpleaudio":
                print("[Audio] Error con simpleaudio:", e)

    if backend in ("playsound", "auto"):
        try:
            from playsound import playsound
            playsound(path)
            return
        except Exception as e:
            if backend == "playsound":
                print("[Audio] Error con playsound:", e)

    # Último recurso: comando del SO
    try:
        if os.name == "posix":
            os.system(f"aplay {path}")
        else:
            os.system(f"start {path}")
    except Exception as e:
        print("[Audio] No se pudo reproducir:", e)
