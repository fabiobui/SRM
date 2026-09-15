"""
Script per importare Nazioni (europee principali), Regioni e Province italiane.

Uso:
    python manage.py shell < vendor_management_system/import_geography.py
    oppure:
    python manage.py shell -c "exec(open('vendor_management_system/import_geography.py').read())"
"""

from vendor_management_system.vendors.models import Country, Region, Province

# ============================================================================
# NAZIONI (europee principali + extra)
# ============================================================================
COUNTRIES = [
    ("IT", "Italia", 1),
    ("DE", "Germania", 10),
    ("FR", "Francia", 10),
    ("ES", "Spagna", 10),
    ("GB", "Regno Unito", 10),
    ("AT", "Austria", 20),
    ("BE", "Belgio", 20),
    ("BG", "Bulgaria", 20),
    ("HR", "Croazia", 20),
    ("CY", "Cipro", 20),
    ("CZ", "Repubblica Ceca", 20),
    ("DK", "Danimarca", 20),
    ("EE", "Estonia", 20),
    ("FI", "Finlandia", 20),
    ("GR", "Grecia", 20),
    ("HU", "Ungheria", 20),
    ("IE", "Irlanda", 20),
    ("LV", "Lettonia", 20),
    ("LT", "Lituania", 20),
    ("LU", "Lussemburgo", 20),
    ("MT", "Malta", 20),
    ("NL", "Paesi Bassi", 20),
    ("PL", "Polonia", 20),
    ("PT", "Portogallo", 20),
    ("RO", "Romania", 20),
    ("SK", "Slovacchia", 20),
    ("SI", "Slovenia", 20),
    ("SE", "Svezia", 20),
    ("CH", "Svizzera", 15),
    ("US", "Stati Uniti", 50),
]

print("=== IMPORTAZIONE NAZIONI ===")
for code, name, sort_order in COUNTRIES:
    obj, created = Country.objects.get_or_create(
        code=code,
        defaults={"name": name, "sort_order": sort_order}
    )
    print(f"  {'CREATA' if created else 'ESISTE'}: {code} - {name}")

print(f"Totale nazioni: {Country.objects.count()}\n")

# ============================================================================
# REGIONI ITALIANE
# ============================================================================
italy = Country.objects.get(code="IT")

REGIONS = [
    ("ABR", "Abruzzo"),
    ("BAS", "Basilicata"),
    ("CAL", "Calabria"),
    ("CAM", "Campania"),
    ("EMR", "Emilia-Romagna"),
    ("FVG", "Friuli Venezia Giulia"),
    ("LAZ", "Lazio"),
    ("LIG", "Liguria"),
    ("LOM", "Lombardia"),
    ("MAR", "Marche"),
    ("MOL", "Molise"),
    ("PIE", "Piemonte"),
    ("PUG", "Puglia"),
    ("SAR", "Sardegna"),
    ("SIC", "Sicilia"),
    ("TOS", "Toscana"),
    ("TAA", "Trentino-Alto Adige"),
    ("UMB", "Umbria"),
    ("VDA", "Valle d'Aosta"),
    ("VEN", "Veneto"),
]

print("=== IMPORTAZIONE REGIONI ===")
for code, name in REGIONS:
    obj, created = Region.objects.get_or_create(
        code=code,
        defaults={"name": name, "country": italy}
    )
    print(f"  {'CREATA' if created else 'ESISTE'}: {code} - {name}")

print(f"Totale regioni: {Region.objects.count()}\n")

# ============================================================================
# PROVINCE ITALIANE (tutte le 107 + 3 province autonome / città metropolitane)
# ============================================================================
# Formato: (sigla, nome, codice_regione)
PROVINCES = [
    # Abruzzo
    ("AQ", "L'Aquila", "ABR"),
    ("CH", "Chieti", "ABR"),
    ("PE", "Pescara", "ABR"),
    ("TE", "Teramo", "ABR"),
    # Basilicata
    ("MT", "Matera", "BAS"),
    ("PZ", "Potenza", "BAS"),
    # Calabria
    ("CZ", "Catanzaro", "CAL"),
    ("CS", "Cosenza", "CAL"),
    ("KR", "Crotone", "CAL"),
    ("RC", "Reggio Calabria", "CAL"),
    ("VV", "Vibo Valentia", "CAL"),
    # Campania
    ("AV", "Avellino", "CAM"),
    ("BN", "Benevento", "CAM"),
    ("CE", "Caserta", "CAM"),
    ("NA", "Napoli", "CAM"),
    ("SA", "Salerno", "CAM"),
    # Emilia-Romagna
    ("BO", "Bologna", "EMR"),
    ("FE", "Ferrara", "EMR"),
    ("FC", "Forlì-Cesena", "EMR"),
    ("MO", "Modena", "EMR"),
    ("PR", "Parma", "EMR"),
    ("PC", "Piacenza", "EMR"),
    ("RA", "Ravenna", "EMR"),
    ("RE", "Reggio Emilia", "EMR"),
    ("RN", "Rimini", "EMR"),
    # Friuli Venezia Giulia
    ("GO", "Gorizia", "FVG"),
    ("PN", "Pordenone", "FVG"),
    ("TS", "Trieste", "FVG"),
    ("UD", "Udine", "FVG"),
    # Lazio
    ("FR", "Frosinone", "LAZ"),
    ("LT", "Latina", "LAZ"),
    ("RI", "Rieti", "LAZ"),
    ("RM", "Roma", "LAZ"),
    ("VT", "Viterbo", "LAZ"),
    # Liguria
    ("GE", "Genova", "LIG"),
    ("IM", "Imperia", "LIG"),
    ("SP", "La Spezia", "LIG"),
    ("SV", "Savona", "LIG"),
    # Lombardia
    ("BG", "Bergamo", "LOM"),
    ("BS", "Brescia", "LOM"),
    ("CO", "Como", "LOM"),
    ("CR", "Cremona", "LOM"),
    ("LC", "Lecco", "LOM"),
    ("LO", "Lodi", "LOM"),
    ("MN", "Mantova", "LOM"),
    ("MI", "Milano", "LOM"),
    ("MB", "Monza e della Brianza", "LOM"),
    ("PV", "Pavia", "LOM"),
    ("SO", "Sondrio", "LOM"),
    ("VA", "Varese", "LOM"),
    # Marche
    ("AN", "Ancona", "MAR"),
    ("AP", "Ascoli Piceno", "MAR"),
    ("FM", "Fermo", "MAR"),
    ("MC", "Macerata", "MAR"),
    ("PU", "Pesaro e Urbino", "MAR"),
    # Molise
    ("CB", "Campobasso", "MOL"),
    ("IS", "Isernia", "MOL"),
    # Piemonte
    ("AL", "Alessandria", "PIE"),
    ("AT", "Asti", "PIE"),
    ("BI", "Biella", "PIE"),
    ("CN", "Cuneo", "PIE"),
    ("NO", "Novara", "PIE"),
    ("TO", "Torino", "PIE"),
    ("VB", "Verbano-Cusio-Ossola", "PIE"),
    ("VC", "Vercelli", "PIE"),
    # Puglia
    ("BA", "Bari", "PUG"),
    ("BT", "Barletta-Andria-Trani", "PUG"),
    ("BR", "Brindisi", "PUG"),
    ("FG", "Foggia", "PUG"),
    ("LE", "Lecce", "PUG"),
    ("TA", "Taranto", "PUG"),
    # Sardegna
    ("CA", "Cagliari", "SAR"),
    ("NU", "Nuoro", "SAR"),
    ("OR", "Oristano", "SAR"),
    ("SS", "Sassari", "SAR"),
    ("SU", "Sud Sardegna", "SAR"),
    # Sicilia
    ("AG", "Agrigento", "SIC"),
    ("CL", "Caltanissetta", "SIC"),
    ("CT", "Catania", "SIC"),
    ("EN", "Enna", "SIC"),
    ("ME", "Messina", "SIC"),
    ("PA", "Palermo", "SIC"),
    ("RG", "Ragusa", "SIC"),
    ("SR", "Siracusa", "SIC"),
    ("TP", "Trapani", "SIC"),
    # Toscana
    ("AR", "Arezzo", "TOS"),
    ("FI", "Firenze", "TOS"),
    ("GR", "Grosseto", "TOS"),
    ("LI", "Livorno", "TOS"),
    ("LU", "Lucca", "TOS"),
    ("MS", "Massa-Carrara", "TOS"),
    ("PI", "Pisa", "TOS"),
    ("PT", "Pistoia", "TOS"),
    ("PO", "Prato", "TOS"),
    ("SI", "Siena", "TOS"),
    # Trentino-Alto Adige
    ("BZ", "Bolzano", "TAA"),
    ("TN", "Trento", "TAA"),
    # Umbria
    ("PG", "Perugia", "UMB"),
    ("TR", "Terni", "UMB"),
    # Valle d'Aosta
    ("AO", "Aosta", "VDA"),
    # Veneto
    ("BL", "Belluno", "VEN"),
    ("PD", "Padova", "VEN"),
    ("RO", "Rovigo", "VEN"),
    ("TV", "Treviso", "VEN"),
    ("VE", "Venezia", "VEN"),
    ("VR", "Verona", "VEN"),
    ("VI", "Vicenza", "VEN"),
]

# Cache regioni
region_cache = {r.code: r for r in Region.objects.filter(country=italy)}

print("=== IMPORTAZIONE PROVINCE ===")
for code, name, region_code in PROVINCES:
    region = region_cache.get(region_code)
    if not region:
        print(f"  ERRORE: regione {region_code} non trovata per {code} - {name}")
        continue
    obj, created = Province.objects.get_or_create(
        code=code,
        defaults={"name": name, "region": region}
    )
    print(f"  {'CREATA' if created else 'ESISTE'}: {code} - {name} ({region_code})")

print(f"Totale province: {Province.objects.count()}\n")
print("=== IMPORTAZIONE COMPLETATA ===")
