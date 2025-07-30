#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# --- NOVO BLOCO DE CÓDIGO ---
# Este bloco só será executado se a variável de ambiente RESET_DATABASE estiver definida como "true"
if [[ $RESET_DATABASE == "true" ]]; then
  echo "RESETANDO A BASE DE DADOS..."
  # O comando psql usa a variável DATABASE_URL que já configurámos na Render
  psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
  echo "BASE DE DADOS RESETADA."
fi
# --- FIM DO NOVO BLOCO ---

python manage.py migrate