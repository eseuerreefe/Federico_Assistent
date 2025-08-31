# server/config.py
# ============================
# Configuración del SERVIDOR
# ============================

# --- Red / Escucha ---
HOST = "0.0.0.0"     # escucha en todas las interfaces de la LAN
PORT = 5000

# Tamaños / timeouts de socket
ACCEPT_BACKLOG = 5
RECV_TIMEOUT_S = 120
SEND_TIMEOUT_S = 120
BUFFER_SIZE = 4096

# --- Rutas temporales ---
IN_AUDIO_WAV = "input_server.wav"      # audio recibido del cliente
OUT_TTS_WAV  = "output_server.wav"     # respuesta TTS a enviar

# --- Whisper (STT) ---
# Modelos posibles: "tiny", "base", "small", "medium", "large-v3"
WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cpu"                 # "cpu" o "cuda"
WHISPER_COMPUTE_TYPE = "int8"          # en CPU: "int8" o "int8_float16"
WHISPER_LANGUAGE = "es"                # None para autodetección

# --- Ollama (LLM local) ---
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:latest"             # cambia al modelo que tengas descargado
OLLAMA_TIMEOUT_S = 60                  # timeout HTTP

# Prompt del sistema
SYSTEM_PROMPT = (
    "Eres un asistente de voz en español. Responde breve y claro. "
    "Si te piden chistes o bromas puedes ser un poco colega pero respetuoso."
)

# --- TTS ---
USE_EDGE_TTS = True
EDGE_TTS_VOICE = "es-ES-ElviraNeural"  # o "es-ES-AlvaroNeural"
EDGE_TTS_RATE = "+0%"
EDGE_TTS_PITCH = "+0Hz"
EDGE_TTS_VOLUME = "+0%"

# pyttsx3 (offline)
PYTTSX3_RATE = 170

# --- Intenciones simples ---
WAKE_WORD = "federico"
INTENT_NEWS_KEYWORDS = ["noticias", "titulares", "resumen de noticias", "leer noticias"]
INTENT_TIMER_KEYWORDS = ["alarma", "temporizador", "timer", "cuenta atras", "cuenta atrás", "avísame en", "avisame en"]
INTENT_FRIENDS_KEYWORDS = ["listar amigos", "lista de amigos"]
INTENT_SHUTUP_KEYWORDS = ["cállate", "callate", "para", "silencio", "stop"]

NEWS_FEEDS = [
    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    "https://www.bbc.co.uk/mundo/ultimas_noticias/index.xml",
    "https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml",
]

DEFAULT_CITY = "Bilbao"
DEFAULT_LAT = 43.2630
DEFAULT_LON = -2.9350

# --- Logging ---
LOG_LEVEL = "DEBUG"



def debug_enabled() -> bool:
    return LOG_LEVEL.upper() == "DEBUG"
