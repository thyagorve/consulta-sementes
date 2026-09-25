#!/bin/bash
set -e

cron
echo "Cron iniciado"

# Corrige somente registros legados que ainda apontam para localhost.
# Credenciais vêm exclusivamente das variáveis protegidas do ambiente.
if [ -n "${EVOLUTION_API_BASE_URL:-}" ]; then
python /app/manage.py shell <<'PY'
import os
from whatsapp_integration.models import UserInstance

base_url = os.environ.get("EVOLUTION_API_BASE_URL", "").rstrip("/")
qs = UserInstance.objects.filter(base_url__startswith="http://localhost")
count = qs.update(base_url=base_url)
print(f"Instâncias legadas sincronizadas: {count}")
PY
else
    echo "EVOLUTION_API_BASE_URL não configurada; instâncias legadas não foram alteradas."
fi

python /app/manage.py migrate --noinput
exec gunicorn clienteapp.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
