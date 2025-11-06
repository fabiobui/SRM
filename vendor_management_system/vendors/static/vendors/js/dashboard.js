// Global variables
let allVendors = [];
let filteredVendors = [];
let activeFilters = {
    regions: [],
    provinces: [],
    categories: [],
    qualification_statuses: [],
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
    
    console.log('Initializing dashboard...');
    console.log('Total vendors:', allVendors.length);
    console.log('Chart data:', chartDataJson);
    
    createCategoryChart(chartDataJson.by_category);
    createQualificationChart(chartDataJson.by_qualification);
    createRegionChart(chartDataJson.by_region);
    createProvinceChart(chartDataJson.by_province || []);
    createQualityChart(chartDataJson.by_quality);
    createFulfillmentChart(chartDataJson.by_fulfillment);
    createCompetenciesChart(chartDataJson.by_competencies || []);
    
    renderVendorsTable();
    
    document.getElementById('search-input').addEventListener('input', filterVendors);
}

// Create charts
function createCategoryChart(data) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    charts.category = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.category || 'Non Classificato'),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('categories', charts.category.data.labels[activeElements[0].index]);
                }
            },
            plugins: { legend: { position: 'bottom' } }
        }
    });
}

function createQualificationChart(data) {
    const ctx = document.getElementById('qualificationChart').getContext('2d');
    const statusMap = { 'APPROVED': 'Approvato', 'PENDING': 'In attesa', 'REJECTED': 'Respinto' };
    charts.qualification = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.map(item => statusMap[item.status] || item.status),
            datasets: [{ data: data.map(item => item.count), backgroundColor: ['#28a745', '#ffc107', '#dc3545'] }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    const reverseMap = { 'Approvato': 'APPROVED', 'In attesa': 'PENDING', 'Respinto': 'REJECTED' };
                    toggleFilter('qualification_statuses', reverseMap[charts.qualification.data.labels[activeElements[0].index]]);
                }
            },
            plugins: { legend: { position: 'bottom' } }
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
                    updateProvinceChart();
                }
            },
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            plugins: { legend: { display: false } }
        }
    });
}

function createProvinceChart(data) {
    const ctx = document.getElementById('provinceChart').getContext('2d');
    
    console.log('=== PROVINCE CHART DEBUG ===');
    console.log('Data received:', data);
    
    // Se non ci sono dati dal backend, calcoliamo manualmente
    if (!data || data.length === 0) {
        console.log('No province data from backend, calculating from vendors...');
        
        // Mostra i primi 10 address per capire la struttura
        console.log('=== Checking first 10 vendors addresses ===');
        allVendors.slice(0, 10).forEach((vendor, i) => {
            console.log(`Vendor ${i} (${vendor.vendor_code}):`, {
                has_address: !!vendor.address,
                address: vendor.address,
                state_province: vendor.address?.state_province,
                region: vendor.address?.region
            });
        });
        
        const provinceCount = {};
        let vendorsWithProvince = 0;
        let vendorsWithoutProvince = 0;
        
        allVendors.forEach((vendor, index) => {
            if (vendor.address) {
                const province = vendor.address.state_province;
                
                if (province && province.trim() !== '' && province !== 'Non Specificato') {
                    provinceCount[province.trim()] = (provinceCount[province.trim()] || 0) + 1;
                    vendorsWithProvince++;
                } else {
                    vendorsWithoutProvince++;
                    if (vendorsWithoutProvince <= 5) {
                        console.log(`Vendor ${index} has no province:`, vendor.address);
                    }
                }
            } else {
                vendorsWithoutProvince++;
            }
        });
        
        console.log(`Vendors WITH province: ${vendorsWithProvince}`);
        console.log(`Vendors WITHOUT province: ${vendorsWithoutProvince}`);
        console.log('Province counts:', provinceCount);
        console.log('Unique provinces found:', Object.keys(provinceCount).length);
        
        // Converti in array e ordina per count
        data = Object.entries(provinceCount)
            .map(([province, count]) => ({ province, count }))
            .sort((a, b) => b.count - a.count);
        
        console.log('Top 10 provinces:', data.slice(0, 10));
    }
    
    allProvinces = data;
    
    if (data.length === 0) {
        console.warn('⚠️ NO PROVINCE DATA - Creating empty chart');
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
    
    console.log(`✓ Creating chart with ${labels.length} provinces`);
    
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
                        }
                    }
                }
            }
        }
    });
    
    console.log('✓ Province chart created successfully');
}

function createQualityChart(data) {
    const ctx = document.getElementById('qualityChart').getContext('2d');
    charts.quality = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.range),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#6f42c1' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            plugins: { legend: { display: false } }
        }
    });
}

function createFulfillmentChart(data) {
    const ctx = document.getElementById('fulfillmentChart').getContext('2d');
    charts.fulfillment = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.range),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#fd7e14' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            plugins: { legend: { display: false } }
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
            plugins: { legend: { display: false } }
        }
    });
}

// Update Province Chart
function updateProvinceChart() {
    console.log('=== UPDATE PROVINCE CHART ===');
    console.log('Active region filters:', activeFilters.regions);
    
    if (activeFilters.regions.length === 0) {
        // Mostra TUTTE le province
        console.log('Showing all provinces');
        const labels = allProvinces.map(item => item.province || 'Non Specificato');
        const values = allProvinces.map(item => item.count);
        
        charts.province.data.labels = labels;
        charts.province.data.datasets[0].data = values;
        charts.province.data.datasets[0].backgroundColor = labels.map(label => 
            activeFilters.provinces.includes(label) ? '#28a745' : '#6f42c1'
        );
        document.getElementById('province-region-badge').style.display = 'none';
    } else {
        // Filtra province per le regioni selezionate
        console.log('Filtering provinces by selected regions');
        const filteredData = {};
        
        allVendors.forEach(v => {
            if (v.address && v.address.state_province && v.address.region) {
                // Verifica se la regione del vendor è tra quelle selezionate
                if (activeFilters.regions.includes(v.address.region)) {
                    const province = v.address.state_province;
                    filteredData[province] = (filteredData[province] || 0) + 1;
                }
            }
        });
        
        console.log('Filtered province data:', filteredData);
        
        const labels = Object.keys(filteredData).sort((a, b) => filteredData[b] - filteredData[a]);
        const values = labels.map(label => filteredData[label]);
        
        console.log('Filtered provinces:', labels.length);
        
        charts.province.data.labels = labels;
        charts.province.data.datasets[0].data = values;
        charts.province.data.datasets[0].backgroundColor = labels.map(label => 
            activeFilters.provinces.includes(label) ? '#28a745' : '#6f42c1'
        );
        
        const badge = document.getElementById('province-region-badge');
        badge.textContent = activeFilters.regions.join(', ');
        badge.style.display = 'inline-block';
    }
    
    charts.province.update();
    console.log('Province chart updated');
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
    
    if (dimension === 'regions' || dimension === 'provinces') updateProvinceChart();
    updateActiveFiltersDisplay();
    filterVendors();
}

function clearAllFilters() {
    activeFilters = { regions: [], provinces: [], categories: [], qualification_statuses: [], competencies: [] };
    document.getElementById('search-input').value = '';
    updateProvinceChart();
    updateActiveFiltersDisplay();
    filterVendors();
}

function removeFilter(dimension, value) {
    const index = activeFilters[dimension].indexOf(value);
    if (index > -1) activeFilters[dimension].splice(index, 1);
    
    if (dimension === 'regions') {
        const provincesToRemove = Object.keys(provinceRegionMap).filter(p => provinceRegionMap[p] === value);
        activeFilters.provinces = activeFilters.provinces.filter(p => !provincesToRemove.includes(p));
        updateProvinceChart();
    }
    
    if (dimension === 'provinces') updateProvinceChart();
    updateActiveFiltersDisplay();
    filterVendors();
}

function updateActiveFiltersDisplay() {
    const container = document.getElementById('active-filters-container');
    const row = document.getElementById('active-filters-row');
    const hasFilters = Object.values(activeFilters).some(arr => arr.length > 0);
    
    row.style.display = hasFilters ? 'block' : 'none';
    if (!hasFilters) return;
    
    container.innerHTML = '';
    const filterLabels = {
        'categories': 'Categoria', 'qualification_statuses': 'Qualifica',
        'regions': 'Regione', 'provinces': 'Provincia', 'competencies': 'Competenza'
    };
    
    Object.entries(activeFilters).forEach(([key, values]) => {
        values.forEach(value => {
            const chip = document.createElement('span');
            chip.className = 'filter-chip';
            chip.innerHTML = `${filterLabels[key]}: <strong>${value}</strong> <span class="remove" onclick="removeFilter('${key}', '${value.replace(/'/g, "\\'")}')">✕</span>`;
            container.appendChild(chip);
        });
    });
}

function filterVendors() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    filteredVendors = allVendors.filter(vendor => {
        if (activeFilters.categories.length > 0) {
            const vendorCategory = vendor.category ? (vendor.category.name || vendor.category) : 'Non Classificato';
            if (!activeFilters.categories.includes(vendorCategory)) return false;
        }
        
        if (activeFilters.qualification_statuses.length > 0 && !activeFilters.qualification_statuses.includes(vendor.qualification_status)) return false;
        
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
}

function renderVendorsTable() {
    const tbody = document.getElementById('vendors-table-body');
    document.getElementById('filtered-count').textContent = filteredVendors.length;
    document.getElementById('showing-count').textContent = filteredVendors.length;
    
    if (filteredVendors.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4"><div class="text-muted"><i class="fas fa-search fa-2x mb-2"></i><p>Nessun fornitore trovato</p></div></td></tr>';
        return;
    }
    
    tbody.innerHTML = filteredVendors.map(vendor => {
        const badges = {
            'APPROVED': 'status-approved">Approvato', 'PENDING': 'status-pending">In attesa',
            'REJECTED': 'status-rejected">Respinto', 'NOT_STARTED': 'status-pending">Non Iniziato',
            'IN_PROGRESS': 'status-pending">In Corso'
        };
        const badge = vendor.qualification_status ? `<span class="status-badge ${badges[vendor.qualification_status] || ''}"></span>` : '';
        const rating = vendor.quality_rating_avg || vendor.quality_rating || 0;
        const performance = rating > 0 ? `⭐ ${parseFloat(rating).toFixed(1)}/5` : '<span class="text-muted">N/A</span>';
        
        return `<tr>
            <td><code>${vendor.vendor_code}</code></td>
            <td><strong>${vendor.name || 'N/A'}</strong><br><small class="text-muted">${vendor.email || ''}</small></td>
            <td>${vendor.category?.name || vendor.category || '<span class="text-muted">Non Classificato</span>'}</td>
            <td>${vendor.address?.region || '<span class="text-muted">N/A</span>'}</td>
            <td>${badge}</td>
            <td>${vendor.service_type?.name || vendor.service_type || '<span class="text-muted">N/A</span>'}</td>
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
