web: python manage.py migrate && gunicorn futb_events.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
