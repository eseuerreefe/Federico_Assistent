#!/data/data/com.termux/files/usr/bin/bash
# =========================================
# Lanzando Cliente Asistente en Termux
# =========================================

# Ir al directorio raíz del cliente
cd "$(dirname "$0")"

echo "==============================="
echo "  Lanzando Cliente Asistente"
echo "==============================="

# Ejecutar el cliente como módulo
python -m client_termux.main
