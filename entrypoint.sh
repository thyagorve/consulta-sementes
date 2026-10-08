#!/bin/sh
set -e

PROCESS_TYPE="${APP_PROCESS:-web}"

echo "[ImobCRM] Processo: ${PROCESS_TYPE}"

if [ "$PROCESS_TYPE" = "worker" ]; then
  echo "[ImobCRM] Iniciando worker de WhatsApp..."
  exec python manage.py whatsapp_worker --interval "${WHATSAPP_WORKER_INTERVAL:-15}"
fi

if [ "$PROCESS_TYPE" = "web" ]; then
  echo "[ImobCRM] Aplicando migrations..."
  python manage.py migrate --noinput

  echo "[ImobCRM] Coletando arquivos estáticos..."
  python manage.py collectstatic --noinput

  echo "[ImobCRM] Iniciando Gunicorn..."
  exec gunicorn imobcrm.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --threads ${GUNICORN_THREADS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile -
fi

echo "[ImobCRM] APP_PROCESS inválido: ${PROCESS_TYPE}. Use web ou worker."
exit 2
