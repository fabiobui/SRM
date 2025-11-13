// Global variables
let allVendors = [];
let filteredVendors = [];
let activeFilters = {
    regions: [],
    provinces: [],
    vendor_types: [],
    ico_consultant: null, // null, true, or false
    competencies: [],
    certifications: []
};
let advancedFilters = []; // Array of {field, operator, value}
let filterRowCounter = 0;
let charts = {};
let allProvinces = [];

// Available filter fields configuration
const filterFields = {
    'name': { label: 'Nome', type: 'text' },
    'vendor_code': { label: 'Codice Fornitore', type: 'text' },
    'vendor_type': { label: 'Tipo Fornitore', type: 'select', options: ['Società', 'Professionista', 'Dipendente', 'Dipendente + Libero professionista', 'Disoccupato', 'Libero Professionista', 'Presso Studio', 'Prestazione Occasionale', 'Società/professionista', 'Internazionale'] },
    'email': { label: 'Email', type: 'text' },
    'phone': { label: 'Telefono', type: 'text' },
    'vat_number': { label: 'Partita IVA', type: 'text' },
    'fiscal_code': { label: 'Codice Fiscale', type: 'text' },
    'qualification_status': { label: 'Stato Qualifica', type: 'select', options: ['PENDING', 'APPROVED', 'REJECTED'] },
    'vendor_final_evaluation': { label: 'Valutazione Finale', type: 'select', options: ['DA VALUTARE', 'NEGATIVO', 'POSITIVO', 'MOLTO POSITIVO'] },
    'quality_rating_avg': { label: 'Valutazione Qualità', type: 'number' },
    'fulfillment_rate': { label: 'Tasso Adempimento', type: 'number' },
    'is_active': { label: 'Attivo', type: 'boolean' },
    'is_ico_consultant': { label: 'Consulente ICO', type: 'boolean' },
    'contractual_status': { label: 'Stato Contrattuale', type: 'select', options: ['00', '02', '03', '04', '05', '06', '99'] },
    'address.city': { label: 'Città', type: 'text' },
    'address.region': { label: 'Regione', type: 'text' },
    'address.state_province': { label: 'Provincia', type: 'text' },
    'address.country': { label: 'Paese', type: 'text' },
    'category.name': { label: 'Categoria', type: 'text' },
    'service_type.name': { label: 'Tipo Servizio', type: 'text' }
};

// Operator options by field type
const operatorsByType = {
    'text': [
        { value: 'contains', label: 'contiene' },
        { value: 'not_contains', label: 'non contiene' },
        { value: 'equals', label: 'è uguale a' },
        { value: 'not_equals', label: 'è diverso da' },
        { value: 'starts_with', label: 'inizia con' },
        { value: 'ends_with', label: 'finisce con' },
        { value: 'is_empty', label: 'è vuoto' },
        { value: 'is_not_empty', label: 'non è vuoto' }
    ],
    'number': [
        { value: 'equals', label: 'è uguale a' },
        { value: 'not_equals', label: 'è diverso da' },
        { value: 'greater_than', label: 'è maggiore di' },
        { value: 'less_than', label: 'è minore di' },
        { value: 'greater_or_equal', label: 'è maggiore o uguale a' },
        { value: 'less_or_equal', label: 'è minore o uguale a' },
        { value: 'is_empty', label: 'è vuoto' },
        { value: 'is_not_empty', label: 'non è vuoto' }
    ],
    'select': [
        { value: 'equals', label: 'è uguale a' },
        { value: 'not_equals', label: 'è diverso da' },
        { value: 'is_empty', label: 'è vuoto' },
        { value: 'is_not_empty', label: 'non è vuoto' }
    ],
    'boolean': [
        { value: 'is_true', label: 'è vero' },
        { value: 'is_false', label: 'è falso' }
    ]
};

// Italian Provinces mapping to Regions
const provinceRegionMap = {
    'Agrigento': 'Sicilia', 'Alessandria': 'Piemonte', 'Ancona': 'Marche', 'Aosta': "Valle d'Aosta",
    "L'Aquila": 'Abruzzo', 'Arezzo': 'Toscana', 'Ascoli Piceno': 'Marche', 'Asti': 'Piemonte',
    'Avellino': 'Campania', 'Bari': 'Puglia', 'Barletta-Andria-Trani': 'Puglia', 'Belluno': 'Veneto',
    'Benevento': 'Campania', 'Bergamo': 'Lombardia', 'Biella': 'Piemonte', 'Bologna': 'Emilia-Romagna',
    'Bolzano': 'Trentino-Alto Adige', 'Brescia': 'Lombardia', 'Brindisi': 'Puglia', 'Cagliari': 'Sardegna',
    'Caltanissetta': 'Sicilia', 'Campobasso': 'Molise', 'Caserta': 'Campania', 'Catania': 'Sicilia',
    'Catanzaro': 'Calabria', 'Chieti': 'Abruzzo', 'Como': 'Lombardia', 'Cosenza': 'Calabria',
    'Cremona': 'Lombardia', 'Crotone': 'Calabria', 'Cuneo': 'Piemonte', 'Enna': 'Sicilia',
    'Fermo': 'Marche', 'Ferrara': 'Emilia-Romagna', 'Firenze': 'Toscana', 'Foggia': 'Puglia',
    'Forlì-Cesena': 'Emilia-Romagna', 'Frosinone': 'Lazio', 'Genova': 'Liguria',
    'Gorizia': 'Friuli-Venezia Giulia', 'Grosseto': 'Toscana', 'Imperia': 'Liguria', 'Isernia': 'Molise',
    'La Spezia': 'Liguria', 'Latina': 'Lazio', 'Lecce': 'Puglia', 'Lecco': 'Lombardia',
    'Livorno': 'Toscana', 'Lodi': 'Lombardia', 'Lucca': 'Toscana', 'Macerata': 'Marche',
    'Mantova': 'Lombardia', 'Massa-Carrara': 'Toscana', 'Matera': 'Basilicata',
    'Messina': 'Sicilia', 'Milano': 'Lombardia', 'Modena': 'Emilia-Romagna', 'Monza e Brianza': 'Lombardia',
    'Napoli': 'Campania', 'Novara': 'Piemonte', 'Nuoro': 'Sardegna', 'Oristano': 'Sardegna',
    'Padova': 'Veneto', 'Palermo': 'Sicilia', 'Parma': 'Emilia-Romagna', 'Pavia': 'Lombardia',
    'Perugia': 'Umbria', 'Pesaro e Urbino': 'Marche', 'Pescara': 'Abruzzo', 'Piacenza': 'Emilia-Romagna',
    'Pisa': 'Toscana', 'Pistoia': 'Toscana', 'Pordenone': 'Friuli-Venezia Giulia', 'Potenza': 'Basilicata',
    'Prato': 'Toscana', 'Ragusa': 'Sicilia', 'Ravenna': 'Emilia-Romagna', 'Reggio Calabria': 'Calabria',
    'Reggio Emilia': 'Emilia-Romagna', 'Rieti': 'Lazio', 'Rimini': 'Emilia-Romagna', 'Roma': 'Lazio',
    'Rovigo': 'Veneto', 'Salerno': 'Campania', 'Sassari': 'Sardegna', 'Savona': 'Liguria',
    'Siena': 'Toscana', 'Siracusa': 'Sicilia', 'Sondrio': 'Lombardia', 'Sud Sardegna': 'Sardegna',
    'Taranto': 'Puglia', 'Teramo': 'Abruzzo', 'Terni': 'Umbria', 'Torino': 'Piemonte',
    'Trapani': 'Sicilia', 'Trento': 'Trentino-Alto Adige', 'Treviso': 'Veneto',
    'Trieste': 'Friuli-Venezia Giulia', 'Udine': 'Friuli-Venezia Giulia', 'Varese': 'Lombardia',
    'Venezia': 'Veneto', 'Verbano-Cusio-Ossola': 'Piemonte', 'Vercelli': 'Piemonte',
    'Verona': 'Veneto', 'Vibo Valentia': 'Calabria', 'Vicenza': 'Veneto', 'Viterbo': 'Lazio'
};

// Initialize dashboard
function initDashboard(chartDataJson, vendorsDataJson) {
    allVendors = vendorsDataJson;
    filteredVendors = [...allVendors];
    
    // Salva i dati originali per ricalcolare i grafici
    window.originalChartData = chartDataJson;
    
    createVendorTypeChart(chartDataJson.by_vendor_type);
    createIcoConsultantChart(chartDataJson.by_ico_consultant);
    createRegionChart(chartDataJson.by_region);
    createProvinceChart(chartDataJson.by_province || []);
    createCompetenciesChart(chartDataJson.by_competencies || []);
    createCertificationsChart(chartDataJson.by_certifications || []);
    
    renderVendorsTable();
    updateStatistics();
    
    document.getElementById('search-input').addEventListener('input', filterVendors);
}

// Funzione per aggiornare tutti i grafici in base ai filtri attivi
function updateAllCharts() {
    // Calcola i nuovi dati per ogni grafico in base ai vendor filtrati
    updateVendorTypeChart();
    updateIcoConsultantChart();
    updateRegionChart();
    updateProvinceChart();
    updateCompetenciesChart();
    updateCertificationsChart();
}

// Funzione per aggiornare le statistiche in alto
function updateStatistics() {
    const totalVendors = allVendors.length;
    const activeVendors = allVendors.filter(v => v.is_active === true).length;
    const selectedVendors = filteredVendors.length;
    
    // Filtra i fornitori positivi TRA QUELLI SELEZIONATI
    const positiveVendors = filteredVendors.filter(v => {
        const evaluation = v.vendor_final_evaluation;
        return evaluation && (evaluation === 'Positivo' || evaluation === 'Molto Positivo');
    }).length;
    
    document.getElementById('total-vendors').textContent = totalVendors;
    document.getElementById('active-vendors').textContent = activeVendors;
    document.getElementById('selected-vendors').textContent = selectedVendors;
    document.getElementById('positive-vendors').textContent = positiveVendors;
}

// Funzione per ricalcolare i dati del grafico Tipo Fornitore
function updateVendorTypeChart() {
    const vendorTypeCounts = {};
    
    // Filtra i vendor escludendo il filtro vendor_types per calcolare il grafico
    const vendorsWithoutTypeFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO vendor_types
        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }
        
        if (activeFilters.regions.length > 0) {
            const vendorRegion = vendor.address?.region || 'Non Specificato';
            if (!activeFilters.regions.includes(vendorRegion)) return false;
        }
        
        if (activeFilters.provinces.length > 0) {
            const vendorProvince = vendor.address?.state_province || 'Non Specificato';
            if (!activeFilters.provinces.includes(vendorProvince)) return false;
        }
        
        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.some(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }
        
        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.some(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }
        
        // Apply advanced filters
        if (advancedFilters.length > 0) {
            for (const filter of advancedFilters) {
                if (!applyAdvancedFilterToVendor(vendor, filter)) {
                    return false;
                }
            }
        }
        
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        if (searchTerm) {
            const searchableText = [
                vendor.vendor_code, vendor.name, vendor.email,
                vendor.vendor_type, vendor.service_type?.parent,
                vendor.category?.name || vendor.category, vendor.address?.region,
                vendor.address?.city, vendor.address?.state_province,
                vendor.vat_number, vendor.fiscal_code,
                vendor.competences?.join(' ')
            ].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    vendorsWithoutTypeFilter.forEach(v => {
        const type = v.vendor_type || 'Non Specificato';
        vendorTypeCounts[type] = (vendorTypeCounts[type] || 0) + 1;
    });
    
    const vendorTypeMap = {
        'SUPPLIER': 'Fornitore',
        'CONTRACTOR': 'Appaltatore',
        'CONSULTANT': 'Consulente',
        'SERVICE_PROVIDER': 'Fornitore di Servizi'
    };
    
    const labels = Object.keys(vendorTypeCounts).map(key => vendorTypeMap[key] || key);
    const data = Object.values(vendorTypeCounts);
    
    // Evidenzia le selezioni attive
    const backgroundColors = labels.map((label, index) => {
        const originalKey = Object.keys(vendorTypeCounts)[index];
        return activeFilters.vendor_types.includes(originalKey) ? '#20c997' : ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6f42c1'][index % 6];
    });
    
    charts.vendorType.data.labels = labels;
    charts.vendorType.data.datasets[0].data = data;
    charts.vendorType.data.datasets[0].backgroundColor = backgroundColors;
    charts.vendorType.update();
}

// Funzione per ricalcolare i dati del grafico ICO Consultant
function updateIcoConsultantChart() {
    // Filtra i vendor escludendo il filtro ico_consultant per calcolare il grafico
    const vendorsWithoutIcoFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO ico_consultant
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }
        
        if (activeFilters.regions.length > 0) {
            const vendorRegion = vendor.address?.region || 'Non Specificato';
            if (!activeFilters.regions.includes(vendorRegion)) return false;
        }
        
        if (activeFilters.provinces.length > 0) {
            const vendorProvince = vendor.address?.state_province || 'Non Specificato';
            if (!activeFilters.provinces.includes(vendorProvince)) return false;
        }
        
        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.some(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }
        
        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.some(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }
        
        // Apply advanced filters
        if (advancedFilters.length > 0) {
            for (const filter of advancedFilters) {
                if (!applyAdvancedFilterToVendor(vendor, filter)) {
                    return false;
                }
            }
        }
        
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        if (searchTerm) {
            const searchableText = [
                vendor.vendor_code, vendor.name, vendor.email,
                vendor.vendor_type, vendor.service_type?.parent,
                vendor.category?.name || vendor.category, vendor.address?.region,
                vendor.address?.city, vendor.address?.state_province,
                vendor.vat_number, vendor.fiscal_code,
                vendor.competences?.join(' ')
            ].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    const icoCount = vendorsWithoutIcoFilter.filter(v => v.is_ico_consultant === true).length;
    const nonIcoCount = vendorsWithoutIcoFilter.filter(v => v.is_ico_consultant === false).length;
    
    charts.icoConsultant.data.datasets[0].data = [icoCount, nonIcoCount];
    
    // Evidenzia la selezione attiva
    charts.icoConsultant.data.datasets[0].backgroundColor = [
        activeFilters.ico_consultant === true ? '#20c997' : '#28a745',
        activeFilters.ico_consultant === false ? '#20c997' : '#6c757d'
    ];
    
    charts.icoConsultant.update();
}

// Funzione per ricalcolare i dati del grafico Regioni
function updateRegionChart() {
    const regionCounts = {};
    
    // Filtra i vendor escludendo il filtro regioni per calcolare il grafico
    const vendorsWithoutRegionFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO regioni e province
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }
        
        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }
        
        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.some(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }
        
        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.some(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }
        
        // Apply advanced filters
        if (advancedFilters.length > 0) {
            for (const filter of advancedFilters) {
                if (!applyAdvancedFilterToVendor(vendor, filter)) {
                    return false;
                }
            }
        }
        
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        if (searchTerm) {
            const searchableText = [
                vendor.vendor_code, vendor.name, vendor.email,
                vendor.vendor_type, vendor.service_type?.parent,
                vendor.category?.name || vendor.category, vendor.address?.region,
                vendor.address?.city, vendor.address?.state_province,
                vendor.vat_number, vendor.fiscal_code,
                vendor.competences?.join(' ')
            ].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    vendorsWithoutRegionFilter.forEach(v => {
        const region = v.address?.region || 'Non Specificato';
        regionCounts[region] = (regionCounts[region] || 0) + 1;
    });
    
    const labels = Object.keys(regionCounts);
    const data = Object.values(regionCounts);
    
    // Evidenzia le selezioni attive
    const backgroundColors = labels.map(label => 
        activeFilters.regions.includes(label) ? '#20c997' : '#17a2b8'
    );
    
    charts.region.data.labels = labels;
    charts.region.data.datasets[0].data = data;
    charts.region.data.datasets[0].backgroundColor = backgroundColors;
    charts.region.update();
}

// Funzione per ricalcolare i dati del grafico Competenze
function updateCompetenciesChart() {
    const competencyCounts = {};
    
    // Filtra i vendor escludendo il filtro competenze per calcolare il grafico
    const vendorsWithoutCompetencyFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO competenze
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }
        
        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }
        
        if (activeFilters.regions.length > 0) {
            const vendorRegion = vendor.address?.region || 'Non Specificato';
            if (!activeFilters.regions.includes(vendorRegion)) return false;
        }
        
        if (activeFilters.provinces.length > 0) {
            const vendorProvince = vendor.address?.state_province || 'Non Specificato';
            if (!activeFilters.provinces.includes(vendorProvince)) return false;
        }
        
        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.some(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }
        
        // Apply advanced filters
        if (advancedFilters.length > 0) {
            for (const filter of advancedFilters) {
                if (!applyAdvancedFilterToVendor(vendor, filter)) {
                    return false;
                }
            }
        }
        
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        if (searchTerm) {
            const searchableText = [
                vendor.vendor_code, vendor.name, vendor.email,
                vendor.vendor_type, vendor.service_type?.parent,
                vendor.category?.name || vendor.category, vendor.address?.region,
                vendor.address?.city, vendor.address?.state_province,
                vendor.vat_number, vendor.fiscal_code,
                vendor.competences?.join(' ')
            ].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    vendorsWithoutCompetencyFilter.forEach(v => {
        if (v.competences && Array.isArray(v.competences)) {
            v.competences.forEach(comp => {
                competencyCounts[comp] = (competencyCounts[comp] || 0) + 1;
            });
        }
    });
    
    // Ordina per conteggio e mostra TUTTE le competenze
    const sortedCompetencies = Object.entries(competencyCounts)
        .sort((a, b) => b[1] - a[1]);
    
    const labels = sortedCompetencies.map(([comp]) => comp);
    const data = sortedCompetencies.map(([, count]) => count);
    
    // Evidenzia le selezioni attive
    const backgroundColors = labels.map(label => 
        activeFilters.competencies.includes(label) ? '#20c997' : '#28a745'
    );
    
    charts.competencies.data.labels = labels;
    charts.competencies.data.datasets[0].data = data;
    charts.competencies.data.datasets[0].backgroundColor = backgroundColors;
    charts.competencies.update();
}

// Funzione per ricalcolare i dati del grafico Certificazioni
function updateCertificationsChart() {
    const certificationCounts = {};
    
    // Filtra i vendor escludendo il filtro certificazioni per calcolare il grafico
    const vendorsWithoutCertificationFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO certificazioni
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }
        
        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }
        
        if (activeFilters.regions.length > 0) {
            const vendorRegion = vendor.address?.region || 'Non Specificato';
            if (!activeFilters.regions.includes(vendorRegion)) return false;
        }
        
        if (activeFilters.provinces.length > 0) {
            const vendorProvince = vendor.address?.state_province || 'Non Specificato';
            if (!activeFilters.provinces.includes(vendorProvince)) return false;
        }
        
        if (activeFilters.competencies.length > 0) {
            if (!vendor.competences || !Array.isArray(vendor.competences)) return false;
            const hasMatchingCompetency = vendor.competences.some(comp => 
                activeFilters.competencies.includes(comp)
            );
            if (!hasMatchingCompetency) return false;
        }
        
        // Apply advanced filters
        if (advancedFilters.length > 0) {
            for (const filter of advancedFilters) {
                if (!applyAdvancedFilterToVendor(vendor, filter)) {
                    return false;
                }
            }
        }
        
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        if (searchTerm) {
            const searchableText = [
                vendor.vendor_code, vendor.name, vendor.email,
                vendor.vendor_type, vendor.service_type?.parent,
                vendor.category?.name || vendor.category, vendor.address?.region,
                vendor.address?.city, vendor.address?.state_province,
                vendor.vat_number, vendor.fiscal_code,
                vendor.competences?.join(' '),
                vendor.certifications?.join(' ')
            ].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    vendorsWithoutCertificationFilter.forEach(v => {
        if (v.certifications && Array.isArray(v.certifications)) {
            v.certifications.forEach(cert => {
                certificationCounts[cert] = (certificationCounts[cert] || 0) + 1;
            });
        }
    });
    
    // Ordina per conteggio e mostra TUTTE le certificazioni
    const sortedCertifications = Object.entries(certificationCounts)
        .sort((a, b) => b[1] - a[1]);
    
    const labels = sortedCertifications.map(([cert]) => cert);
    const data = sortedCertifications.map(([, count]) => count);
    
    // Evidenzia le selezioni attive
    const backgroundColors = labels.map(label => 
        activeFilters.certifications.includes(label) ? '#20c997' : '#ffc107'
    );
    
    charts.certifications.data.labels = labels;
    charts.certifications.data.datasets[0].data = data;
    charts.certifications.data.datasets[0].backgroundColor = backgroundColors;
    charts.certifications.update();
}

// Create charts
function createVendorTypeChart(data) {
    const ctx = document.getElementById('vendorTypeChart').getContext('2d');
    const vendorTypeMap = {
        'SUPPLIER': 'Fornitore',
        'CONTRACTOR': 'Appaltatore',
        'CONSULTANT': 'Consulente',
        'SERVICE_PROVIDER': 'Fornitore di Servizi'
    };
    
    charts.vendorType = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => vendorTypeMap[item.type] || item.type || 'Non Specificato'),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6f42c1']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    const label = charts.vendorType.data.labels[activeElements[0].index];
                    const reverseMap = {
                        'Fornitore': 'SUPPLIER',
                        'Appaltatore': 'CONTRACTOR',
                        'Consulente': 'CONSULTANT',
                        'Fornitore di Servizi': 'SERVICE_PROVIDER'
                    };
                    toggleFilter('vendor_types', reverseMap[label] || label);
                }
            },
            plugins: { 
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        afterLabel: function() {
                            return 'Clicca per filtrare';
                        }
                    }
                }
            }
        }
    });
}

function createIcoConsultantChart(data) {
    const ctx = document.getElementById('serviceTypeChart').getContext('2d');
    
    charts.icoConsultant = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Consulenti ICO', 'Altri Fornitori'],
            datasets: [{
                data: [
                    data.find(d => d.is_ico === true)?.count || 0,
                    data.find(d => d.is_ico === false)?.count || 0
                ],
                backgroundColor: ['#28a745', '#6c757d']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    const index = activeElements[0].index;
                    const isIco = index === 0;
                    toggleIcoFilter(isIco);
                }
            },
            plugins: { 
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function createRegionChart(data) {
    const ctx = document.getElementById('regionChart').getContext('2d');
    charts.region = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.region || 'Non Specificato'),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#17a2b8' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('regions', charts.region.data.labels[activeElements[0].index]);
                }
            },
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterLabel: function() {
                            return 'Clicca per filtrare';
                        }
                    }
                }
            }
        }
    });
}

function createProvinceChart(data) {
    const ctx = document.getElementById('provinceChart').getContext('2d');
    
    if (!data || data.length === 0) {
        const provinceCount = {};
        
        allVendors.forEach((vendor) => {
            if (vendor.address && vendor.address.state_province) {
                const province = vendor.address.state_province.trim();
                if (province && province !== 'Non Specificato' && province !== '') {
                    provinceCount[province] = (provinceCount[province] || 0) + 1;
                }
            }
        });
        
        data = Object.entries(provinceCount)
            .map(([province, count]) => ({ province, count }))
            .sort((a, b) => b.count - a.count);
    }
    
    allProvinces = data;
    
    if (data.length === 0) {
        charts.province = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Nessuna provincia nel database'],
                datasets: [{ label: 'Numero Fornitori', data: [0], backgroundColor: '#dc3545' }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: { x: { beginAtZero: true, max: 10 } },
                plugins: { legend: { display: false }, tooltip: { enabled: false } }
            }
        });
        return;
    }
    
    const labels = data.map(item => item.province);
    const values = data.map(item => item.count);
    
    charts.province = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Numero Fornitori',
                data: values,
                backgroundColor: '#6f42c1'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('provinces', charts.province.data.labels[activeElements[0].index]);
                }
            },
            scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Fornitori: ' + context.parsed.x;
                        },
                        afterLabel: function() {
                            return 'Clicca per filtrare';
                        }
                    }
                }
            }
        }
    });
}

function createCompetenciesChart(data) {
    const ctx = document.getElementById('competenciesChart').getContext('2d');
    charts.competencies = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.competency || 'N/A'),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#28a745' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('competencies', charts.competencies.data.labels[activeElements[0].index]);
                }
            },
            scales: { 
                y: { beginAtZero: true, ticks: { stepSize: 1 } },
                x: { 
                    ticks: {
                        maxRotation: 90,
                        minRotation: 45
                    }
                }
            },
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterLabel: function() {
                            return 'Clicca per filtrare';
                        }
                    }
                }
            }
        }
    });
}

function createCertificationsChart(data) {
    const ctx = document.getElementById('certificationsChart').getContext('2d');
    charts.certifications = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.certification || 'N/A'),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#ffc107' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('certifications', charts.certifications.data.labels[activeElements[0].index]);
                }
            },
            scales: { 
                y: { beginAtZero: true, ticks: { stepSize: 1 } },
                x: { 
                    ticks: {
                        maxRotation: 90,
                        minRotation: 45
                    }
                }
            },
            plugins: { 
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterLabel: function() {
                            return 'Clicca per filtrare';
                        }
                    }
                }
            }
        }
    });
}

// Update Province Chart
function updateProvinceChart() {
    // Filtra i vendor escludendo il filtro province per calcolare il grafico
    const vendorsWithoutProvinceFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO province
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }
        
        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }
        
        if (activeFilters.regions.length > 0) {
            const vendorRegion = vendor.address?.region || 'Non Specificato';
            if (!activeFilters.regions.includes(vendorRegion)) return false;
        }
        
        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.some(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }
        
        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.some(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }
        
        // Apply advanced filters
        if (advancedFilters.length > 0) {
            for (const filter of advancedFilters) {
                if (!applyAdvancedFilterToVendor(vendor, filter)) {
                    return false;
                }
            }
        }
        
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        if (searchTerm) {
            const searchableText = [
                vendor.vendor_code, vendor.name, vendor.email,
                vendor.vendor_type, vendor.service_type?.parent,
                vendor.category?.name || vendor.category, vendor.address?.region,
                vendor.address?.city, vendor.address?.state_province,
                vendor.vat_number, vendor.fiscal_code,
                vendor.competences?.join(' ')
            ].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    const provinceCount = {};
    
    vendorsWithoutProvinceFilter.forEach((vendor) => {
        if (vendor.address && vendor.address.state_province) {
            const province = vendor.address.state_province.trim();
            if (province && province !== 'Non Specificato' && province !== '') {
                provinceCount[province] = (provinceCount[province] || 0) + 1;
            }
        }
    });
    
    const sortedProvinces = Object.entries(provinceCount)
        .sort((a, b) => b[1] - a[1]);
    
    const labels = sortedProvinces.map(([province]) => province);
    const values = sortedProvinces.map(([, count]) => count);
    
    charts.province.data.labels = labels;
    charts.province.data.datasets[0].data = values;
    charts.province.data.datasets[0].backgroundColor = labels.map(label => 
        activeFilters.provinces.includes(label) ? '#20c997' : '#6f42c1'
    );
    
    // Mostra badge se ci sono regioni selezionate
    const badge = document.getElementById('province-region-badge');
    if (activeFilters.regions.length > 0) {
        badge.textContent = activeFilters.regions.join(', ');
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
    
    charts.province.update();
}

// Filter functions
function toggleFilter(dimension, value) {
    const index = activeFilters[dimension].indexOf(value);
    if (index > -1) {
        activeFilters[dimension].splice(index, 1);
        if (dimension === 'regions') {
            const provincesToRemove = Object.keys(provinceRegionMap).filter(p => provinceRegionMap[p] === value);
            activeFilters.provinces = activeFilters.provinces.filter(p => !provincesToRemove.includes(p));
        }
    } else {
        activeFilters[dimension].push(value);
    }
    
    updateActiveFiltersDisplay();
    filterVendors();
    updateAllCharts();
}

function toggleIcoFilter(isIco) {
    if (activeFilters.ico_consultant === isIco) {
        activeFilters.ico_consultant = null; // Deseleziona
    } else {
        activeFilters.ico_consultant = isIco;
    }
    
    updateActiveFiltersDisplay();
    filterVendors();
    updateAllCharts();
}

function clearAllFilters() {
    activeFilters = { regions: [], provinces: [], vendor_types: [], ico_consultant: null, competencies: [], certifications: [] };
    advancedFilters = [];
    document.getElementById('search-input').value = '';
    document.getElementById('applied-filters-count').style.display = 'none';
    
    updateActiveFiltersDisplay();
    filterVendors();
    updateAllCharts();
    updateStatistics();
}

function removeFilter(dimension, value) {
    if (dimension === 'ico_consultant') {
        activeFilters.ico_consultant = null;
    } else {
        const index = activeFilters[dimension].indexOf(value);
        if (index > -1) activeFilters[dimension].splice(index, 1);
        
        if (dimension === 'regions') {
            const provincesToRemove = Object.keys(provinceRegionMap).filter(p => provinceRegionMap[p] === value);
            activeFilters.provinces = activeFilters.provinces.filter(p => !provincesToRemove.includes(p));
        }
    }
    
    updateActiveFiltersDisplay();
    filterVendors();
    updateAllCharts();
}

function updateActiveFiltersDisplay() {
    const container = document.getElementById('active-filters-container');
    const row = document.getElementById('active-filters-row');
    const hasFilters = Object.values(activeFilters).some(val => 
        (Array.isArray(val) && val.length > 0) || (val !== null && val !== undefined && !Array.isArray(val))
    );
    
    row.style.display = hasFilters ? 'block' : 'none';
    if (!hasFilters) return;
    
    container.innerHTML = '';
    const filterLabels = {
        'vendor_types': 'Tipo Fornitore',
        'regions': 'Regione',
        'provinces': 'Provincia',
        'competencies': 'Competenza',
        'certifications': 'Certificazione'
    };
    
    Object.entries(activeFilters).forEach(([key, values]) => {
        if (key === 'ico_consultant' && values !== null) {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            const label = values ? 'Consulenti ICO' : 'Altri Fornitori';
            chip.innerHTML = `Tipo: <strong>${label}</strong> <span class="remove" onclick="removeFilter('ico_consultant', null)">✕</span>`;
            container.appendChild(chip);
        } else if (Array.isArray(values)) {
            values.forEach(value => {
                const chip = document.createElement('span');
                chip.className = 'filter-chip';
                chip.innerHTML = `${filterLabels[key]}: <strong>${value}</strong> <span class="remove" onclick="removeFilter('${key}', '${value.replace(/'/g, "\\'")}')">✕</span>`;
                container.appendChild(chip);
            });
        }
    });
}

function filterVendors() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    filteredVendors = allVendors.filter(vendor => {
        // Apply chart-based filters
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }
        
        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }
        
        if (activeFilters.regions.length > 0) {
            const vendorRegion = vendor.address?.region || 'Non Specificato';
            if (!activeFilters.regions.includes(vendorRegion)) return false;
        }
        
        if (activeFilters.provinces.length > 0) {
            const vendorProvince = vendor.address?.state_province || 'Non Specificato';
            if (!activeFilters.provinces.includes(vendorProvince)) return false;
        }
        
        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.some(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }
        
        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.some(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }
        
        // Apply advanced filters
        if (advancedFilters.length > 0) {
            for (const filter of advancedFilters) {
                if (!applyAdvancedFilterToVendor(vendor, filter)) {
                    return false;
                }
            }
        }
        
        // Apply search term
        if (searchTerm) {
            const searchableText = [
                vendor.vendor_code, vendor.name, vendor.email,
                vendor.vendor_type, vendor.service_type?.parent,
                vendor.category?.name || vendor.category, vendor.address?.region,
                vendor.address?.city, vendor.address?.state_province,
                vendor.vat_number, vendor.fiscal_code,
                vendor.competences?.join(' '),
                vendor.certifications?.join(' ')
            ].join(' ').toLowerCase();
            if (!searchableText.includes(searchTerm)) return false;
        }
        
        return true;
    });
    
    renderVendorsTable();
    updateStatistics();
    
    // Aggiorna i grafici solo se c'è un termine di ricerca
    if (searchTerm) {
        updateAllCharts();
    }
    
    // Update advanced filters display
    updateAdvancedFiltersDisplay();
}

function renderVendorsTable() {
    const tbody = document.getElementById('vendors-table-body');
    document.getElementById('filtered-count').textContent = filteredVendors.length;
    document.getElementById('showing-count').textContent = filteredVendors.length;
    
    if (filteredVendors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="text-muted"><i class="fas fa-search fa-2x mb-2"></i><p>Nessun fornitore trovato</p></div></td></tr>';
        return;
    }
    
    const vendorTypeMap = {
        'SUPPLIER': 'Fornitore',
        'CONTRACTOR': 'Appaltatore',
        'CONSULTANT': 'Consulente',
        'SERVICE_PROVIDER': 'Fornitore di Servizi'
    };
    
    tbody.innerHTML = filteredVendors.map(vendor => {
        const region = vendor.address?.region || '<span class="text-muted">N/A</span>';
        const province = vendor.address?.state_province || '<span class="text-muted">N/A</span>';
        const phone = vendor.phone || '<span class="text-muted">N/A</span>';
        const evaluation = vendor.vendor_final_evaluation || 'DA VALUTARE';
        
        // Map evaluation to badge class
        let evaluationBadge = 'bg-secondary';
        if (evaluation === 'MOLTO POSITIVO') evaluationBadge = 'bg-success';
        else if (evaluation === 'POSITIVO') evaluationBadge = 'bg-info';
        else if (evaluation === 'NEGATIVO') evaluationBadge = 'bg-danger';
        else if (evaluation === 'DA VALUTARE') evaluationBadge = 'bg-warning';
        
        const vendorTypeLabel = vendor.vendor_type || '<span class="text-muted">N/A</span>';
        
        return `<tr>
            <td><strong>${vendor.name || 'N/A'}</strong></td>
            <td>${vendorTypeLabel}</td>
            <td><small>${vendor.email || '<span class="text-muted">N/A</span>'}</small></td>
            <td>${phone}</td>
            <td>${region}</td>
            <td>${province}</td>
            <td><span class="badge ${evaluationBadge}">${evaluation}</span></td>
            <td><a href="/admin/vendors/vendor/${vendor.vendor_code}/change/" class="btn btn-sm btn-outline-primary" target="_blank"><i class="fas fa-eye"></i></a></td>
        </tr>`;
    }).join('');
}

function exportToExcel() {
    const params = new URLSearchParams();
    Object.entries(activeFilters).forEach(([key, values]) => {
        if (values.length > 0) params.append(key, values.join(','));
    });
    const searchTerm = document.getElementById('search-input').value;
    if (searchTerm) params.append('search', searchTerm);
    
    window.location.href = `/vendors/export-excel/${params.toString() ? '?' + params.toString() : ''}`;
}

// ===== ADVANCED FILTERS FUNCTIONS =====

function toggleAdvancedFilters() {
    const body = document.getElementById('advanced-filters-body');
    const btn = document.getElementById('toggle-filters-btn');
    
    if (body.style.display === 'none') {
        body.style.display = 'block';
        btn.innerHTML = '<i class="fas fa-chevron-up"></i> Nascondi';
        // Add first filter row if none exist
        if (document.getElementById('filters-container').children.length === 0) {
            addFilterRow();
        }
    } else {
        body.style.display = 'none';
        btn.innerHTML = '<i class="fas fa-chevron-down"></i> Mostra';
    }
}

function addFilterRow() {
    filterRowCounter++;
    const container = document.getElementById('filters-container');
    
    const row = document.createElement('div');
    row.className = 'filter-row';
    row.id = `filter-row-${filterRowCounter}`;
    row.dataset.rowId = filterRowCounter;
    
    // Field selector
    const fieldSelect = document.createElement('select');
    fieldSelect.className = 'form-select form-select-sm filter-field-select';
    fieldSelect.id = `filter-field-${filterRowCounter}`;
    fieldSelect.innerHTML = '<option value="">-- Seleziona Campo --</option>';
    
    for (const [key, config] of Object.entries(filterFields)) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = config.label;
        option.dataset.type = config.type;
        fieldSelect.appendChild(option);
    }
    
    fieldSelect.addEventListener('change', function() {
        updateOperatorOptions(filterRowCounter);
        updateValueInput(filterRowCounter);
    });
    
    // Operator selector
    const operatorSelect = document.createElement('select');
    operatorSelect.className = 'form-select form-select-sm filter-operator-select';
    operatorSelect.id = `filter-operator-${filterRowCounter}`;
    operatorSelect.innerHTML = '<option value="">-- Seleziona Operatore --</option>';
    
    operatorSelect.addEventListener('change', function() {
        updateValueInputVisibility(filterRowCounter);
    });
    
    // Value input
    const valueInput = document.createElement('input');
    valueInput.className = 'form-control form-control-sm filter-value-input';
    valueInput.id = `filter-value-${filterRowCounter}`;
    valueInput.placeholder = 'Valore';
    
    // Remove button
    const removeBtn = document.createElement('button');
    removeBtn.className = 'btn btn-sm btn-danger btn-remove';
    removeBtn.innerHTML = '<i class="fas fa-trash"></i>';
    removeBtn.onclick = function() { removeFilterRow(filterRowCounter); };
    
    row.appendChild(fieldSelect);
    row.appendChild(operatorSelect);
    row.appendChild(valueInput);
    row.appendChild(removeBtn);
    
    container.appendChild(row);
}

function removeFilterRow(rowId) {
    const row = document.getElementById(`filter-row-${rowId}`);
    if (row) {
        row.remove();
    }
}

function updateOperatorOptions(rowId) {
    const fieldSelect = document.getElementById(`filter-field-${rowId}`);
    const operatorSelect = document.getElementById(`filter-operator-${rowId}`);
    
    const selectedOption = fieldSelect.options[fieldSelect.selectedIndex];
    if (!selectedOption || !selectedOption.value) {
        operatorSelect.innerHTML = '<option value="">-- Seleziona Operatore --</option>';
        return;
    }
    
    const fieldType = selectedOption.dataset.type;
    const operators = operatorsByType[fieldType] || operatorsByType['text'];
    
    operatorSelect.innerHTML = '<option value="">-- Seleziona Operatore --</option>';
    operators.forEach(op => {
        const option = document.createElement('option');
        option.value = op.value;
        option.textContent = op.label;
        operatorSelect.appendChild(option);
    });
}

function updateValueInput(rowId) {
    const fieldSelect = document.getElementById(`filter-field-${rowId}`);
    const valueInput = document.getElementById(`filter-value-${rowId}`);
    
    const selectedOption = fieldSelect.options[fieldSelect.selectedIndex];
    if (!selectedOption || !selectedOption.value) {
        return;
    }
    
    const fieldKey = selectedOption.value;
    const fieldConfig = filterFields[fieldKey];
    
    // Clear existing input
    const row = document.getElementById(`filter-row-${rowId}`);
    const oldInput = valueInput;
    
    if (fieldConfig.type === 'select') {
        // Replace with select
        const newSelect = document.createElement('select');
        newSelect.className = 'form-select form-select-sm filter-value-input';
        newSelect.id = `filter-value-${rowId}`;
        newSelect.innerHTML = '<option value="">-- Seleziona Valore --</option>';
        
        fieldConfig.options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt;
            option.textContent = opt;
            newSelect.appendChild(option);
        });
        
        row.replaceChild(newSelect, oldInput);
    } else if (fieldConfig.type === 'boolean') {
        // For boolean, value input is not needed (handled by operator)
        const newInput = document.createElement('input');
        newInput.className = 'form-control form-control-sm filter-value-input';
        newInput.id = `filter-value-${rowId}`;
        newInput.style.display = 'none';
        row.replaceChild(newInput, oldInput);
    } else if (fieldConfig.type === 'number') {
        // Replace with number input
        const newInput = document.createElement('input');
        newInput.type = 'number';
        newInput.className = 'form-control form-control-sm filter-value-input';
        newInput.id = `filter-value-${rowId}`;
        newInput.placeholder = 'Valore numerico';
        newInput.step = '0.01';
        row.replaceChild(newInput, oldInput);
    } else {
        // Text input
        const newInput = document.createElement('input');
        newInput.type = 'text';
        newInput.className = 'form-control form-control-sm filter-value-input';
        newInput.id = `filter-value-${rowId}`;
        newInput.placeholder = 'Valore';
        row.replaceChild(newInput, oldInput);
    }
}

function updateValueInputVisibility(rowId) {
    const operatorSelect = document.getElementById(`filter-operator-${rowId}`);
    const valueInput = document.getElementById(`filter-value-${rowId}`);
    
    const operator = operatorSelect.value;
    const noValueOperators = ['is_empty', 'is_not_empty', 'is_true', 'is_false'];
    
    if (noValueOperators.includes(operator)) {
        valueInput.style.display = 'none';
        valueInput.value = '';
    } else {
        valueInput.style.display = 'block';
    }
}

function applyAdvancedFilters() {
    // Collect all filter rows
    advancedFilters = [];
    const rows = document.querySelectorAll('.filter-row');
    
    rows.forEach(row => {
        const rowId = row.dataset.rowId;
        const field = document.getElementById(`filter-field-${rowId}`).value;
        const operator = document.getElementById(`filter-operator-${rowId}`).value;
        const value = document.getElementById(`filter-value-${rowId}`).value;
        
        if (field && operator) {
            // For operators that don't need a value
            const noValueOperators = ['is_empty', 'is_not_empty', 'is_true', 'is_false'];
            if (noValueOperators.includes(operator) || value) {
                advancedFilters.push({
                    field: field,
                    operator: operator,
                    value: value,
                    label: filterFields[field].label
                });
            }
        }
    });
    
    // Update badge count
    const badge = document.getElementById('applied-filters-count');
    if (advancedFilters.length > 0) {
        badge.textContent = advancedFilters.length;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
    
    // Apply filters
    filterVendors();
    updateAllCharts();
    updateStatistics();
    updateAdvancedFiltersDisplay();
}

function clearAdvancedFilters() {
    advancedFilters = [];
    document.getElementById('filters-container').innerHTML = '';
    filterRowCounter = 0;
    document.getElementById('applied-filters-count').style.display = 'none';
    
    // Re-apply without advanced filters
    filterVendors();
    updateAllCharts();
    updateStatistics();
    updateAdvancedFiltersDisplay();
    
    // Add one empty row
    addFilterRow();
}

function removeAdvancedFilter(index) {
    advancedFilters.splice(index, 1);
    
    // Update badge
    const badge = document.getElementById('applied-filters-count');
    if (advancedFilters.length > 0) {
        badge.textContent = advancedFilters.length;
    } else {
        badge.style.display = 'none';
    }
    
    filterVendors();
    updateAllCharts();
    updateStatistics();
    updateAdvancedFiltersDisplay();
}

function updateAdvancedFiltersDisplay() {
    const container = document.getElementById('active-filters-container');
    const row = document.getElementById('active-filters-row');
    
    // Check if we have any filters (chart filters or advanced filters)
    const hasChartFilters = Object.values(activeFilters).some(val => 
        (Array.isArray(val) && val.length > 0) || (val !== null && val !== undefined && !Array.isArray(val))
    );
    const hasAdvancedFilters = advancedFilters.length > 0;
    
    if (!hasChartFilters && !hasAdvancedFilters) {
        row.style.display = 'none';
        return;
    }
    
    row.style.display = 'block';
    
    // Clear and rebuild
    container.innerHTML = '';
    
    // Add chart filters (existing functionality)
    const filterLabels = {
        'vendor_types': 'Tipo Fornitore',
        'regions': 'Regione',
        'provinces': 'Provincia',
        'competencies': 'Competenza',
        'certifications': 'Certificazione'
    };
    
    Object.entries(activeFilters).forEach(([key, values]) => {
        if (key === 'ico_consultant' && values !== null) {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            const label = values ? 'Consulenti ICO' : 'Altri Fornitori';
            chip.innerHTML = `Tipo: <strong>${label}</strong> <span class="remove" onclick="removeFilter('ico_consultant', null)">✕</span>`;
            container.appendChild(chip);
        } else if (Array.isArray(values)) {
            values.forEach(value => {
                const chip = document.createElement('span');
                chip.className = 'filter-chip';
                chip.innerHTML = `${filterLabels[key]}: <strong>${value}</strong> <span class="remove" onclick="removeFilter('${key}', '${value.replace(/'/g, "\\'")}')">✕</span>`;
                container.appendChild(chip);
            });
        }
    });
    
    // Add advanced filters
    advancedFilters.forEach((filter, index) => {
        const chip = document.createElement('span');
        chip.className = 'applied-filter-badge';
        
        const operatorLabel = getOperatorLabel(filter.operator);
        let displayValue = filter.value;
        
        // For operators that don't show value
        if (['is_empty', 'is_not_empty', 'is_true', 'is_false'].includes(filter.operator)) {
            chip.innerHTML = `
                <span class="filter-label">${filter.label}</span>
                <span class="filter-operator">${operatorLabel}</span>
                <span class="remove" onclick="removeAdvancedFilter(${index})">✕</span>
            `;
        } else {
            chip.innerHTML = `
                <span class="filter-label">${filter.label}</span>
                <span class="filter-operator">${operatorLabel}</span>
                <span class="filter-value">"${displayValue}"</span>
                <span class="remove" onclick="removeAdvancedFilter(${index})">✕</span>
            `;
        }
        
        container.appendChild(chip);
    });
}

function getOperatorLabel(operatorValue) {
    for (const [type, operators] of Object.entries(operatorsByType)) {
        const found = operators.find(op => op.value === operatorValue);
        if (found) return found.label;
    }
    return operatorValue;
}

function applyAdvancedFilterToVendor(vendor, filter) {
    // Get the field value from vendor (supports nested properties like address.city)
    const fieldPath = filter.field.split('.');
    let value = vendor;
    
    for (const part of fieldPath) {
        if (value === null || value === undefined) {
            value = null;
            break;
        }
        value = value[part];
    }
    
    // Convert value to string for text operations
    const strValue = value !== null && value !== undefined ? String(value).toLowerCase() : '';
    const filterValue = filter.value ? String(filter.value).toLowerCase() : '';
    
    // Apply operator
    switch (filter.operator) {
        case 'contains':
            return strValue.includes(filterValue);
        case 'not_contains':
            return !strValue.includes(filterValue);
        case 'equals':
            return strValue === filterValue || value === filter.value;
        case 'not_equals':
            return strValue !== filterValue && value !== filter.value;
        case 'starts_with':
            return strValue.startsWith(filterValue);
        case 'ends_with':
            return strValue.endsWith(filterValue);
        case 'is_empty':
            return value === null || value === undefined || strValue === '';
        case 'is_not_empty':
            return value !== null && value !== undefined && strValue !== '';
        case 'greater_than':
            return parseFloat(value) > parseFloat(filter.value);
        case 'less_than':
            return parseFloat(value) < parseFloat(filter.value);
        case 'greater_or_equal':
            return parseFloat(value) >= parseFloat(filter.value);
        case 'less_or_equal':
            return parseFloat(value) <= parseFloat(filter.value);
        case 'is_true':
            return value === true;
        case 'is_false':
            return value === false || value === null || value === undefined;
        default:
            return true;
    }
}
