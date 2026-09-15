#!/usr/bin/env python
"""
Script per importare i DocumentType da CSV
"""
import os
import sys
import django
import csv
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from vendor_management_system.documents.models import DocumentType
from django.utils import timezone

CSV_FILE = "vendor_management_system/documenttype.csv"

def parse_bool(value):
    """Converte 0/1 in boolean"""
    if value in ['1', 1, True, 'True', 'true']:
        return True
    return False

def parse_int(value):
    """Converte stringa in int, gestisce NULL"""
    if value in ['NULL', '', None]:
        return None
    try:
        return int(value)
    except:
        return None

def parse_datetime(value):
    """Converte stringa in datetime"""
    if value in ['NULL', '', None]:
        return timezone.now()
    try:
        # Formato: "2025-11-04 18:49:57.252489"
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    except:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except:
            return timezone.now()

def import_documenttypes():
    """Importa i DocumentType dal CSV"""
    
    if not os.path.exists(CSV_FILE):
        print(f"❌ File non trovato: {CSV_FILE}")
        return
    
    created = 0
    updated = 0
    errors = 0
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        
        for row in reader:
            try:
                # Prepara i dati
                code = row['code'].strip() if row['code'] else None
                
                # Cerca per code invece che per id
                doc_type = None
                if code:
                    try:
                        doc_type = DocumentType.objects.get(code=code)
                    except DocumentType.DoesNotExist:
                        pass
                
                if doc_type:
                    # Aggiorna esistente
                    doc_type.name = row['name'].strip()
                    doc_type.description = row['description'].strip() if row['description'] else ''
                    doc_type.document_category = row['document_category'].strip() if row['document_category'] else 'OTHER'
                    doc_type.is_required = parse_bool(row['is_mandatory'])
                    doc_type.requires_renewal = parse_bool(row['requires_renewal'])
                    doc_type.validity_period_days = parse_int(row['default_validity_days']) or 365
                    doc_type.reminder_days_before = parse_int(row['alert_days_before_expiry']) or 30
                    doc_type.is_active = parse_bool(row['is_active'])
                    doc_type.sort_order = parse_int(row['sort_order']) or 100
                    doc_type.updated_at = parse_datetime(row['updated_at'])
                    doc_type.instructions = row['instructions'] if row['instructions'] not in ['NULL', '', None] else None
                    doc_type.save()
                    
                    updated += 1
                    print(f"♻️  Aggiornato: {doc_type.code} - {doc_type.name}")
                else:
                    # Crea nuovo
                    doc_type = DocumentType(
                        code=code,
                        name=row['name'].strip(),
                        description=row['description'].strip() if row['description'] else '',
                        document_category=row['document_category'].strip() if row['document_category'] else 'OTHER',
                        is_required=parse_bool(row['is_mandatory']),
                        requires_renewal=parse_bool(row['requires_renewal']),
                        validity_period_days=parse_int(row['default_validity_days']) or 365,
                        reminder_days_before=parse_int(row['alert_days_before_expiry']) or 30,
                        is_active=parse_bool(row['is_active']),
                        sort_order=parse_int(row['sort_order']) or 100,
                        created_at=parse_datetime(row['created_at']),
                        updated_at=parse_datetime(row['updated_at']),
                        instructions=row['instructions'] if row['instructions'] not in ['NULL', '', None] else None,
                    )
                    doc_type.save()
                    
                    created += 1
                    print(f"✅ Creato: {doc_type.code} - {doc_type.name}")
                    
            except Exception as e:
                errors += 1
                print(f"❌ Errore su riga {row.get('code', 'N/A')}: {e}")
    
    print(f"\n📊 Riepilogo:")
    print(f"   Creati: {created}")
    print(f"   Aggiornati: {updated}")
    print(f"   Errori: {errors}")
    print(f"   Totale: {created + updated}")

if __name__ == '__main__':
    print("🚀 Avvio import DocumentType...\n")
    import_documenttypes()
    print("\n✅ Import completato!")
