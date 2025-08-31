# server/tts_engine.py
# ====================================
# Síntesis de voz a WAV:
#  - Preferente: Microsoft Edge TTS (online) vía subprocess (formato WAV PCM)
#  - Fallback: pyttsx3 (offline) a WAV
# ====================================

from __future__ import annotations

import subprocess
import sys
import os
from typing import Optional

from .config import (
    USE_EDGE_TTS,
    EDGE_TTS_VOICE,
    EDGE_TTS_RATE,
    EDGE_TTS_PITCH,
    EDGE_TTS_VOLUME,
    PYTTSX3_RATE,
    debug_enabled,
)

def tts_to_wav(text: str, out_wav_path: str) -> Optional[str]:
    """
    Sintetiza 'text' a un WAV (16kHz, 16-bit mono) en 'out_wav_path'.
    Devuelve la ruta al WAV si fue exitoso, o None si falló.
    """
    text = (text or "").strip()
    if not text:
        return None

    # 1) Intento Edge TTS (online) si está habilitado en config
    if USE_EDGE_TTS:
        if debug_enabled():
            print(f"[TTS] Edge TTS -> WAV: {len(text)} chars -> {out_wav_path}")
        ok = _edge_tts_wav(text, out_wav_path)
        if ok:
            return out_wav_path
        else:
            print("[TTS] Edge TTS falló; usando pyttsx3 (offline).")

    # 2) Fallback: pyttsx3 (offline)
    if debug_enabled():
        print(f"[TTS] pyttsx3 -> WAV: {len(text)} chars -> {out_wav_path}")
    ok = _pyttsx3_wav(text, out_wav_path)
    return out_wav_path if ok else None


# -------------------------------------------------------------------
# Edge TTS (vía subprocess -m edge_tts) -> WAV PCM 16kHz 16-bit mono
# -------------------------------------------------------------------
def _edge_tts_wav(text: str, out_wav_path: str) -> bool:
    """
    Usa el binario de Python para llamar al módulo edge_tts y guardar WAV PCM.
    Requiere conexión a Internet.
    """
    try:
        # edge-tts soporta salida WAV PCM con --format riff-16khz-16bit-mono-pcm
        cmd = [
            sys.executable, "-m", "edge_tts",
            "--voice", EDGE_TTS_VOICE,
            "--text", text,
            "--format", "riff-16khz-16bit-mono-pcm",
            "--write-media", out_wav_path,
            "--rate", EDGE_TTS_RATE,
            "--pitch", EDGE_TTS_PITCH,
            "--volume", EDGE_TTS_VOLUME,
        ]
        # Capturamos stdout/stderr para diagnóstico sin ensuciar consola
        res = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore",
        )
        if res.returncode != 0:
            if debug_enabled():
                print("[TTS][edge-tts] returncode:", res.returncode)
                print("[TTS][edge-tts] stderr:", (res.stderr or "").strip()[:500])
            return False

        if not os.path.isfile(out_wav_path) or os.path.getsize(out_wav_path) == 0:
            if debug_enabled():
                print("[TTS][edge-tts] No se generó WAV.")
            return False

        return True

    except FileNotFoundError:
        # edge-tts no instalado
        if debug_enabled():
            print("[TTS][edge-tts] Módulo no encontrado (instala: pip install edge-tts).")
        return False
    except Exception as e:
        if debug_enabled():
            print("[TTS][edge-tts] Excepción:", e)
        return False


# ---------------------------------------
# pyttsx3 (offline) -> WAV (bloqueante)
# ---------------------------------------
def _pyttsx3_wav(text: str, out_wav_path: str) -> bool:
    try:
        import pyttsx3
    except Exception as e:
        print("[TTS][pyttsx3] No disponible:", e)
        return False

    try:
        engine = pyttsx3.init()
        # Ajustes básicos
        try:
            engine.setProperty("rate", PYTTSX3_RATE)
        except Exception:
            pass

        # Nota: Algunas voces/propiedades dependen de la plataforma.
        # pyttsx3 guarda directamente a WAV:
        engine.save_to_file(text, out_wav_path)
        engine.runAndWait()

        ok = os.path.isfile(out_wav_path) and os.path.getsize(out_wav_path) > 0
        if debug_enabled() and not ok:
            print("[TTS][pyttsx3] WAV no generado.")
        return ok

    except Exception as e:
        print("[TTS][pyttsx3] Error sintetizando:", e)
        return False
