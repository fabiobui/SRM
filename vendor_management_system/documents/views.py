from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count
from vendor_management_system.documents.models import Document, DocumentType
from vendor_management_system.vendors.models import Vendor

class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        total_documents = Document.objects.count()
        pending_review = Document.objects.filter(status='UPLOADED').count()
        
        # Count expiring documents
        expiring_soon = 0
        for doc in Document.objects.filter(status__in=['APPROVED', 'UPLOADED']):
            if doc.is_expiring_soon:
                expiring_soon += 1
        
        expired = Document.objects.filter(status='EXPIRED').count()
        
        # Recent documents
        recent_documents = Document.objects.select_related('vendor', 'document_type').order_by('-uploaded_at')[:10]
        
        # Documents by status
        status_counts = Document.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        context.update({
            'total_documents': total_documents,
            'pending_review': pending_review,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'recent_documents': recent_documents,
            'status_counts': status_counts,
        })
        
        return context

class VendorPortalView(LoginRequiredMixin, TemplateView):
    template_name = 'documents/vendor_portal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get first vendor for demo (in production, link to current user)
        try:
            vendor = Vendor.objects.first()
            
            if vendor:
                # Get required document types
                required_types = DocumentType.objects.filter(is_required=True)
                
                # Get vendor's documents
                vendor_documents = Document.objects.filter(vendor=vendor).select_related('document_type')
                
                # Check which documents are missing
                existing_types = vendor_documents.values_list('document_type_id', flat=True)
                missing_types = required_types.exclude(id__in=existing_types)
                
                context.update({
                    'vendor': vendor,
                    'required_types': required_types,
                    'vendor_documents': vendor_documents,
                    'missing_types': missing_types,
                })
            else:
                context['error'] = 'Nessun fornitore trovato. Creare un fornitore nell\'admin.'
            
        except Exception as e:
            context['error'] = f'Errore nel caricamento dati: {str(e)}'
        
        return context
