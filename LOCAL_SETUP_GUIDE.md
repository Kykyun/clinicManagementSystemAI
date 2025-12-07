# Clinic Management System - Local Setup Guide

## Prerequisites

Before running this system locally, make sure you have:

1. **Python 3.10 or higher** - Download from https://python.org
2. **PostgreSQL 14+** - Download from https://postgresql.org
3. **Git** - Download from https://git-scm.com

## Step 1: Clone the Project

```bash
git clone <your-repository-url>
cd clinic-management
```

## Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (Mac/Linux)
source venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install django psycopg2-binary python-dateutil reportlab requests pillow gunicorn google-genai openai
```

## Step 4: Set Up PostgreSQL Database

1. Open PostgreSQL and create a new database:

```sql
CREATE DATABASE clinic_management;
CREATE USER clinic_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE clinic_management TO clinic_user;
```

## Step 5: Configure Environment Variables

Create a `.env` file in the project root (or set these as system environment variables):

```
DATABASE_URL=postgresql://clinic_user:your_password@localhost:5432/clinic_management
SESSION_SECRET=your-secret-key-here-make-it-long-and-random
DEBUG=True

# Optional: For AI features
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
```

Then update `clinic_management/settings.py` to read from environment:

```python
import os
from urllib.parse import urlparse

# At the top of settings.py, add:
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    url = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or 5432,
        }
    }
```

## Step 6: Run Database Migrations

```bash
python manage.py migrate
```

## Step 7: Create Admin User

```bash
python manage.py createsuperuser
```

Follow the prompts to create your admin account.

## Step 8: Load Initial Data (Optional)

If you have fixture files:

```bash
python manage.py loaddata initial_data.json
```

## Step 9: Run the Development Server

```bash
python manage.py runserver 0.0.0.0:5000
```

## Step 10: Access the Application

Open your browser and go to:
- **Main App**: http://localhost:5000
- **Admin Panel**: http://localhost:5000/admin

## Default User Roles

After logging in as admin, create users with these roles:
- **Admin** - Full system access
- **Doctor** - Consultations, prescriptions
- **Nurse** - Triage, patient vitals
- **Receptionist** - Patient registration, check-in
- **Finance** - Billing, payments
- **Pharmacy** - Dispensing medications

## Key URLs

| URL | Description |
|-----|-------------|
| `/accounts/login/` | Login page |
| `/management/` | Main dashboard |
| `/patients/reception/` | Reception workstation |
| `/patients/nurse/` | Nurse workstation |
| `/patients/doctor/` | Doctor workstation |
| `/patients/pharmacy/` | Pharmacy workstation |
| `/finance/billing/` | Billing workstation |
| `/patients/queue/` | Public queue display |
| `/setup/` | System setup (admin only) |

## Troubleshooting

### Database Connection Error
- Verify PostgreSQL is running
- Check DATABASE_URL format
- Ensure database user has correct permissions

### Static Files Not Loading
```bash
python manage.py collectstatic
```

### Migration Errors
```bash
python manage.py makemigrations
python manage.py migrate --run-syncdb
```

### AI Features Not Working
- Verify GEMINI_API_KEY is set correctly
- Check AI configuration in Admin > AI Config

## Production Deployment

For production, use:
```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port clinic_management.wsgi:application
```

Remember to:
1. Set `DEBUG=False`
2. Configure proper `ALLOWED_HOSTS`
3. Use a secure `SESSION_SECRET`
4. Set up HTTPS with a reverse proxy (nginx/Apache)
