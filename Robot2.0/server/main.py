# server/main.py
# ====================================
# Servidor del asistente de voz (TCP)
# 1) Recibe WAV del cliente
# 2) Transcribe con Faster-Whisper
# 3) Si es atajo -> responde directo
#    Si no -> consulta a Ollama
# 4) Sintetiza a WAV con TTS
# 5) Devuelve el WAV al cliente
# ====================================

from __future__ import annotations

import os
import socket
import sys
import traceback
from typing import List, Dict

# --- Imports robustos (permiten ejecutar como módulo o script) ---
try:
    from .config import (
        HOST, PORT, ACCEPT_BACKLOG, IN_AUDIO_WAV, OUT_TTS_WAV,
        debug_enabled,
    )
    from . import utils_net, asr_whisper, llm_ollama, tts_engine, commands
except ImportError:
    # Ejecutado como script: añadir carpeta actual al path
    sys.path.append(os.path.dirname(__file__))
    from config import (
        HOST, PORT, ACCEPT_BACKLOG, IN_AUDIO_WAV, OUT_TTS_WAV,
        debug_enabled,
    )
    import utils_net, asr_whisper, llm_ollama, tts_engine, commands


def handle_client(conn: socket.socket, addr, history: List[Dict[str, str]]):
    """
    Maneja una petición completa de un cliente:
      - recibe WAV -> input_server.wav
      - ASR -> texto
      - atajos o LLM -> reply_text
      - TTS -> output_server.wav
      - envía WAV de salida
    """
    if debug_enabled():
        print(f"[SERV] Conexión de {addr}")

    # 1) Recibir WAV del cliente
    ok = utils_net.receive_file(conn, IN_AUDIO_WAV)
    if not ok:
        print("[SERV] Error recibiendo audio. Cerrando conexión.")
        return

    # 2) Transcribir
    try:
        text = asr_whisper.transcribe_wav(IN_AUDIO_WAV)
    except Exception:
        print("[SERV] Error en transcripción:")
        traceback.print_exc()
        text = ""

    if not text.strip():
        reply_text = "No he entendido nada, ¿puedes repetirlo más claro?"
    else:
        if debug_enabled():
            print(f"[SERV] Usuario dijo: {text}")

        # 3) Atajos / intenciones simples
        handled, short_reply = commands.handle_intents(text)
        if handled and short_reply:
            reply_text = short_reply
        else:
            # 3b) Conversación con LLM (manteniendo historial de turno)
            reply_text = ""
            try:
                reply_text = llm_ollama.ask_llm(text, history=history)
            except Exception:
                print("[SERV] Error llamando al LLM:")
                traceback.print_exc()
                reply_text = "Perdona, ahora mismo no puedo pensar bien."

    # Actualizar historial (recortando para no crecer sin límite)
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply_text})
    if len(history) > 20:
        # conservar solo los últimos 18 mensajes + (opcionalmente un system en llm_ollama)
        history[:] = history[-18:]

    # 4) TTS a WAV
    try:
        if os.path.exists(OUT_TTS_WAV):
            try:
                os.remove(OUT_TTS_WAV)
            except Exception:
                pass
        wav = tts_engine.tts_to_wav(reply_text, OUT_TTS_WAV)
        if not wav or not os.path.exists(OUT_TTS_WAV) or os.path.getsize(OUT_TTS_WAV) == 0:
            # Fallback ultra simple: generar un WAV "vacío" de 1s para no romper protocolo
            print("[SERV] TTS falló; devolviendo WAV vacío con texto impreso en consola.")
            _make_silent_wav(OUT_TTS_WAV, 16000, 1, 1.0)
    except Exception:
        print("[SERV] Error en TTS:")
        traceback.print_exc()
        _make_silent_wav(OUT_TTS_WAV, 16000, 1, 1.0)

    # 5) Enviar WAV de vuelta
    ok = utils_net.send_file(conn, OUT_TTS_WAV)
    if not ok:
        print("[SERV] Error enviando respuesta al cliente.")
    if debug_enabled():
        print("[SERV] Petición completada.")


def _make_silent_wav(path: str, sr: int, ch: int, seconds: float):
    """Genera un WAV de silencio por si el TTS falla, para respetar el protocolo."""
    import wave, struct
    frames = int(sr * seconds)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(ch)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        silence_frame = struct.pack("<h", 0)
        for _ in range(frames):
            wf.writeframesraw(silence_frame)


def main():
    print("=== Servidor Asistente de Voz ===")
    print(f"Escuchando en {HOST}:{PORT} (Ctrl+C para salir)")

    # Historial de conversación en memoria (por servidor)
    history: List[Dict[str, str]] = []

    # Preparar socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Reusar puerto rápidamente tras reinicios
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(ACCEPT_BACKLOG)

    try:
        while True:
            conn, addr = srv.accept()
            try:
                handle_client(conn, addr, history)
            except Exception:
                print("[SERV] Excepción manejando cliente:")
                traceback.print_exc()
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    except KeyboardInterrupt:
        print("\n👋 Servidor detenido por usuario.")
    finally:
        try:
            srv.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
