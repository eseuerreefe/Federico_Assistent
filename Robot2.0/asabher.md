# Cliente-Servidor: Ollama + ASR (cliente mínimo)

## Estructura
- server/ (FastAPI) — todo lo pesado (Ollama y Whisper)
- client/ (CLI) — menú bonito, subir audio y prompts

## Puesta en marcha rápida
### Servidor
1. Tener Ollama y el modelo descargado:
   - `ollama serve`
   - `ollama pull llama3.1:8b`
2. Instalar dependencias:
   - `cd server && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
3. Lanzar API:
   - `uvicorn main:app --host 0.0.0.0 --port 8000`
4. Variables de entorno (opcional):
   - `OLLAMA_HOST=http://127.0.0.1:11434`
   - `OLLAMA_MODEL=llama3.1:8b`
   - `ASR_MODEL=small`
   - `API_TOKEN=changeme`

### Cliente
1. Instalar dependencias:
   - `cd client && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
2. Variables de entorno:
   - `SERVER_URL=http://IP_DEL_SERVIDOR:8000`
   - `API_TOKEN=changeme`
3. Ejecutar:
   - `python client.py`
