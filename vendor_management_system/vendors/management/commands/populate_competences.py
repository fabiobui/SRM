"""
Management command per popolare le competenze iniziali dei fornitori.
Uso: python manage.py populate_competences
"""
from django.core.management.base import BaseCommand
from vendor_management_system.vendors.models import Competence


class Command(BaseCommand):
    help = 'Popola le competenze iniziali dei fornitori'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Inizio popolamento competenze...'))
        
        competences_data = [
            # Sicurezza
            {
                'code': 'RSPP',
                'name': 'Qualifica RSPP',
                'description': 'Responsabile del Servizio di Prevenzione e Protezione',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': True,
            },
            {
                'code': 'ASPP',
                'name': 'ASPP',
                'description': 'Addetto al Servizio di Prevenzione e Protezione',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': False,
            },
            {
                'code': 'COORD_SICUR',
                'name': 'Qualifica Coord. Sicurezza Cantieri',
                'description': 'Coordinatore per la sicurezza nei cantieri',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': False,
            },
            {
                'code': 'ATEX',
                'name': 'ATEX',
                'description': 'Atmosfere Esplosive - Direttiva ATEX',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'PREV_INCENDI',
                'name': 'Tecnico abilitato prevenzione Incendi - (818)',
                'description': 'Tecnico per la prevenzione incendi ai sensi del DM 818',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': False,
            },
            {
                'code': 'PROG_ANTINC',
                'name': 'Progettista antincendio',
                'description': 'Professionista abilitato alla progettazione antincendio',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': False,
            },
            {
                'code': 'FUNC_SAFETY',
                'name': 'Functional Safety Expert',
                'description': 'Esperto di sicurezza funzionale',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'HAZOP_CHAIR',
                'name': 'HAZOP SIL Chairman',
                'description': 'Chairman per analisi HAZOP e SIL',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'HAZOP_SCRIBE',
                'name': 'HAZOP SIL Scribe',
                'description': 'Scribe per analisi HAZOP e SIL',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'QRA_FERA',
                'name': 'QRA/FERA',
                'description': 'Quantitative Risk Assessment / Fire and Explosion Risk Analysis',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'REQ_FORMATORE',
                'name': 'Requisito formatore per la sicurezza',
                'description': 'Requisiti per formatore in materia di salute e sicurezza sul lavoro',
                'competence_category': 'SAFETY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            
            # Tecnico
            {
                'code': 'DIR_LAVORI',
                'name': 'Direzione Lavori',
                'description': 'Abilitazione alla direzione lavori',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': False,
                'renewal_period_months': None,
                'is_mandatory': False,
            },
            {
                'code': 'CONSUL_MERC',
                'name': 'Consul. Merci Pericolose',
                'description': 'Consulente per il trasporto di merci pericolose',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': False,
            },
            {
                'code': 'TLS_ASL',
                'name': 'TLS/ASL tecnico laser',
                'description': 'Tecnico laser secondo normativa TLS/ASL',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'IGIENISTA',
                'name': 'Igienista industriale certificato',
                'description': 'Certificazione come igienista industriale',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'RESP_AMIANTO',
                'name': 'Resp. Amianto',
                'description': 'Responsabile gestione amianto',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 24,
                'is_mandatory': False,
            },
            {
                'code': 'RAM',
                'name': 'RAM Analysis',
                'description': 'Reliability, Availability and Maintainability Analysis',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'ACUSTICA',
                'name': 'Tecnico competente in acustica',
                'description': 'Tecnico competente in acustica ambientale',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': False,
            },
            {
                'code': 'VERIFICA_ITP',
                'name': 'Verifica ITP',
                'description': 'Verifica Inspection and Test Plan',
                'competence_category': 'TECHNICAL',
                'requires_certification': True,
                'requires_renewal': False,
                'renewal_period_months': None,
                'is_mandatory': False,
            },
            
            # Energia
            {
                'code': 'ENERGY_MAN',
                'name': 'Energy manager',
                'description': 'Energy Manager certificato',
                'competence_category': 'ENERGY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 12,
                'is_mandatory': False,
            },
            {
                'code': 'EGE',
                'name': 'Esperto Gestione Energia (EGE)',
                'description': 'Esperto in Gestione dell\'Energia certificato UNI CEI 11339',
                'competence_category': 'ENERGY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 48,
                'is_mandatory': False,
            },
            {
                'code': 'MOBILITY_MAN',
                'name': 'Mobility Manager',
                'description': 'Mobility Manager aziendale',
                'competence_category': 'ENERGY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 12,
                'is_mandatory': False,
            },
            
            # Qualità/Ergonomia
            {
                'code': 'ERGONOMO',
                'name': 'Qualific. Ergonomo europeo',
                'description': 'Ergonomo certificato secondo standard europei',
                'competence_category': 'QUALITY',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 60,
                'is_mandatory': False,
            },
            
            # Audit e Certificazioni
            {
                'code': 'AUD_14001',
                'name': 'AUDITOR 14001',
                'description': 'Auditor per sistemi di gestione ambientale ISO 14001',
                'competence_category': 'AUDIT',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'AUD_45001',
                'name': 'AUDITOR 45001',
                'description': 'Auditor per sistemi di gestione salute e sicurezza ISO 45001',
                'competence_category': 'AUDIT',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'AUD_9001',
                'name': 'AUDITOR 9001',
                'description': 'Auditor per sistemi di gestione qualità ISO 9001',
                'competence_category': 'AUDIT',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'AUD_50001',
                'name': 'AUDITOR 50001',
                'description': 'Auditor per sistemi di gestione energia ISO 50001',
                'competence_category': 'AUDIT',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
            {
                'code': 'AUD_SGS_PIR',
                'name': 'AUDITOR SGS PIR (prev. incidenti rilevanti)',
                'description': 'Auditor per sistemi di gestione sicurezza e prevenzione incidenti rilevanti',
                'competence_category': 'AUDIT',
                'requires_certification': True,
                'requires_renewal': True,
                'renewal_period_months': 36,
                'is_mandatory': False,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for data in competences_data:
            competence, created = Competence.objects.update_or_create(
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'description': data.get('description', ''),
                    'competence_category': data['competence_category'],
                    'requires_certification': data['requires_certification'],
                    'requires_renewal': data['requires_renewal'],
                    'renewal_period_months': data.get('renewal_period_months'),
                    'is_mandatory': data.get('is_mandatory', False),
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Creata competenza: {competence.code} - {competence.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Aggiornata competenza: {competence.code} - {competence.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Popolamento completato!\n'
                f'   - Competenze create: {created_count}\n'
                f'   - Competenze aggiornate: {updated_count}\n'
                f'   - Totale: {created_count + updated_count}'
            )
        )
