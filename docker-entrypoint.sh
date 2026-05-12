#!/bin/bash
# Si no existe .env, copiar desde .env.example con valores default
if [ ! -f /app/.env ]; then
    cp /app/.env.example /app/.env
    echo "Archivo .env creado desde .env.example. Configuralo con tus datos reales."
fi

exec "$@"
