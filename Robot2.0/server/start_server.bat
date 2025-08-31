@echo off
REM Colócate en la carpeta padre del script (la raíz del proyecto)
cd /d %~dp0..
echo ================================
echo  Lanzando Servidor Asistente
echo ================================
python -m server.main
pause
