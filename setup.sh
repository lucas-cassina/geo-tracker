#!/bin/bash
# setup.sh — Instala dependencias y registra el cron semanal

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📦 Creando entorno virtual e instalando dependencias..."
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet

PYTHON="$SCRIPT_DIR/.venv/bin/python3"

echo ""
echo "📅 Registrando cron semanal (lunes 9:00 AM)..."

CRON_JOB="0 9 * * 1 cd \"$SCRIPT_DIR\" && \"$SCRIPT_DIR/.venv/bin/python3\" monitor.py >> results/cron.log 2>&1"

# Agregar solo si no existe ya
( crontab -l 2>/dev/null | grep -v "geo-tracker"; echo "$CRON_JOB" ) | crontab -

echo "✅ Cron registrado:"
crontab -l | grep geo-tracker

echo ""
echo "🔑 Próximos pasos:"
echo "   1. Copiar .env.example → .env y completar las API keys"
echo "   2. Generar Gmail App Password en: https://myaccount.google.com/apppasswords"
echo "   3. Probar: python3 monitor.py --test"
echo "   4. Correr completo: python3 monitor.py"
