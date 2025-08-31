# server/asr_whisper.py
# ====================================
# Transcripción de audio a texto con Faster-Whisper
# ====================================

from __future__ import annotations

import threading
from typing import Optional

from faster_whisper import WhisperModel

from .config import (
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE,
    debug_enabled,
)

# Carga perezosa en singleton (un único modelo compartido por hilos)
_model_lock = threading.Lock()
_model: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    """
    Devuelve una instancia única de WhisperModel cargada según config.
    Reutilizar el modelo evita tiempos de carga repetidos.
    """
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is None:
            if debug_enabled():
                print(
                    f"[ASR] Cargando Faster-Whisper: size={WHISPER_MODEL_SIZE}, "
                    f"device={WHISPER_DEVICE}, compute_type={WHISPER_COMPUTE_TYPE}"
                )
            _model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            if debug_enabled():
                print("[ASR] Modelo cargado.")
    return _model


def transcribe_wav(path_wav: str, language: Optional[str] = WHISPER_LANGUAGE) -> str:
    """
    Transcribe un WAV mono PCM16 a texto.
    - language: "es" para forzar español, o None para autodetección.
    Devuelve el texto concatenado de todos los segmentos.
    """
    model = get_model()

    # Ajustes razonables: VAD interno y beam pequeño para latencia
    # Puedes tunear estos parámetros si necesitas más precisión/menos latencia.
    if debug_enabled():
        print(f"[ASR] Transcribiendo: {path_wav} (lang={language or 'auto'})")

    segments, info = model.transcribe(
        path_wav,
        language=language,       # None -> autodetect
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
        beam_size=1,             # 1 para velocidad; >1 mejora precisión
    )

    if debug_enabled():
        lang = getattr(info, "language", "?")
        prob = getattr(info, "language_probability", 0.0)
        print(f"[ASR] Info idioma: {lang} (p={prob:.2f})")

    text = "".join(seg.text for seg in segments).strip()
    if debug_enabled():
        print(f"[ASR] Texto: {text}")
    return text
