# config.py — Termux client (en la MISMA carpeta que main.py)

# --- Red / Servidor ---
SERVER_HOST = "192.168.1.133"   # <-- pon aquí la IP de tu servidor
SERVER_PORT = 5000

# --- Timeouts de socket (segundos) ---
CONNECT_TIMEOUT_S = 10
SEND_TIMEOUT_S = 120
RECV_TIMEOUT_S = 300

# --- Tamaño de bloque para red ---
BUFFER_SIZE = 4096

# --- Audio (grabación) ---
SAMPLE_RATE = 16000    # Hz
CHANNELS = 1           # mono
SAMPLE_WIDTH = 2       # bytes (16-bit PCM)
CHUNK = 1024           # frames por lectura

# Índice del dispositivo de entrada (micrófono). None => predeterminado.
INPUT_DEVICE_INDEX = None

# Duración máxima de una locución (segundos)
RECORD_MAX_SECONDS = 20

# --- VAD (umbral y tiempos) ---
# Umbral base mínimo (se recalibra dinámicamente; este es el mínimo)
VAD_RMS_THRESHOLD = 0.015
# Tiempo mínimo de habla para considerar una locución (ms)
VAD_MIN_TALK_MS = 300
# Cola de silencio para cortar la locución (ms)
VAD_SILENCE_TAIL_MS = 600

# --- Ficheros de I/O ---
RESPONSE_WAV = "response.wav"
RECORDING_WAV = "recording_temp.wav"

# --- Reproductor preferido ---
# En Termux usaremos termux-media-player si está disponible.
# (Este valor se ignora si hay termux-media-player)
PLAYBACK_BACKEND = "auto"

# --- Logging ---
PRINT_LEVEL = "DEBUG"   # "INFO" o "DEBUG"

def debug_enabled() -> bool:
    return PRINT_LEVEL.upper() == "DEBUG"
