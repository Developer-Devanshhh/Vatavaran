#!/usr/bin/env python
"""
Verification script for Vatavaran Django project setup.
Run this to verify the project structure and configuration.
"""

import os
import sys
from pathlib import Path

def check_directory_structure():
    """Verify required directories exist."""
    print("Checking directory structure...")
    required_dirs = [
        'vatavaran_server',
        'api',
        'api/nlp',
        'models',
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} - MISSING")
            return False
    return True

def check_required_files():
    """Verify required files exist."""
    print("\nChecking required files...")
    required_files = [
        'manage.py',
        'requirements.txt',
        'vatavaran_server/settings.py',
        'vatavaran_server/urls.py',
        'api/views.py',
        'api/urls.py',
        'api/nlp/__init__.py',
        '.env.example',
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} - MISSING")
            return False
    return True

def check_django_config():
    """Verify Django configuration."""
    print("\nChecking Django configuration...")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vatavaran_server.settings')
        import django
        django.setup()
        from django.conf import settings
        
        # Check installed apps
        if 'api' in settings.INSTALLED_APPS:
            print("  ✓ 'api' app installed")
        else:
            print("  ✗ 'api' app not in INSTALLED_APPS")
            return False
            
        if 'rest_framework' in settings.INSTALLED_APPS:
            print("  ✓ 'rest_framework' installed")
        else:
            print("  ✗ 'rest_framework' not in INSTALLED_APPS")
            return False
        
        # Check custom settings
        if hasattr(settings, 'WEATHERAPI_KEY'):
            print("  ✓ WEATHERAPI_KEY configured")
        else:
            print("  ✗ WEATHERAPI_KEY not configured")
            return False
            
        if hasattr(settings, 'MODEL_DIR'):
            print("  ✓ MODEL_DIR configured")
        else:
            print("  ✗ MODEL_DIR not configured")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ Django configuration error: {e}")
        return False

def check_url_routing():
    """Verify URL routing is configured."""
    print("\nChecking URL routing...")
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vatavaran_server.settings')
        import django
        django.setup()
        from django.urls import resolve
        from django.urls.exceptions import Resolver404
        
        try:
            match = resolve('/api/predict/')
            print(f"  ✓ /api/predict/ routes to {match.func.__name__}")
            return True
        except Resolver404:
            print("  ✗ /api/predict/ route not found")
            return False
    except Exception as e:
        print(f"  ✗ URL routing error: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Vatavaran Django Project Setup Verification")
    print("=" * 60)
    
    checks = [
        check_directory_structure(),
        check_required_files(),
        check_django_config(),
        check_url_routing(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✓ All checks passed! Setup is complete.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure environment variables")
        print("2. Place model artifacts in the models/ directory")
        print("3. Run: python manage.py runserver")
        return 0
    else:
        print("✗ Some checks failed. Please review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
