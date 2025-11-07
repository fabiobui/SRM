// Global variables
let allVendors = [];
let filteredVendors = [];
let activeFilters = {
    regions: [],
    provinces: [],
    vendor_types: [],
    ico_consultant: null, // null, true, or false
    competencies: []
};
let charts = {};
let allProvinces = [];

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
    
    // Ordina per conteggio e prendi le top 10
    const sortedCompetencies = Object.entries(competencyCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
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
                    const isIco = index === 0; // 0 = Consulenti ICO, 1 = Altri Fornitori
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
    
    // Se non ci sono dati dal backend, calcoliamo manualmente
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
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('competencies', charts.competencies.data.labels[activeElements[0].index]);
                }
            },
            scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } },
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
    activeFilters = { regions: [], provinces: [], vendor_types: [], ico_consultant: null, competencies: [] };
    document.getElementById('search-input').value = '';
    
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
        'competencies': 'Competenza'
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
    
    renderVendorsTable();
    updateStatistics();
    
    // Aggiorna i grafici solo se c'è un termine di ricerca
    if (searchTerm) {
        updateAllCharts();
    }
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
        const badges = {
            'APPROVED': 'status-approved">Approvato', 'PENDING': 'status-pending">In attesa',
            'REJECTED': 'status-rejected">Respinto', 'NOT_STARTED': 'status-pending">Non Iniziato',
            'IN_PROGRESS': 'status-pending">In Corso'
        };
        const badge = vendor.qualification_status ? `<span class="status-badge ${badges[vendor.qualification_status] || ''}"></span>` : '';
        const rating = vendor.quality_rating_avg || vendor.quality_rating || 0;
        const performance = rating > 0 ? `⭐ ${parseFloat(rating).toFixed(1)}/5` : '<span class="text-muted">N/A</span>';
        const vendorTypeLabel = vendorTypeMap[vendor.vendor_type] || vendor.vendor_type || '<span class="text-muted">Non Specificato</span>';
        
        return `<tr>
            <td><code>${vendor.vendor_code}</code></td>
            <td><strong>${vendor.name || 'N/A'}</strong><br><small class="text-muted">${vendor.email || ''}</small></td>
            <td>${vendorTypeLabel}</td>
            <td>${vendor.service_type?.parent || '<span class="text-muted">N/A</span>'}</td>
            <td>${badge}</td>
            <td>${vendor.address?.region || '<span class="text-muted">N/A</span>'}</td>
            <td>${performance}</td>
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
