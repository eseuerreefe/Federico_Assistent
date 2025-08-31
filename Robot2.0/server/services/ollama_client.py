from typing import Iterable, Dict, Any
import requests

# ---- soporte módulo o script ----
try:
    # cuando todo se ejecuta como paquete
    from ..config import settings
except ImportError:
    # cuando ejecutas "python main.py" desde dentro de server\
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # añade ...\server al path
    from config import settings
# ---------------------------------

def chat(prompt: str, system: str | None = None, temperature: float = 0.6) -> str:
    url = f"{settings.OLLAMA_HOST}/api/generate"
    payload: Dict[str, Any] = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "options": {"temperature": temperature},
        "stream": False,
    }
    if system:
        payload["system"] = system
    r = requests.post(url, json=payload, timeout=600)
    r.raise_for_status()
    data = r.json()
    return data.get("response", "")

def stream_chat(prompt: str, system: str | None = None, temperature: float = 0.6) -> Iterable[str]:
    url = f"{settings.OLLAMA_HOST}/api/generate"
    payload: Dict[str, Any] = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "options": {"temperature": temperature},
        "stream": True,
    }
    if system:
        payload["system"] = system
    with requests.post(url, json=payload, stream=True, timeout=0) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = line.decode("utf-8")
                import json
                obj = json.loads(chunk)
                yield obj.get("response", "")
                if obj.get("done"):
                    break
            except Exception:
                continue
