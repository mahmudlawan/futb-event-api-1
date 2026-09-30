@echo off
cd /d C:\Users\HomePC\Desktop\Smart_campus_antigravity\futb-event-api
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python manage.py send_reminders
