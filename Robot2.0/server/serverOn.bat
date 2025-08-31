@echo off
setlocal
cd /d "%~dp0"

rem ===== venv local de ESTA carpeta =====
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
)
set PY=".venv\Scripts\python.exe"
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt

rem (opcional; ya viene en requirements)
rem %PY% -m pip install python-multipart

rem ===== variables de entorno =====
set HOST=0.0.0.0
set PORT=8000
set API_TOKEN=SURF

rem Dónde corre Ollama (en el SERVIDOR)
set OLLAMA_HOST=http://127.0.0.1:11434
set OLLAMA_MODEL=llama3.1:8b

rem Modelo de ASR (Whisper)
set ASR_MODEL=small

rem ===== evitar CUDA/cuDNN: forzar CPU para faster-whisper =====
set CT2_FORCE_CPU=1
set OMP_NUM_THREADS=1

rem (opcional) arrancar Ollama en otra ventana
rem start "ollama serve" /min cmd /c ollama serve

rem ===== arrancar uvicorn usando el python del venv =====
rem Si este .bat está dentro de la carpeta 'server' (junto a main.py):
%PY% -m uvicorn main:app --host %HOST% --port %PORT% --reload

rem Si ejecutas desde la raíz del repo, usa esta en su lugar:
rem %PY% -m uvicorn server.main:app --host %HOST% --port %PORT% --reload

pause
