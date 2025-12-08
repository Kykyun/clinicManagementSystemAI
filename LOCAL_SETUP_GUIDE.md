# Clinic Management System - Local Setup Guide

## Prerequisites

Before running this system locally, make sure you have:

1. **Python 3.10 or higher** - Download from https://python.org
2. **PostgreSQL 14+** - Download from https://postgresql.org
3. **Git** - Download from https://git-scm.com

---

## Quick Start - Running the Application

**Already completed the setup?** Follow these steps to run the system locally:

### Step 1: Open PowerShell

1. Navigate to your project directory:
   ```powershell
   cd c:\clinicManagementSystemAI
   ```

### Step 2: Activate Virtual Environment

**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**Command Prompt (if PowerShell doesn't work):**
```cmd
venv\Scripts\activate.bat
```

You should see `(venv)` appear at the start of your command prompt.

### Step 3: Start the Development Server

```powershell
python manage.py runserver
```

**Expected output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
December 08, 2025 - 22:30:00
Django version 5.x.x, using settings 'clinic_management.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Step 4: Access the Application

**Main Application:**
- Open your browser and go to: http://127.0.0.1:8000
- Or: http://localhost:8000

**Admin Panel:**
- URL: http://127.0.0.1:8000/admin
- Username: `admin`
- Password: `admin123` (or the password you set)

### Step 5: Stop the Server

When you're done, press `Ctrl + C` in the PowerShell window to stop the server.

### Daily Startup Commands (Summary)

```powershell
# Navigate to project
cd c:\clinicManagementSystemAI

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start server
python manage.py runserver

# Open browser to: http://127.0.0.1:8000/admin
```

---

## Full Setup Guide (First Time Only)

If you haven't set up the system yet, follow these detailed steps:

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
pip install django psycopg2-binary python-dotenv python-dateutil reportlab requests pillow gunicorn google-genai openai
```

> **Note:** `python-dotenv` is required to automatically load environment variables from the `.env` file.

## Step 4: Set Up PostgreSQL Database

### Option 1: Using pgAdmin (Recommended for Windows)

1. Open **pgAdmin 4** from the Start Menu
2. Connect to your PostgreSQL server (localhost)
   - Enter your postgres password when prompted
3. Right-click **Databases** → **Create** → **Database**
4. Set **Database name** to `ClinicMSAI`
5. Click **Save**

### Option 2: Using Command Line

**Windows PowerShell:**
```powershell
# Add PostgreSQL to PATH for this session
$env:Path += ';C:\Program Files\PostgreSQL\18\bin'

# Create the database (will prompt for postgres password)
psql -U postgres -c "CREATE DATABASE ClinicMSAI;"
```

**Mac/Linux:**
```bash
sudo -u postgres psql -c "CREATE DATABASE ClinicMSAI;"
```

## Step 5: Configure Environment Variables

Create a `.env` file in the project root directory with the following content:

```env
# Django Secret Key - Required for security
SESSION_SECRET=django-insecure-@k9m#p2v$x8w!q5t&n7r*j6h+f4d-clinic-management-2024

# Debug Mode - Set to True for local development
DEBUG=True

# PostgreSQL Database Configuration (Option 1: Individual variables)
PGDATABASE=ClinicMSAI
PGUSER=postgres
PGPASSWORD=YOUR_POSTGRES_PASSWORD_HERE
PGHOST=localhost
PGPORT=5432

# PostgreSQL Database Configuration (Option 2: Single URL - comment out PG* variables above if using this)
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ClinicMSAI

# Allowed Hosts (comma-separated, only used when DEBUG=False)
ALLOWED_HOSTS=localhost,127.0.0.1

# Optional: For AI features
# GEMINI_API_KEY=your-gemini-api-key
# OPENAI_API_KEY=your-openai-api-key
```

> **IMPORTANT:** Replace `YOUR_POSTGRES_PASSWORD_HERE` with your actual PostgreSQL password!

### How to Generate a Secure SESSION_SECRET (Optional)

For production, generate a random secret key:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> **Note:** The `manage.py` file is already configured to automatically load environment variables from the `.env` file using `python-dotenv`.

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

---

## Using the Admin Panel

The Django Admin Panel is the control center for managing your clinic system.

### Accessing the Admin Panel

1. **Start the development server** (see Quick Start above)
2. **Open your browser** and go to: http://127.0.0.1:8000/admin
3. **Login** with your admin credentials:
   - Username: `admin`
   - Password: `admin123`

### What You Can Do in the Admin Panel

#### 1. User Management

**Create Staff Accounts:**
1. Click **Accounts** → **Users** → **Add User**
2. Fill in the details:
   - Username
   - Email
   - Password
   - Role (Admin, Doctor, Nurse, Receptionist, Finance, Pharmacy)
3. Click **Save**

**Manage User Roles:**
- Edit existing users to change their roles and permissions
- Activate/deactivate user accounts
- Reset user passwords

#### 2. System Configuration

**Setup Clinic Information:**
1. Navigate to **Setup App** → **Clinic Settings**
2. Configure:
   - Clinic name, address, contact details
   - Business hours
   - Default settings

**Configure Panels:**
- Add insurance panels
- Set panel rates and billing rules

#### 3. Data Management

**Patient Records:**
- View all patient records
- Search and filter patients
- Edit patient information

**Consultations:**
- View consultation history
- Manage medical records
- Track patient visits

**Financial Data:**
- View billing records
- Manage payments
- Track invoices

**Pharmacy Inventory:**
- Manage medication stock
- Track dispensing records

#### 4. AI Configuration

**Setup AI Features:**
1. Go to **AI** → **AI Config**
2. Configure AI settings:
   - Enable/disable AI features
   - Set API keys for Gemini or OpenAI
   - Configure AI assistance options

### Admin Panel Best Practices

✅ **Change default password immediately** after first login  
✅ **Create separate accounts** for each staff member  
✅ **Assign appropriate roles** based on job responsibilities  
✅ **Regularly backup** your database  
✅ **Review audit logs** periodically

### Common Admin Tasks

**Quick Reference:**

| Task | Path |
|------|------|
| Create new user | Accounts → Users → Add User |
| View patients | Patients → Patients |
| Check billing | Finance → Billing Records |
| Setup clinic info | Setup App → Clinic Settings |
| Configure AI | AI → AI Config |

---


## Troubleshooting

### PowerShell Execution Policy Error

If you get an error when activating the virtual environment on Windows:
```
.\venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled
```

**Solution:**
```powershell
# Run PowerShell as Administrator, then:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or for a single session only:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
```

**Alternative:** Use Command Prompt instead:
```cmd
venv\Scripts\activate.bat
```

### PostgreSQL Service Not Running

If you encounter `connection refused` errors:

**Check service status:**
```powershell
Get-Service -Name postgresql-x64-18
```

**Start the service:**
```powershell
# Run PowerShell as Administrator
Start-Service -Name postgresql-x64-18
```

**Or use Services GUI:**
1. Press `Win + R`, type `services.msc`, press Enter
2. Find **postgresql-x64-18**
3. Right-click → **Start**

### PostgreSQL Port Already in Use

If pgAdmin shows: `An attempt was made to access a socket in a way forbidden`

**Check what's using port 5432:**
```powershell
netstat -ano | findstr :5432
```

This is usually normal - PostgreSQL server should be running on port 5432. Simply restart pgAdmin.

### Password Authentication Failed

If you get: `password authentication failed for user "postgres"`

**Solutions:**

1. **Verify your password** in the `.env` file matches your PostgreSQL installation password

2. **Reset PostgreSQL password** (PowerShell as Administrator):
```powershell
cd "C:\Program Files\PostgreSQL\18\bin"
.\psql.exe -U postgres -c "ALTER USER postgres WITH PASSWORD 'new_password';"
```

3. **Find saved password in pgAdmin:**
   - pgAdmin stores passwords if you selected "Save password"
   - Check your pgAdmin connection properties

### Environment Variables Not Loading

If Django shows: `SESSION_SECRET environment variable must be set`

**Verify:**
1. Check that `.env` file exists in project root
2. Ensure `python-dotenv` is installed: `pip install python-dotenv`
3. Verify `manage.py` has been updated to load `.env` (should already be configured)
4. Try closing and reopening your terminal/PowerShell window

### Database Connection Error

- Verify PostgreSQL is running (see above)
- Check `.env` file has correct database name (`ClinicMSAI`)
- Ensure database user has correct permissions
- Verify `PGHOST=localhost` and `PGPORT=5432`

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

- Verify `GEMINI_API_KEY` or `OPENAI_API_KEY` is set correctly in `.env`
- Check AI configuration in Admin → AI Config

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
