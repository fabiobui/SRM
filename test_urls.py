#!/usr/bin/env python3
"""
Script di test per verificare che gli URL Django siano corretti
quando l'applicazione è servita sotto /fornitori
"""

import os
import django
from django.conf import settings

# Configura Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import reverse
from django.test import RequestFactory

def test_urls():
    """Test che gli URL vengano generati correttamente"""
    
    # Crea una factory per le richieste di test
    factory = RequestFactory()
    request = factory.get('/fornitori/')
    
    # Test degli URL principali
    urls_to_test = [
        ('home', 'Home'),
        ('admin:index', 'Admin Index'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('vendor-portal', 'Portale Vendor'),
        ('admin-dashboard', 'Dashboard Admin'),
        ('backoffice-dashboard', 'Dashboard Backoffice'),
        ('document-upload', 'Upload Documento'),
        ('schema-swagger-ui', 'Swagger UI'),
    ]
    
    print("=== TEST URL GENERATION ===")
    print(f"FORCE_SCRIPT_NAME: {settings.FORCE_SCRIPT_NAME}")
    print(f"STATIC_URL: {settings.STATIC_URL}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print()
    
    for url_name, description in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"✅ {description:20} -> {url}")
        except Exception as e:
            print(f"❌ {description:20} -> ERROR: {e}")
    
    print()
    print("=== URL ADMIN ESEMPI ===")
    
    admin_urls = [
        ('admin:vendors_vendor_add', 'Aggiungi Vendor'),
        ('admin:documents_documenttype_add', 'Aggiungi Document Type'),
        ('admin:logout', 'Admin Logout'),
    ]
    
    for url_name, description in admin_urls:
        try:
            url = reverse(url_name)
            print(f"✅ {description:20} -> {url}")
        except Exception as e:
            print(f"❌ {description:20} -> ERROR: {e}")

if __name__ == '__main__':
    test_urls()