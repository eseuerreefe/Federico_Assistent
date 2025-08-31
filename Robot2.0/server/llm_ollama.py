# server/llm_ollama.py
# ====================================
# Llamada a Ollama (LLM local)
# Provee ask_llm(text, history=[])
# ====================================

from __future__ import annotations
import requests
from typing import List, Dict

try:
    # cuando se ejecuta como paquete
    from .config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_S, SYSTEM_PROMPT, debug_enabled
except ImportError:
    # cuando se ejecuta como script
    from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_S, SYSTEM_PROMPT, debug_enabled


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """Convierte historial estilo chat en prompt simple para /api/generate."""
    parts = []
    system = next((m["content"] for m in messages if m["role"] == "system"), None)
    if system:
        parts.append(f"<<SYS>>\n{system}\n<</SYS>>")
    for m in messages:
        if m["role"] == "user":
            parts.append(f"Usuario: {m['content']}")
        elif m["role"] == "assistant":
            parts.append(f"Asistente: {m['content']}")
    parts.append("Asistente:")
    return "\n".join(parts)


def _call_chat(messages: List[Dict[str, str]]) -> str:
    url = OLLAMA_URL.rstrip("/") + "/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.5},
    }
    if debug_enabled():
        print(f"[LLM] POST {url} (modelo={OLLAMA_MODEL})")
    r = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT_S)
    r.raise_for_status()
    data = r.json()
    return (data.get("message") or {}).get("content", "") or ""


def _call_generate(messages: List[Dict[str, str]]) -> str:
    url = OLLAMA_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": _messages_to_prompt(messages),
        "stream": False,
        "options": {"temperature": 0.5},
    }
    if debug_enabled():
        print(f"[LLM] POST {url} (modelo={OLLAMA_MODEL})")
    r = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT_S)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "") or ""


def ask_llm(user_text: str, history: List[Dict[str, str]] | None = None) -> str:
    """
    Devuelve la respuesta del LLM. Acepta 'history' (lista de turnos anteriores).
    Añade un system prompt al inicio si no existe.
    """
    msgs: List[Dict[str, str]] = []
    # System prompt
    if not history or (history and history[0].get("role") != "system"):
        msgs.append({"role": "system", "content": SYSTEM_PROMPT})

    if history:
        msgs.extend(history)

    msgs.append({"role": "user", "content": user_text})

    # Intentamos /api/chat; si el servidor no lo soporta, probamos /api/generate
    try:
        reply = _call_chat(msgs).strip()
        if reply:
            return reply
    except requests.HTTPError as e:
        # 404 u otro -> fallback
        if debug_enabled():
            print("[LLM] /api/chat falló, pruebo /api/generate:", e)
    except Exception as e:
        if debug_enabled():
            print("[LLM] Error en /api/chat:", e)

    # Fallback
    try:
        reply = _call_generate(msgs).strip()
        if reply:
            return reply
    except Exception as e:
        if debug_enabled():
            print("[LLM] Error en /api/generate:", e)

    return "Ahora mismo no puedo consultar el modelo local."
