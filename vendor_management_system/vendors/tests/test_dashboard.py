"""
Script di test per la dashboard fornitori

Questo script verifica che:
1. Gli URL siano configurati correttamente
2. Le view rispondano
3. I dati JSON siano nel formato corretto
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from vendor_management_system.vendors.models import Vendor, Category, Address
from rest_framework.authtoken.models import Token


class VendorDashboardTestCase(TestCase):
    """Test per la dashboard fornitori"""
    
    def setUp(self):
        """Setup test data"""
        User = get_user_model()
        
        # Crea utente admin
        self.user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        # Crea token per autenticazione API
        self.token = Token.objects.create(user=self.user)
        
        # Crea categoria
        self.category = Category.objects.create(
            code='TEST',
            name='Test Category',
            is_active=True
        )
        
        # Crea indirizzo
        self.address = Address.objects.create(
            street_address='Via Test 123',
            city='Milano',
            postal_code='20100',
            country='Italia'
        )
        
        # Crea alcuni fornitori di test
        for i in range(5):
            Vendor.objects.create(
                name=f'Fornitore Test {i}',
                email=f'fornitore{i}@test.com',
                category=self.category,
                qualification_status='APPROVED' if i % 2 == 0 else 'PENDING',
                risk_level='LOW' if i % 3 == 0 else 'MEDIUM',
                country='Italia',
                quality_rating_avg=4.0 + (i * 0.2),
                fulfillment_rate=80.0 + (i * 2),
                is_active=True,
                address=self.address
            )
        
        # Setup client
        self.client = Client()
        self.client.login(email='admin@test.com', password='testpass123')
    
    def test_dashboard_view_accessible(self):
        """Test che la dashboard sia accessibile"""
        response = self.client.get('/vendors/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Fornitori')
    
    def test_dashboard_stats_api(self):
        """Test che l'API stats ritorni dati corretti"""
        response = self.client.get(
            '/vendors/dashboard-stats/',
            HTTP_AUTHORIZATION=f'Token {self.token.key}'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verifica struttura risposta
        self.assertIn('by_category', data)
        self.assertIn('by_qualification', data)
        self.assertIn('by_risk', data)
        self.assertIn('by_country', data)
        self.assertIn('by_quality', data)
        self.assertIn('by_fulfillment', data)
        
        # Verifica dati categoria
        self.assertGreater(len(data['by_category']), 0)
        self.assertEqual(data['by_category'][0]['category'], 'Test Category')
        self.assertEqual(data['by_category'][0]['count'], 5)
    
    def test_export_excel_endpoint(self):
        """Test che l'endpoint export Excel sia accessibile"""
        response = self.client.get(
            '/vendors/export-excel/',
            HTTP_AUTHORIZATION=f'Token {self.token.key}'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_export_excel_with_filters(self):
        """Test export Excel con filtri applicati"""
        response = self.client.get(
            '/vendors/export-excel/?qualification_status=APPROVED&risk_level=LOW',
            HTTP_AUTHORIZATION=f'Token {self.token.key}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_context(self):
        """Test che il contesto della dashboard contenga i dati corretti"""
        response = self.client.get('/vendors/dashboard/')
        
        self.assertEqual(response.context['total_vendors'], 5)
        self.assertEqual(response.context['active_vendors'], 5)
        self.assertEqual(response.context['pending_qualification'], 2)
        self.assertEqual(response.context['high_risk_vendors'], 0)
    
    def test_unauthenticated_access(self):
        """Test che gli utenti non autenticati vengano redirezionati"""
        client = Client()
        response = client.get('/vendors/dashboard/')
        
        # Dovrebbe redirezionare al login
        self.assertEqual(response.status_code, 302)
    
    def test_api_without_token(self):
        """Test che l'API richieda autenticazione"""
        client = Client()
        response = client.get('/vendors/dashboard-stats/')
        
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    import django
    import os
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    import unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(VendorDashboardTestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
