#!/usr/bin/env python
"""Script to set admin password"""
import os
import django
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_management.settings')
django.setup()

from accounts.models import User

# Set password for admin user
try:
    user = User.objects.get(username='admin')
    user.set_password('admin123')
    user.save()
    print("[SUCCESS] Admin password set successfully!")
    print("Username: admin")
    print("Password: admin123")
except User.DoesNotExist:
    print("[ERROR] Admin user not found!")
