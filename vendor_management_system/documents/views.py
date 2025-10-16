from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.http import JsonResponse

from vendor_management_system.core.permissions import (
    AdminRequiredMixin, BackOfficeRequiredMixin, VendorRequiredMixin
)
from vendor_management_system.documents.models import Document, DocumentType
from vendor_management_system.vendors.models import Vendor


class HomeRedirectView(LoginRequiredMixin, View):
    """Redirect dinamico in base al ruolo dell'utente"""
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        if user.is_admin():
            return redirect('admin-dashboard')
        elif user.is_bo_user():
            return redirect('backoffice-dashboard')
        elif user.is_vendor_user():
            return redirect('vendor-portal')
        else:
            return redirect('login')

class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Dashboard completa per amministratori"""
    template_name = 'documents/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics complete per admin
        total_documents = Document.objects.count()
        pending_review = Document.objects.filter(status='UPLOADED').count()
        
        # Count expiring documents
        expiring_soon = 0
        for doc in Document.objects.filter(status__in=['APPROVED', 'UPLOADED']):
            if doc.is_expiring_soon:
                expiring_soon += 1
        
        expired = Document.objects.filter(status='EXPIRED').count()
        
        # Recent documents
        recent_documents = Document.objects.select_related('vendor', 'document_type').order_by('-uploaded_at')[:15]
        
        # Documents by status
        status_counts = Document.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Vendor statistics
        total_vendors = Vendor.objects.count()
        vendors_with_docs = Vendor.objects.filter(documents__isnull=False).distinct().count()
        
        context.update({
            'total_documents': total_documents,
            'pending_review': pending_review,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'recent_documents': recent_documents,
            'status_counts': status_counts,
            'total_vendors': total_vendors,
            'vendors_with_docs': vendors_with_docs,
            'user_role': 'admin',
        })
        
        return context


class BackOfficeDashboardView(BackOfficeRequiredMixin, TemplateView):
    """Dashboard per utenti Back Office"""
    template_name = 'documents/backoffice_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics limitate per BO users
        total_documents = Document.objects.count()
        pending_review = Document.objects.filter(status='UPLOADED').count()
        
        # Recent documents da revisionare
        documents_to_review = Document.objects.filter(
            status='UPLOADED'
        ).select_related('vendor', 'document_type').order_by('-uploaded_at')[:10]
        
        # Vendor senza documenti
        vendors_without_docs = Vendor.objects.filter(documents__isnull=True)[:5]
        
        context.update({
            'total_documents': total_documents,
            'pending_review': pending_review,
            'documents_to_review': documents_to_review,
            'vendors_without_docs': vendors_without_docs,
            'user_role': 'backoffice',
        })
        
        return context


class VendorPortalView(VendorRequiredMixin, TemplateView):
    """Portale per fornitori - accesso solo ai propri documenti"""
    template_name = 'documents/vendor_portal.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Solo documenti del vendor dell'utente loggato
        vendor = self.request.user.vendor
        
        # Get required document types
        required_types = DocumentType.objects.filter(is_required=True)
        
        # Get vendor's documents
        vendor_documents = Document.objects.filter(
            vendor=vendor
        ).select_related('document_type')
        
        # Check which documents are missing
        existing_types = vendor_documents.values_list('document_type_id', flat=True)
        missing_types = required_types.exclude(id__in=existing_types)
        
        # Documenti in scadenza del vendor
        expiring_docs = []
        for doc in vendor_documents.filter(status__in=['APPROVED', 'UPLOADED']):
            if doc.is_expiring_soon:
                expiring_docs.append(doc)
        
        context.update({
            'vendor': vendor,
            'required_types': required_types,
            'vendor_documents': vendor_documents,
            'missing_types': missing_types,
            'expiring_docs': expiring_docs,
            'user_role': 'vendor',
        })
        
        return context


class DocumentUploadView(VendorRequiredMixin, View):
    """Upload documenti - solo per il proprio vendor"""
    
    def post(self, request):
        # Solo il vendor dell'utente loggato
        vendor = request.user.vendor
        document_type_id = request.POST.get('document_type')
        file = request.FILES.get('file')
        issue_date = request.POST.get('issue_date')
        expiry_date = request.POST.get('expiry_date')
        notes = request.POST.get('notes', '')
        
        try:
            document_type = get_object_or_404(DocumentType, id=document_type_id)
            
            # Create or update document per il vendor dell'utente
            document, created = Document.objects.get_or_create(
                vendor=vendor,
                document_type=document_type,
                defaults={
                    'file': file,
                    'issue_date': issue_date if issue_date else None,
                    'expiry_date': expiry_date if expiry_date else None,
                    'notes': notes,
                    'status': 'UPLOADED'
                }
            )
            
            if not created:
                # Update existing document
                document.file = file
                document.issue_date = issue_date if issue_date else None
                document.expiry_date = expiry_date if expiry_date else None
                document.notes = notes
                document.status = 'UPLOADED'
                document.save()
            
            messages.success(request, f'Documento {document_type.name} caricato con successo!')
            
        except Exception as e:
            messages.error(request, f'Errore nel caricamento: {str(e)}')
        
        return redirect('vendor-portal')


class DocumentReviewView(BackOfficeRequiredMixin, View):
    """Approvazione/rifiuto documenti - solo per BO users e Admin"""
    
    def post(self, request, document_id):
        document = get_object_or_404(Document, id=document_id)
        action = request.POST.get('action')  # 'approve' or 'reject'
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            document.status = 'APPROVED'
            messages.success(request, f'Documento {document.document_type.name} approvato!')
        elif action == 'reject':
            document.status = 'REJECTED'
            messages.warning(request, f'Documento {document.document_type.name} rifiutato!')
        
        document.reviewed_by = request.user
        document.reviewed_at = timezone.now()
        if notes:
            document.notes = notes
        document.save()
        
        # Redirect basato sul ruolo
        if request.user.is_admin():
            return redirect('admin-dashboard')
        else:
            return redirect('backoffice-dashboard')
