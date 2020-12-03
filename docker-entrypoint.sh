#!/bin/bash

set -e

# Wait for the database
if [ -z "$SKIP_DATABASE_CHECK" -o "$SKIP_DATABASE_CHECK" = "0" ]; then
    wait-for-it.sh "${DATABASE_HOST}:${DATABASE_PORT-5432}" --timeout=30
fi

# Apply database migrations
if [[ "$APPLY_MIGRATIONS" = "1" ]]; then
    echo "Applying database migrations..."
    ./manage.py migrate --noinput
fi

# Create admin user. Generate password if there isn't one in the environment variables
if [[ "$CREATE_ADMIN_USER" = "1" ]]; then
    if [[ "$ADMIN_USER_PASSWORD" ]]; then
      ./manage.py add_admin_user -u kuva-admin -p $ADMIN_USER_PASSWORD -e kuva-admin@hel.ninja
    else
      ./manage.py add_admin_user -u kuva-admin -e kuva-admin@hel.ninja
    fi
fi

# Start server
if [[ ! -z "$@" ]]; then
    "$@"
elif [[ "$DEV_SERVER" = "1" ]]; then
    python -Wd ./manage.py runserver 0.0.0.0:8000
else
    uwsgi --ini .prod/uwsgi.ini
fi
