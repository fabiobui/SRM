"""
Management command per popolare i tipi di documenti comuni richiesti ai fornitori.
Uso: python manage.py populate_document_types
"""
from django.core.management.base import BaseCommand
from vendor_management_system.vendors.models import DocumentType


class Command(BaseCommand):
    help = 'Popola i tipi di documenti comuni richiesti ai fornitori'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Inizio popolamento tipi documento...'))
        
        document_types_data = [
            # Documenti Legali/Amministrativi
            {
                'code': 'DURC',
                'name': 'DURC (Documento Unico di Regolarità Contributiva)',
                'description': 'Documento che attesta la regolarità contributiva INPS e INAIL',
                'document_category': 'LEGAL',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 120,
                'alert_days_before_expiry': 30,
            },
            {
                'code': 'VISURA_CAM',
                'name': 'Visura Camerale',
                'description': 'Certificato della Camera di Commercio',
                'document_category': 'LEGAL',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 180,
                'alert_days_before_expiry': 30,
            },
            {
                'code': 'CERT_PREF',
                'name': 'Certificato Prefettura Antimafia',
                'description': 'Certificazione antimafia rilasciata dalla Prefettura',
                'document_category': 'LEGAL',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 180,
                'alert_days_before_expiry': 45,
            },
            {
                'code': 'CASELLARIO',
                'name': 'Certificato Casellario Giudiziale',
                'description': 'Certificato del casellario giudiziale',
                'document_category': 'LEGAL',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 180,
                'alert_days_before_expiry': 30,
            },
            {
                'code': 'STAT_SOC',
                'name': 'Statuto Societario',
                'description': 'Statuto della società',
                'document_category': 'LEGAL',
                'is_mandatory': True,
                'requires_renewal': False,
                'default_validity_days': None,
                'alert_days_before_expiry': 0,
            },
            {
                'code': 'ATTO_COST',
                'name': 'Atto Costitutivo',
                'description': 'Atto costitutivo della società',
                'document_category': 'LEGAL',
                'is_mandatory': True,
                'requires_renewal': False,
                'default_validity_days': None,
                'alert_days_before_expiry': 0,
            },
            
            # Documenti Finanziari
            {
                'code': 'BILAN_ULT',
                'name': 'Bilancio Ultimo Esercizio',
                'description': 'Bilancio dell\'ultimo esercizio fiscale',
                'document_category': 'FINANCIAL',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 60,
            },
            {
                'code': 'CERT_BANC',
                'name': 'Certificazione Bancaria',
                'description': 'Certificazione della situazione bancaria',
                'document_category': 'FINANCIAL',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 180,
                'alert_days_before_expiry': 30,
            },
            
            # Documenti Assicurativi
            {
                'code': 'RC_PROF',
                'name': 'Assicurazione RC Professionale',
                'description': 'Polizza assicurativa responsabilità civile professionale',
                'document_category': 'INSURANCE',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 60,
            },
            {
                'code': 'RC_OPER',
                'name': 'Assicurazione RC Operativa',
                'description': 'Polizza assicurativa responsabilità civile operativa',
                'document_category': 'INSURANCE',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 60,
            },
            {
                'code': 'INF_INAIL',
                'name': 'Copertura INAIL',
                'description': 'Certificazione copertura assicurativa INAIL',
                'document_category': 'INSURANCE',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 45,
            },
            
            # Documenti di Sicurezza
            {
                'code': 'DVR',
                'name': 'Documento di Valutazione dei Rischi (DVR)',
                'description': 'Documento di valutazione dei rischi secondo D.Lgs 81/2008',
                'document_category': 'SAFETY',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 60,
            },
            {
                'code': 'DUVRI',
                'name': 'DUVRI',
                'description': 'Documento Unico di Valutazione dei Rischi da Interferenze',
                'document_category': 'SAFETY',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 60,
            },
            {
                'code': 'POS',
                'name': 'Piano Operativo di Sicurezza (POS)',
                'description': 'Piano operativo di sicurezza per cantieri',
                'document_category': 'SAFETY',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 45,
            },
            {
                'code': 'FORM_LAVORAT',
                'name': 'Attestati Formazione Lavoratori',
                'description': 'Attestati di formazione dei lavoratori sulla sicurezza',
                'document_category': 'SAFETY',
                'is_mandatory': True,
                'requires_renewal': True,
                'default_validity_days': 1825,  # 5 anni
                'alert_days_before_expiry': 90,
            },
            
            # Certificazioni di Qualità
            {
                'code': 'ISO_9001',
                'name': 'Certificazione ISO 9001',
                'description': 'Certificazione sistema gestione qualità ISO 9001',
                'document_category': 'CERTIFICATION',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 1095,  # 3 anni
                'alert_days_before_expiry': 90,
            },
            {
                'code': 'ISO_14001',
                'name': 'Certificazione ISO 14001',
                'description': 'Certificazione sistema gestione ambientale ISO 14001',
                'document_category': 'CERTIFICATION',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 1095,  # 3 anni
                'alert_days_before_expiry': 90,
            },
            {
                'code': 'ISO_45001',
                'name': 'Certificazione ISO 45001',
                'description': 'Certificazione sistema gestione salute e sicurezza ISO 45001',
                'document_category': 'CERTIFICATION',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 1095,  # 3 anni
                'alert_days_before_expiry': 90,
            },
            {
                'code': 'ISO_50001',
                'name': 'Certificazione ISO 50001',
                'description': 'Certificazione sistema gestione energia ISO 50001',
                'document_category': 'CERTIFICATION',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 1095,  # 3 anni
                'alert_days_before_expiry': 90,
            },
            
            # Documenti Tecnici
            {
                'code': 'REF_TÈCN',
                'name': 'Referenze Tecniche',
                'description': 'Referenze di lavori simili eseguiti',
                'document_category': 'TECHNICAL',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 730,  # 2 anni
                'alert_days_before_expiry': 60,
            },
            {
                'code': 'ORG_TECN',
                'name': 'Organigramma Tecnico',
                'description': 'Organigramma del personale tecnico',
                'document_category': 'TECHNICAL',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 60,
            },
            {
                'code': 'ATTREZZA',
                'name': 'Elenco Attrezzature',
                'description': 'Elenco delle attrezzature disponibili',
                'document_category': 'TECHNICAL',
                'is_mandatory': False,
                'requires_renewal': True,
                'default_validity_days': 365,
                'alert_days_before_expiry': 60,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for data in document_types_data:
            document_type, created = DocumentType.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'description': data.get('description', ''),
                    'document_category': data['document_category'],
                    'is_mandatory': data['is_mandatory'],
                    'requires_renewal': data['requires_renewal'],
                    'default_validity_days': data.get('default_validity_days'),
                    'alert_days_before_expiry': data.get('alert_days_before_expiry', 30),
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Creato tipo documento: {document_type.code} - {document_type.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Aggiornato tipo documento: {document_type.code} - {document_type.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Popolamento completato!\n'
                f'   - Tipi documento creati: {created_count}\n'
                f'   - Tipi documento aggiornati: {updated_count}\n'
                f'   - Totale: {created_count + updated_count}'
            )
        )
