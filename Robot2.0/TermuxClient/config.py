# client/config.py
# ============================
# Configuración del CLIENTE
# ============================

# --- Red / Servidor ---
# Si cliente y servidor están en el mismo PC:
SERVER_HOST = "127.0.0.1"
# Si están en la misma LAN, pon aquí la IP del servidor, ej.: "192.168.1.23"
SERVER_PORT = 5000

# Timeouts de socket (segundos)
CONNECT_TIMEOUT_S = 10
SEND_TIMEOUT_S = 120
RECV_TIMEOUT_S = 300  # alto porque la primera carga de Whisper en el servidor puede tardar

# Tamaño de bloque para red
BUFFER_SIZE = 4096

# --- Audio (grabación) ---
SAMPLE_RATE = 16000      # Hz
CHANNELS = 1             # mono
SAMPLE_WIDTH = 2         # bytes (16-bit PCM)
CHUNK = 1024             # frames por lectura

# Índice del dispositivo de entrada (micrófono). None => predeterminado.
INPUT_DEVICE_INDEX = None

# Duración máxima de una locución (segundos)
RECORD_MAX_SECONDS = 20

# VAD simple (por RMS)
VAD_RMS_THRESHOLD = 0.015   # baja si te corta demasiado; sube si no corta
VAD_MIN_TALK_MS = 300
VAD_SILENCE_TAIL_MS = 600

# --- Activación ---
# "push_to_talk" (pulsa ENTER para hablar) o "always" (siempre escuchando con VAD)
ACTIVATION_MODE = "push_to_talk"

# --- Reproducción ---
RESPONSE_WAV = "response.wav"
# Archivo temporal donde se guarda la grabación del micrófono
RECORDING_WAV = "recording_temp.wav"

PLAYBACK_BACKEND = "auto"   # "simpleaudio", "playsound" o "auto"

# --- Logging ---
PRINT_LEVEL = "DEBUG"       # "INFO" o "DEBUG"
def debug_enabled() -> bool:
    return PRINT_LEVEL.upper() == "DEBUG"
