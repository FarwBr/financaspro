#!/bin/bash
set -e

echo "Aguardando PostgreSQL..."
until python -c "import psycopg2; psycopg2.connect(
  host='$DB_HOST', port='$DB_PORT',
  dbname='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD'
)" 2>/dev/null; do
  echo "  postgres não disponível, aguardando..."
  sleep 2
done
echo "PostgreSQL pronto!"

echo "Rodando migrations..."
python init_db.py

echo "Iniciando aplicação na porta $PORT..."
exec python app.py
