@echo off
cd /d %~dp0..
echo ================================
echo   Lanzando Cliente Asistente
echo ================================
python -m client.main
pause
