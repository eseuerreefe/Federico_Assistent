from functools import lru_cache

# ---- soporte módulo o script ----
try:
    from ..config import settings
except ImportError:
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # añade ...\server al path
    from config import settings
# ---------------------------------

@lru_cache(maxsize=1)
def _load_model():
    from faster_whisper import WhisperModel
    # Usa GPU si el servidor la tiene (device="auto")
    model = WhisperModel(settings.ASR_MODEL, device="auto")
    return model

def transcribe_file(file_path: str, language: str | None = None) -> str:
    model = _load_model()
    segments, info = model.transcribe(file_path, language=language)
    text_parts = []
    for seg in segments:
        text_parts.append(seg.text)
    return " ".join(text_parts).strip()
