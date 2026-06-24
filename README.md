# futb-event-api

## Tech Stack
- Django 6.0
- Django REST Framework
- PostgreSQL
- Simple JWT
- Pillow & QRCode

## Setup Instructions

1. **Virtual Environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**:
   Create a PostgreSQL database named `futb_events_db`.
   Make sure you have a `postgres` user, or update the `.env` file with your actual database credentials:
   ```env
   DB_NAME=futb_events_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   ```

4. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create Superuser**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Run Development Server**:
   ```bash
   python manage.py runserver
   ```
   Navigate to `http://127.0.0.1:8000/admin` to manage the tables.
