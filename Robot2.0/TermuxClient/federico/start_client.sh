#!/data/data/com.termux/files/usr/bin/bash
# Arranque del cliente en Termux

# Ir a la carpeta del script
cd "$(dirname "$0")"

echo "==============================="
echo "  Lanzando Cliente Asistente"
echo "==============================="

# Ejecuta el archivo main.py (NO como módulo)
exec python main.py
