"""
Script per migrare i servizi esistenti dal vecchio campo ForeignKey service_type
alla nuova relazione ManyToMany attraverso VendorService.

Uso: python vendor_management_system/migrate_existing_services.py
"""
import os
import sys
import django
from pathlib import Path
from django.db import transaction
from termcolor import colored

# --- Setup Django environment ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vendor_management_system.vendors.models import Vendor, VendorService


def migrate_services():
    """Migra i servizi dai vecchi ForeignKey ai nuovi ManyToMany"""
    
    print(colored("\n📦 Migrazione servizi esistenti da service_type a VendorService", "cyan", attrs=["bold"]))
    print(colored("=" * 70, "cyan"))
    
    migrated = 0
    skipped = 0
    errors = 0
    
    with transaction.atomic():
        vendors_with_service = Vendor.objects.filter(service_type__isnull=False)
        total = vendors_with_service.count()
        
        print(colored(f"\n📊 Trovati {total} vendor con service_type compilato\n", "cyan"))
        
        for vendor in vendors_with_service:
            try:
                # Crea VendorService solo se non esiste già
                vs, created = VendorService.objects.get_or_create(
                    vendor=vendor,
                    service_type=vendor.service_type,
                    defaults={
                        'is_primary': True,
                        'notes': 'Migrato automaticamente da service_type'
                    }
                )
                
                if created:
                    migrated += 1
                    print(colored(
                        f"✓ [{migrated:3d}/{total}] Migrato: {vendor.name[:40]:40} → {vendor.service_type.name}",
                        "green"
                    ))
                else:
                    skipped += 1
                    print(colored(
                        f"⊘ [{skipped:3d}/{total}] Saltato (già esistente): {vendor.name[:40]:40}",
                        "yellow"
                    ))
                    
            except Exception as e:
                errors += 1
                print(colored(
                    f"✗ Errore per {vendor.name}: {str(e)}",
                    "red"
                ))
        
        # Riepilogo
        print(colored("\n" + "=" * 70, "cyan"))
        print(colored("📊 RIEPILOGO MIGRAZIONE", "cyan", attrs=["bold"]))
        print(colored("=" * 70, "cyan"))
        print(colored(f"  ✓ Servizi migrati:        {migrated}", "green", attrs=["bold"]))
        print(colored(f"  ⊘ Servizi già esistenti:  {skipped}", "yellow"))
        print(colored(f"  ✗ Errori:                 {errors}", "red"))
        print(colored(f"  📊 Totale elaborati:      {total}", "cyan", attrs=["bold"]))
        print(colored("=" * 70 + "\n", "cyan"))
        
        if errors == 0:
            print(colored("✅ Migrazione completata con successo!", "green", attrs=["bold"]))
        else:
            print(colored(f"⚠️  Migrazione completata con {errors} errori", "yellow", attrs=["bold"]))
        
        return migrated, skipped, errors


if __name__ == "__main__":
    try:
        migrated, skipped, errors = migrate_services()
        
        if errors > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(colored(f"\n❌ Errore durante la migrazione: {str(e)}", "red", attrs=["bold"]))
        import traceback
        traceback.print_exc()
        sys.exit(1)
