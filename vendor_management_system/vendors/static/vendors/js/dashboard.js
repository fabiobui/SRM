// Global variables
let allVendors = [];
let filteredVendors = [];
let activeFilters = {
    regions: [],
    provinces: [],
    vendor_types: [],
    ico_consultant: null, // null, true, or false
    competencies: [],
    certifications: [],
    qualifiche: [],
    competenze_req: [],
    service_categories: [],
    services: []
};
let charts = {};
let allProvinces = [];
let serviceCategoryMap = {}; // Maps service name to category name

// ---------------------------------------------------------------------------
// Copertura territoriale
//
// I grafici "Regioni" e "Province" contano le ZONE DI COMPETENZA del
// fornitore, non piu' la sede. Ogni fornitore porta in `vendor.competence`
// i codici delle aree coperte; la sentinella '*' significa "tutto il
// territorio" ed evita di serializzare 107 sigle per fornitore.
//
// Le mappe codice <-> nome si costruiscono dai dati dei grafici, che il
// server produce gia' ordinati: non serve piu' la tabella provincia ->
// regione hardcodata qui (che fra l'altro divergeva dal database sulla
// grafia di Friuli(-)Venezia Giulia).
// ---------------------------------------------------------------------------
const COMPETENCE_ALL = '*';
const UNSPECIFIED_LABEL = 'Non specificato';

let regionNameByCode = {};
let regionCodeByName = {};
let provinceNameByCode = {};
let provinceCodeByName = {};
let regionNameByProvinceName = {};
let allRegionCodes = [];
let allProvinceCodes = [];

function buildGeoMaps(chartDataJson) {
    regionNameByCode = {};
    regionCodeByName = {};
    provinceNameByCode = {};
    provinceCodeByName = {};
    regionNameByProvinceName = {};

    (chartDataJson.by_region || []).forEach(row => {
        if (!row.code) return;  // bucket "Non specificato"
        regionNameByCode[row.code] = row.region;
        regionCodeByName[row.region] = row.code;
    });
    (chartDataJson.by_province || []).forEach(row => {
        if (!row.code) return;
        provinceNameByCode[row.code] = row.province;
        provinceCodeByName[row.province] = row.code;
        if (row.region_name) {
            regionNameByProvinceName[row.province] = row.region_name;
        }
    });

    allRegionCodes = Object.keys(regionNameByCode);
    allProvinceCodes = Object.keys(provinceNameByCode);
}

// Un fornitore senza nessuna area dichiarata. Stessa definizione del
// bucket "Non specificato" calcolato lato server: se divergessero, il
// grafico iniziale e quello ricalcolato dopo un filtro mostrerebbero
// numeri diversi.
function hasNoCompetence(vendor) {
    const c = vendor.competence;
    if (!c) return true;
    return (c.regions || []).length === 0 && (c.countries || []).length === 0;
}

function competenceRegionCodes(vendor) {
    const codes = (vendor.competence && vendor.competence.regions) || [];
    return codes.indexOf(COMPETENCE_ALL) !== -1 ? allRegionCodes : codes;
}

function competenceProvinceCodes(vendor) {
    const codes = (vendor.competence && vendor.competence.provinces) || [];
    return codes.indexOf(COMPETENCE_ALL) !== -1 ? allProvinceCodes : codes;
}

// Predicato unico dei filtri geografici, al posto delle dieci copie che
// erano sparse in ogni updateXChart(). `opts.skipRegions` /
// `opts.skipProvinces` servono al grafico che sta ricalcolando la propria
// stessa dimensione.
function matchesCompetenceFilters(vendor, opts) {
    opts = opts || {};

    if (!opts.skipRegions && activeFilters.regions.length > 0) {
        const codes = competenceRegionCodes(vendor);
        const ok = activeFilters.regions.some(name =>
            name === UNSPECIFIED_LABEL
                ? hasNoCompetence(vendor)
                : codes.indexOf(regionCodeByName[name]) !== -1
        );
        if (!ok) return false;
    }

    if (!opts.skipProvinces && activeFilters.provinces.length > 0) {
        const codes = competenceProvinceCodes(vendor);
        const ok = activeFilters.provinces.some(name =>
            codes.indexOf(provinceCodeByName[name]) !== -1
        );
        if (!ok) return false;
    }

    return true;
}

// Initialize dashboard
function initDashboard(chartDataJson, vendorsDataJson) {
    allVendors = vendorsDataJson;
    filteredVendors = [...allVendors];

    // Salva i dati originali per ricalcolare i grafici
    window.originalChartData = chartDataJson;

    // Mappe codice <-> nome delle aree di competenza: vanno costruite
    // prima di qualunque createXChart.
    buildGeoMaps(chartDataJson);

    // Costruisci la mappa servizio→categoria
    if (chartDataJson.by_services) {
        chartDataJson.by_services.forEach(item => {
            if (item.service && item.category) {
                serviceCategoryMap[item.service] = item.category;
            }
        });
    }

    createVendorTypeChart(chartDataJson.by_vendor_type);
    createIcoConsultantChart(chartDataJson.by_ico_consultant);
    createRegionChart(chartDataJson.by_region);
    createProvinceChart(chartDataJson.by_province || []);
    createQualificheChart(chartDataJson.by_qualifiche || []);
    createCompetenzeChart(chartDataJson.by_competenze || []);
    createCertificationsChart(chartDataJson.by_certifications || []);
    createServiceCategoriesChart(chartDataJson.by_service_categories || []);
    createServicesChart(chartDataJson.by_services || []);

    renderVendorsTable();
    updateStatistics();

    buildDropdownFilters(chartDataJson);
    document.getElementById('search-input').addEventListener('input', filterVendors);
}

// Funzione per aggiornare tutti i grafici in base ai filtri attivi
function updateAllCharts() {
    // Calcola i nuovi dati per ogni grafico in base ai vendor filtrati
    updateVendorTypeChart();
    updateIcoConsultantChart();
    updateRegionChart();
    updateProvinceChart();
    updateQualificheChart();
    updateCompetenzeChart();
    updateCertificationsChart();
    updateServiceCategoriesChart();
    updateServicesChart();
}

// Funzione per aggiornare le statistiche in alto
function updateStatistics() {
    const totalVendors = allVendors.length;
    const activeVendors = allVendors.filter(v => v.is_active === true).length;
    const selectedVendors = filteredVendors.length;

    // Filtra i fornitori positivi TRA QUELLI SELEZIONATI
    const positiveVendors = filteredVendors.filter(v => {
        return v.vendor_final_evaluation === 'POSITIVO';
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

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutTypeFilter.forEach(v => {
        const type = v.vendor_type || UNSPECIFIED_LABEL;
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

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

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
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        // Il filtro province SI applica (skipRegions: true): cliccare una
        // provincia deve restringere il grafico Regioni alla sola regione
        // di quella provincia. Il filtro regioni resta escluso, altrimenti
        // deselezionare una regione dal proprio stesso grafico sarebbe
        // impossibile.
        if (!matchesCompetenceFilters(vendor, { skipRegions: true })) return false;

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutRegionFilter.forEach(v => {
        if (hasNoCompetence(v)) {
            regionCounts[UNSPECIFIED_LABEL] =
                (regionCounts[UNSPECIFIED_LABEL] || 0) + 1;
            return;
        }

        if (activeFilters.provinces.length > 0) {
            // Con un filtro provincia attivo il grafico si restringe alla
            // sola regione di quella provincia, non a tutte le regioni
            // coperte dal fornitore: altrimenti filtrando "Ravenna" si
            // vedrebbe comparire anche la Lombardia se il fornitore la
            // copre pure lui.
            const coperte = new Set(competenceProvinceCodes(v));
            const regioniDelFiltro = new Set();
            activeFilters.provinces.forEach(nomeProvincia => {
                const codice = provinceCodeByName[nomeProvincia];
                if (codice && coperte.has(codice)) {
                    const nomeRegione = regionNameByProvinceName[nomeProvincia];
                    if (nomeRegione) regioniDelFiltro.add(nomeRegione);
                }
            });
            regioniDelFiltro.forEach(name => {
                regionCounts[name] = (regionCounts[name] || 0) + 1;
            });
            return;
        }

        competenceRegionCodes(v).forEach(code => {
            const name = regionNameByCode[code];
            if (name) regionCounts[name] = (regionCounts[name] || 0) + 1;
        });
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

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutCompetencyFilter.filter(v => matchesOwnSelection(v, 'competencies')).forEach(v => {
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

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            if (!vendor.competences || !Array.isArray(vendor.competences)) return false;
            const hasMatchingCompetency = vendor.competences.some(comp =>
                activeFilters.competencies.includes(comp)
            );
            if (!hasMatchingCompetency) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutCertificationFilter.filter(v => matchesOwnSelection(v, 'certifications')).forEach(v => {
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

// Funzione per ricalcolare i dati del grafico Qualifiche
function updateQualificheChart() {
    const qualificheCounts = {};

    // Filtra i vendor escludendo il filtro qualifiche per calcolare il grafico
    const vendorsWithoutQualificheFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO qualifiche
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }

        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.competenze_req.length > 0) {
            const hasCompetenza = activeFilters.competenze_req.every(comp => vendor.competenze_req?.includes(comp));
            if (!hasCompetenza) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (activeFilters.service_categories.length > 0) {
            const hasCategory = activeFilters.service_categories.every(cat => vendor.service_categories?.includes(cat));
            if (!hasCategory) return false;
        }

        if (activeFilters.services.length > 0) {
            const hasService = activeFilters.services.every(serv => vendor.services?.some(s => s.name === serv));
            if (!hasService) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutQualificheFilter.filter(v => matchesOwnSelection(v, 'qualifiche')).forEach(v => {
        if (v.qualifiche && Array.isArray(v.qualifiche)) {
            v.qualifiche.forEach(qual => {
                qualificheCounts[qual] = (qualificheCounts[qual] || 0) + 1;
            });
        }
    });

    // Ordina per conteggio
    const sortedQualifiche = Object.entries(qualificheCounts)
        .sort((a, b) => b[1] - a[1]);

    const labels = sortedQualifiche.map(([qual]) => qual);
    const data = sortedQualifiche.map(([, count]) => count);

    // Evidenzia le selezioni attive
    const backgroundColors = labels.map(label =>
        activeFilters.qualifiche.includes(label) ? '#20c997' : '#17a2b8'
    );

    charts.qualifiche.data.labels = labels;
    charts.qualifiche.data.datasets[0].data = data;
    charts.qualifiche.data.datasets[0].backgroundColor = backgroundColors;
    charts.qualifiche.update();
}

// Funzione per ricalcolare i dati del grafico Competenze
function updateCompetenzeChart() {
    const competenzeCounts = {};

    // Filtra i vendor escludendo il filtro competenze per calcolare il grafico
    const vendorsWithoutCompetenzeFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO competenze_req
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }

        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.qualifiche.length > 0) {
            const hasQualifica = activeFilters.qualifiche.every(qual => vendor.qualifiche?.includes(qual));
            if (!hasQualifica) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (activeFilters.service_categories.length > 0) {
            const hasCategory = activeFilters.service_categories.every(cat => vendor.service_categories?.includes(cat));
            if (!hasCategory) return false;
        }

        if (activeFilters.services.length > 0) {
            const hasService = activeFilters.services.every(serv => vendor.services?.some(s => s.name === serv));
            if (!hasService) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutCompetenzeFilter.filter(v => matchesOwnSelection(v, 'competenze_req')).forEach(v => {
        if (v.competenze_req && Array.isArray(v.competenze_req)) {
            v.competenze_req.forEach(comp => {
                competenzeCounts[comp] = (competenzeCounts[comp] || 0) + 1;
            });
        }
    });

    // Ordina per conteggio
    const sortedCompetenze = Object.entries(competenzeCounts)
        .sort((a, b) => b[1] - a[1]);

    const labels = sortedCompetenze.map(([comp]) => comp);
    const data = sortedCompetenze.map(([, count]) => count);

    // Evidenzia le selezioni attive
    const backgroundColors = labels.map(label =>
        activeFilters.competenze_req.includes(label) ? '#20c997' : '#6610f2'
    );

    charts.competenze_req.data.labels = labels;
    charts.competenze_req.data.datasets[0].data = data;
    charts.competenze_req.data.datasets[0].backgroundColor = backgroundColors;
    charts.competenze_req.update();
}

// Funzione per ricalcolare i dati del grafico Categorie Servizi
function updateServiceCategoriesChart() {
    const categoryCounts = {};

    // Filtra i vendor escludendo il filtro service_categories per calcolare il grafico
    const vendorsWithoutCategoryFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO service_categories
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }

        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.qualifiche.length > 0) {
            const hasQualifica = activeFilters.qualifiche.every(qual => vendor.qualifiche?.includes(qual));
            if (!hasQualifica) return false;
        }

        if (activeFilters.competenze_req.length > 0) {
            const hasCompetenza = activeFilters.competenze_req.every(comp => vendor.competenze_req?.includes(comp));
            if (!hasCompetenza) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (activeFilters.services.length > 0) {
            const hasService = activeFilters.services.every(serv => vendor.services?.some(s => s.name === serv));
            if (!hasService) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutCategoryFilter.filter(v => matchesOwnSelection(v, 'service_categories')).forEach(v => {
        if (v.service_categories && Array.isArray(v.service_categories)) {
            v.service_categories.forEach(cat => {
                categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
            });
        }
    });

    // Ordina per conteggio
    const sortedCategories = Object.entries(categoryCounts)
        .sort((a, b) => b[1] - a[1]);

    const labels = sortedCategories.map(([cat]) => cat);
    const data = sortedCategories.map(([, count]) => count);

    // Evidenzia le selezioni attive
    const backgroundColors = labels.map(label =>
        activeFilters.service_categories.includes(label) ? '#20c997' : '#fd7e14'
    );

    charts.service_categories.data.labels = labels;
    charts.service_categories.data.datasets[0].data = data;
    charts.service_categories.data.datasets[0].backgroundColor = backgroundColors;
    charts.service_categories.update();
}

// Funzione per ricalcolare i dati del grafico Servizi Specifici
function updateServicesChart() {
    const serviceCounts = {};

    // Filtra i vendor escludendo il filtro services per calcolare il grafico
    const vendorsWithoutServicesFilter = allVendors.filter(vendor => {
        // Applica tutti i filtri ECCETTO services
        if (activeFilters.vendor_types.length > 0) {
            if (!activeFilters.vendor_types.includes(vendor.vendor_type)) return false;
        }

        if (activeFilters.ico_consultant !== null) {
            if (vendor.is_ico_consultant !== activeFilters.ico_consultant) return false;
        }

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.qualifiche.length > 0) {
            const hasQualifica = activeFilters.qualifiche.every(qual => vendor.qualifiche?.includes(qual));
            if (!hasQualifica) return false;
        }

        if (activeFilters.competenze_req.length > 0) {
            const hasCompetenza = activeFilters.competenze_req.every(comp => vendor.competenze_req?.includes(comp));
            if (!hasCompetenza) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (activeFilters.service_categories.length > 0) {
            const hasCategory = activeFilters.service_categories.every(cat => vendor.service_categories?.includes(cat));
            if (!hasCategory) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    vendorsWithoutServicesFilter.filter(v => matchesOwnSelection(v, 'services')).forEach(v => {
        if (v.services && Array.isArray(v.services)) {
            v.services.forEach(serv => {
                serviceCounts[serv.name] = (serviceCounts[serv.name] || 0) + 1;
            });
        }
    });

    // Filtra per categoria selezionata se presente
    if (activeFilters.service_categories.length > 0) {
        // Dobbiamo costruire una mappa servizio->categoria dai dati originali del backend
        const serviceToCategory = {};
        if (window.originalChartData && window.originalChartData.by_services) {
            window.originalChartData.by_services.forEach(item => {
                if (item.service && item.category) {
                    serviceToCategory[item.service] = item.category;
                }
            });
        }

        // Filtra i servizi che appartengono alle categorie selezionate
        Object.keys(serviceCounts).forEach(service => {
            const category = serviceToCategory[service];
            if (!category || !activeFilters.service_categories.includes(category)) {
                delete serviceCounts[service];
            }
        });
    }

    // Ordina per conteggio
    const sortedServices = Object.entries(serviceCounts)
        .sort((a, b) => b[1] - a[1]);

    const labels = sortedServices.map(([serv]) => serv);
    const data = sortedServices.map(([, count]) => count);

    // Evidenzia le selezioni attive
    const backgroundColors = labels.map(label =>
        activeFilters.services.includes(label) ? '#20c997' : '#e83e8c'
    );

    charts.services.data.labels = labels;
    charts.services.data.datasets[0].data = data;
    charts.services.data.datasets[0].backgroundColor = backgroundColors;

    // Mostra badge se ci sono categorie selezionate
    const badge = document.getElementById('service-category-badge');
    if (activeFilters.service_categories.length > 0) {
        badge.textContent = activeFilters.service_categories.join(', ');
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }

    charts.services.update();
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
            labels: data.map(item => vendorTypeMap[item.type] || item.type || UNSPECIFIED_LABEL),
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
            labels: data.map(item => item.region || UNSPECIFIED_LABEL),
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

    // `by_province` e' calcolato lato server: non serve piu'
    // il fallback che ricalcolava i conteggi nel browser.
    data = data || [];
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

function createQualificheChart(data) {
    const ctx = document.getElementById('qualificheChart').getContext('2d');
    charts.qualifiche = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.qualifica || 'N/A'),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#17a2b8' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('qualifiche', charts.qualifiche.data.labels[activeElements[0].index]);
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

function createCompetenzeChart(data) {
    const ctx = document.getElementById('competenzeChart').getContext('2d');
    charts.competenze_req = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.competenza || 'N/A'),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#6610f2' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('competenze_req', charts.competenze_req.data.labels[activeElements[0].index]);
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

function createServiceCategoriesChart(data) {
    const ctx = document.getElementById('serviceCategoriesChart').getContext('2d');
    charts.service_categories = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.category || 'N/A'),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#fd7e14' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('service_categories', charts.service_categories.data.labels[activeElements[0].index]);
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

function createServicesChart(data) {
    const ctx = document.getElementById('servicesChart').getContext('2d');
    charts.services = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(item => item.service || 'N/A'),
            datasets: [{ label: 'Numero Fornitori', data: data.map(item => item.count), backgroundColor: '#e83e8c' }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: (e, activeElements) => {
                if (activeElements.length > 0) {
                    toggleFilter('services', charts.services.data.labels[activeElements[0].index]);
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

        if (!matchesCompetenceFilters(vendor, { skipProvinces: true })) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

        return true;
    });

    const provinceCount = {};

    vendorsWithoutProvinceFilter.forEach((vendor) => {
        competenceProvinceCodes(vendor).forEach(code => {
            const name = provinceNameByCode[code];
            if (name) provinceCount[name] = (provinceCount[name] || 0) + 1;
        });
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
            activeFilters.provinces = activeFilters.provinces.filter(
                p => regionNameByProvinceName[p] !== value
            );
        }
        if (dimension === 'service_categories') {
            const servicesToRemove = Object.keys(serviceCategoryMap).filter(s => serviceCategoryMap[s] === value);
            activeFilters.services = activeFilters.services.filter(s => !servicesToRemove.includes(s));
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
    activeFilters = {
        regions: [],
        provinces: [],
        vendor_types: [],
        ico_consultant: null,
        competencies: [],
        certifications: [],
        qualifiche: [],
        competenze_req: [],
        service_categories: [],
        services: []
    };
    resetDropdownSelection();
    document.querySelectorAll('.dd-filter input[type="checkbox"]').forEach(box => { box.checked = false; });
    DROPDOWN_FILTERS.forEach(f => refreshDropdownCount(f.key));
    document.getElementById('search-input').value = '';
    updateAppliedFiltersBadge();

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
            activeFilters.provinces = activeFilters.provinces.filter(
                p => regionNameByProvinceName[p] !== value
            );
        }

        if (dimension === 'service_categories') {
            const servicesToRemove = Object.keys(serviceCategoryMap).filter(s => serviceCategoryMap[s] === value);
            activeFilters.services = activeFilters.services.filter(s => !servicesToRemove.includes(s));
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
        'certifications': 'Certificazione',
        'qualifiche': 'Qualifica',
        'competenze_req': 'Competenza Richiesta',
        'service_categories': 'Categoria Servizio',
        'services': 'Servizio'
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

// Con la logica AND, il grafico di una dimensione conta i fornitori che hanno
// TUTTI i valori già scelti, compresi quelli della propria dimensione: così
// mostra solo i valori che compaiono insieme a quelli selezionati.
const VENDOR_FIELD_BY_FILTER = {
    competencies: 'competences',
    certifications: 'certifications',
    qualifiche: 'qualifiche',
    competenze_req: 'competenze_req',
    service_categories: 'service_categories'
};

function matchesOwnSelection(vendor, key) {
    const selected = activeFilters[key];
    if (!selected || selected.length === 0) return true;
    if (key === 'services') {
        return selected.every(name => vendor.services?.some(s => s.name === name));
    }
    return selected.every(value => vendor[VENDOR_FIELD_BY_FILTER[key]]?.includes(value));
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

        if (!matchesCompetenceFilters(vendor)) return false;

        if (activeFilters.competencies.length > 0) {
            const hasCompetency = activeFilters.competencies.every(comp => vendor.competences?.includes(comp));
            if (!hasCompetency) return false;
        }

        if (activeFilters.qualifiche.length > 0) {
            const hasQualifica = activeFilters.qualifiche.every(qual => vendor.qualifiche?.includes(qual));
            if (!hasQualifica) return false;
        }

        if (activeFilters.competenze_req.length > 0) {
            const hasCompetenza = activeFilters.competenze_req.every(comp => vendor.competenze_req?.includes(comp));
            if (!hasCompetenza) return false;
        }

        if (activeFilters.certifications.length > 0) {
            const hasCertification = activeFilters.certifications.every(cert => vendor.certifications?.includes(cert));
            if (!hasCertification) return false;
        }

        if (activeFilters.service_categories.length > 0) {
            const hasCategory = activeFilters.service_categories.every(cat => vendor.service_categories?.includes(cat));
            if (!hasCategory) return false;
        }

        if (activeFilters.services.length > 0) {
            const hasService = activeFilters.services.every(serv => vendor.services?.some(s => s.name === serv));
            if (!hasService) return false;
        }

        if (!matchesDropdownFilters(vendor)) return false;

        if (!matchesSearch(vendor)) return false;

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

const FINAL_EVALUATION_BADGES = {
    'POSITIVO': { css: 'bg-success', label: 'Positivo' },
    'NEGATIVO': { css: 'bg-danger', label: 'Negativo' },
    'DA VALUTARE': { css: 'bg-secondary', label: 'Da Valutare' }
};

// Indirizzo dell'anagrafica (sede). Regione/provincia non si mostrano qui:
// i filtri dei grafici lavorano sulle zone di competenza, non sulla sede.
function formatVendorAddress(address) {
    if (!address) return '<span class="text-muted">N/A</span>';
    const localita = [address.postal_code, address.city].filter(Boolean).join(' ');
    const provincia = address.state_province ? `(${address.state_province})` : '';
    const riga = [address.street_address, [localita, provincia].filter(Boolean).join(' ')]
        .filter(Boolean).join(', ');
    if (!riga) return '<span class="text-muted">N/A</span>';
    const div = document.createElement('div');
    div.textContent = riga;
    return div.innerHTML;
}

// Note operative: testo completo, a capo
function formatOperationalNotes(notes) {
    if (!notes) return '<span class="text-muted">—</span>';
    const div = document.createElement('div');
    div.textContent = notes;
    return `<small class="operational-notes">${div.innerHTML}</small>`;
}

function escapeAttr(value) {
    return String(value ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;')
        .replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
        const address = formatVendorAddress(vendor.address);
        const phone = vendor.phone || '<span class="text-muted">N/A</span>';
        const evaluation = FINAL_EVALUATION_BADGES[vendor.vendor_final_evaluation] || FINAL_EVALUATION_BADGES['DA VALUTARE'];

        const vendorTypeLabel = vendor.vendor_type || '<span class="text-muted">N/A</span>';

        return `<tr>
            <td><strong>${vendor.name || 'N/A'}</strong></td>
            <td>${vendorTypeLabel}</td>
            <td><small>${vendor.email || '<span class="text-muted">N/A</span>'}</small></td>
            <td>${phone}</td>
            <td><small>${address}</small></td>
            <td>${formatOperationalNotes(vendor.operational_notes)}</td>
            <td><span class="badge ${evaluation.css}"><i class="fas fa-circle me-1"></i>${evaluation.label}</span></td>
            <td><button type="button" class="btn btn-sm btn-outline-primary btn-vendor-detail" data-vendor-code="${escapeAttr(vendor.vendor_code)}" data-vendor-name="${escapeAttr(vendor.name)}" title="Scheda fornitore"><i class="fas fa-eye"></i></button></td>
        </tr>`;
    }).join('');
}

function exportToExcel() {
    const params = new URLSearchParams();
    Object.entries(activeFilters).forEach(([key, values]) => {
        if (values === null || values === undefined) return;
        // Le zone di competenza viaggiano per CODICE e sotto un nome di
        // parametro diverso da quello del filtro client, che lavora sui
        // nomi. I vecchi `regions`/`provinces` filtravano per
        // nome sulla sede e non esistono più lato server.
        if (key === 'regions' || key === 'provinces') {
            if (!values.length) return;
            const mappa =
                key === 'regions' ? regionCodeByName : provinceCodeByName;
            const codici = values.map(n => mappa[n]).filter(Boolean);
            if (codici.length) {
                params.append('comp_' + key, codici.join(','));
            }
            return;
        }
        if (Array.isArray(values)) {
            if (values.length > 0) params.append(key, values.join(','));
        } else {
            params.append(key, values);
        }
    });
    dropdownExportParams(params);
    const searchTerm = document.getElementById('search-input').value.trim();
    if (searchTerm) params.append('search', searchTerm);

    const prefix = typeof SCRIPT_PREFIX !== 'undefined' ? SCRIPT_PREFIX : '';
    window.location.href = `${prefix}/vendors/export-excel/${params.toString() ? '?' + params.toString() : ''}`;
}

// ===== FILTRI AVANZATI: MENU' A TENDINA =====
//
// Un menu' per campo, sempre visibile. Dentro lo stesso campo i valori
// scelti sono in OR (basta averne uno); tra campi diversi vale l'AND. Il
// server applica le stesse regole all'export (vendors/dashboard_filters.py).

const FINAL_EVALUATION_LABELS = {
    'DA VALUTARE': 'Da Valutare',
    'NEGATIVO': 'Negativo',
    'POSITIVO': 'Positivo'
};

// `values(vendor)` restituisce i valori del fornitore su quel campo; i
// campi geografici (`geo`) confrontano invece i codici di competenza.
const DROPDOWN_FILTERS = [
    { key: 'classifications', param: 'dd_classifications', label: 'Classificazione',
      values: v => v.classifications || [] },
    { key: 'vendor_types', param: 'dd_vendor_types', label: 'Tipo Fornitore',
      values: v => (v.vendor_type ? [v.vendor_type] : []) },
    { key: 'final_evaluations', param: 'dd_final_evaluations', label: 'Valutazione Finale',
      values: v => [v.vendor_final_evaluation || 'DA VALUTARE'],
      display: value => FINAL_EVALUATION_LABELS[value] || value },
    { key: 'services', param: 'dd_services', label: 'Servizi erogati',
      values: v => (v.services || []).map(s => s.name) },
    { key: 'competenze', param: 'dd_competenze', label: 'Competenze',
      values: v => v.competenze_req || [] },
    { key: 'qualifiche', param: 'dd_qualifiche', label: 'Qualifiche professionali',
      values: v => v.qualifiche || [] },
    { key: 'certifications', param: 'dd_certifications', label: 'Certificazioni',
      values: v => v.certifications || [] },
    { key: 'countries', param: 'dd_countries', label: 'Paese', geo: true },
    { key: 'regions', param: 'dd_regions', label: 'Regione', geo: true },
    { key: 'provinces', param: 'dd_provinces', label: 'Provincia', geo: true }
];

let dropdownSelection = {};   // key -> Set di valori scelti
let homeCountryCodes = [];    // nazioni con regioni a catalogo (Italia)

function resetDropdownSelection() {
    dropdownSelection = {};
    DROPDOWN_FILTERS.forEach(f => { dropdownSelection[f.key] = new Set(); });
}
resetDropdownSelection();

// Opzioni {value, label} di ogni menu', ricavate dai dati censiti.
function dropdownOptions(filter, chartDataJson) {
    const byLabel = (a, b) => a.label.localeCompare(b.label, 'it');
    if (filter.key === 'countries') {
        return (chartDataJson.competence_countries || [])
            .map(c => ({ value: c.code, label: c.name })).sort(byLabel);
    }
    if (filter.key === 'regions') {
        return (chartDataJson.by_region || []).filter(r => r.code)
            .map(r => ({ value: r.code, label: r.region })).sort(byLabel);
    }
    if (filter.key === 'provinces') {
        return (chartDataJson.by_province || []).filter(p => p.code)
            .map(p => ({ value: p.code, label: p.province })).sort(byLabel);
    }
    const seen = new Set();
    allVendors.forEach(v => filter.values(v).forEach(value => {
        if (value) seen.add(value);
    }));
    const display = filter.display || (value => value);
    return [...seen].map(value => ({ value, label: display(value) })).sort(byLabel);
}

function vendorCoversCountry(vendor, code) {
    if (((vendor.competence && vendor.competence.countries) || []).includes(code)) return true;
    return homeCountryCodes.includes(code) && competenceProvinceCodes(vendor).length > 0;
}

function matchesDropdownFilter(vendor, filter) {
    const selected = dropdownSelection[filter.key];
    if (!selected || selected.size === 0) return true;
    if (filter.key === 'countries') {
        return [...selected].some(code => vendorCoversCountry(vendor, code));
    }
    if (filter.key === 'regions') {
        return competenceRegionCodes(vendor).some(code => selected.has(code));
    }
    if (filter.key === 'provinces') {
        return competenceProvinceCodes(vendor).some(code => selected.has(code));
    }
    return filter.values(vendor).some(value => selected.has(value));
}

function matchesDropdownFilters(vendor) {
    return DROPDOWN_FILTERS.every(filter => matchesDropdownFilter(vendor, filter));
}

// Ricerca testuale su codice Embyon, codice interno, ragione sociale,
// P.IVA e codice fiscale.
function matchesSearch(vendor) {
    const term = document.getElementById('search-input').value.trim().toLowerCase();
    if (!term) return true;
    return [vendor.old_code, vendor.vendor_code, vendor.name, vendor.vat_number, vendor.fiscal_code]
        .some(value => value && String(value).toLowerCase().includes(term));
}

function buildDropdownFilters(chartDataJson) {
    homeCountryCodes = chartDataJson.home_country_codes || [];
    const container = document.getElementById('dropdown-filters-container');
    container.innerHTML = '';

    DROPDOWN_FILTERS.forEach(filter => {
        const options = dropdownOptions(filter, chartDataJson);
        const col = document.createElement('div');
        col.className = 'col-xl-3 col-lg-4 col-md-6';

        const wrapper = document.createElement('div');
        wrapper.className = 'dropdown dd-filter';
        wrapper.dataset.key = filter.key;

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-sm btn-outline-secondary w-100 text-start dd-toggle';
        button.dataset.bsToggle = 'dropdown';
        button.dataset.bsAutoClose = 'outside';
        button.setAttribute('aria-expanded', 'false');
        const title = document.createElement('span');
        title.className = 'dd-title';
        title.textContent = filter.label;
        const count = document.createElement('span');
        count.className = 'badge bg-primary ms-2 dd-count';
        count.style.display = 'none';
        button.append(title, count);

        const menu = document.createElement('div');
        menu.className = 'dropdown-menu p-2 dd-menu';
        const search = document.createElement('input');
        search.type = 'search';
        search.className = 'form-control form-control-sm mb-2';
        search.placeholder = 'Cerca ' + filter.label.toLowerCase() + '...';
        const list = document.createElement('div');
        list.className = 'dd-options';

        options.forEach(option => {
            const label = document.createElement('label');
            label.className = 'dropdown-item dd-option';
            const box = document.createElement('input');
            box.type = 'checkbox';
            box.className = 'form-check-input me-2';
            box.value = option.value;
            box.addEventListener('change', () => {
                const selected = dropdownSelection[filter.key];
                if (box.checked) selected.add(option.value); else selected.delete(option.value);
                refreshDropdownCount(filter.key);
                applyDropdownFilters();
            });
            const text = document.createElement('span');
            text.textContent = option.label;
            label.append(box, text);
            list.appendChild(label);
        });
        if (options.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'text-muted small px-2';
            empty.textContent = 'Nessun valore censito';
            list.appendChild(empty);
        }

        search.addEventListener('input', () => {
            const term = search.value.trim().toLowerCase();
            list.querySelectorAll('.dd-option').forEach(item => {
                item.style.display = item.textContent.toLowerCase().includes(term) ? '' : 'none';
            });
        });

        menu.append(search, list);
        wrapper.append(button, menu);
        col.appendChild(wrapper);
        container.appendChild(col);
    });
}

function refreshDropdownCount(key) {
    const wrapper = document.querySelector(`.dd-filter[data-key="${key}"]`);
    if (!wrapper) return;
    const size = dropdownSelection[key].size;
    const badge = wrapper.querySelector('.dd-count');
    badge.textContent = size;
    badge.style.display = size > 0 ? 'inline-block' : 'none';
    wrapper.querySelector('.dd-toggle').classList.toggle('active', size > 0);
}

function updateAppliedFiltersBadge() {
    const total = DROPDOWN_FILTERS.reduce((sum, f) => sum + dropdownSelection[f.key].size, 0);
    const badge = document.getElementById('applied-filters-count');
    badge.textContent = total;
    badge.style.display = total > 0 ? 'inline-block' : 'none';
}

function applyDropdownFilters() {
    updateAppliedFiltersBadge();
    filterVendors();
    updateAllCharts();
}

// Azzera menu' e ricerca (senza toccare i filtri dei grafici).
function clearDropdownFilters() {
    resetDropdownSelection();
    document.querySelectorAll('.dd-filter input[type="checkbox"]').forEach(box => { box.checked = false; });
    DROPDOWN_FILTERS.forEach(f => refreshDropdownCount(f.key));
    document.getElementById('search-input').value = '';
    applyDropdownFilters();
}

function updateAdvancedFiltersDisplay() {
    updateActiveFiltersDisplay();
}

// Parametri dei menu' per l'export: stessi nomi letti dal server.
function dropdownExportParams(params) {
    DROPDOWN_FILTERS.forEach(f => {
        const selected = [...dropdownSelection[f.key]];
        if (selected.length) params.append(f.param, selected.join(','));
    });
}

// ===== SCHEDA FORNITORE (SOLA LETTURA) =====

function scriptPrefix() {
    return typeof SCRIPT_PREFIX !== 'undefined' ? SCRIPT_PREFIX : '';
}

async function openVendorDetail(vendorCode, vendorName) {
    const modalEl = document.getElementById('vendor-detail-modal');
    const body = document.getElementById('vendor-detail-body');
    document.getElementById('vendor-detail-title').textContent = vendorName || vendorCode;
    body.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>';
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
    try {
        const response = await fetch(`${scriptPrefix()}/vendors/dashboard/vendor/${encodeURIComponent(vendorCode)}/`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin'
        });
        if (!response.ok) throw new Error(response.status);
        // Frammento prodotto dal server con auto-escape: sola lettura.
        body.innerHTML = await response.text();
    } catch (error) {
        body.innerHTML = '<div class="alert alert-danger mb-0">Impossibile caricare la scheda del fornitore.</div>';
    }
}

// ===== AGGIUNGI FORNITORE PROSPETTO =====

const PROSPECT_FIELDS = ['name', 'vat_number', 'fiscal_code', 'email'];

function resetProspectForm() {
    const form = document.getElementById('prospect-form');
    form.reset();
    form.classList.remove('d-none');
    document.getElementById('prospect-result').classList.add('d-none');
    document.getElementById('prospect-submit').classList.remove('d-none');
    document.getElementById('prospect-non-field-error').classList.add('d-none');
    PROSPECT_FIELDS.forEach(name => {
        form.elements[name].classList.remove('is-invalid');
        document.getElementById(`prospect-error-${name}`).textContent = '';
    });
}

function showProspectErrors(errors) {
    PROSPECT_FIELDS.forEach(name => {
        const messages = errors[name] || [];
        document.getElementById('prospect-form').elements[name].classList.toggle('is-invalid', messages.length > 0);
        document.getElementById(`prospect-error-${name}`).textContent = messages.join(' ');
    });
    const general = errors.__all__ || [];
    const box = document.getElementById('prospect-non-field-error');
    box.textContent = general.join(' ');
    box.classList.toggle('d-none', general.length === 0);
}

async function submitProspect() {
    const form = document.getElementById('prospect-form');
    const submit = document.getElementById('prospect-submit');
    showProspectErrors({});
    submit.disabled = true;
    try {
        const response = await fetch(`${scriptPrefix()}/vendors/dashboard/prospect/`, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin'
        });
        const data = await response.json();
        if (response.status === 400) {
            showProspectErrors(data.errors || {});
            return;
        }
        if (!response.ok) throw new Error(response.status);

        const result = document.getElementById('prospect-result');
        const sentTo = (data.invite_sent_to || []).join(', ');
        result.innerHTML = '';
        const ok = document.createElement('div');
        ok.className = 'alert alert-success';
        ok.textContent = `Fornitore "${data.name}" creato (codice ${data.vendor_code}).` +
            (sentTo ? ` Invito al portale inviato a ${sentTo}.` : '');
        result.appendChild(ok);
        (data.warnings || []).forEach(text => {
            const warning = document.createElement('div');
            warning.className = 'alert alert-warning';
            warning.textContent = text;
            result.appendChild(warning);
        });
        result.classList.remove('d-none');
        form.classList.add('d-none');
        submit.classList.add('d-none');
        document.getElementById('prospect-modal').dataset.created = '1';
    } catch (error) {
        showProspectErrors({ __all__: ["Impossibile creare il fornitore: riprova piu' tardi."] });
    } finally {
        submit.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const prospectModal = document.getElementById('prospect-modal');
    if (prospectModal) {
        prospectModal.addEventListener('show.bs.modal', resetProspectForm);
        // Il fornitore appena creato compare nell'elenco solo dopo un ricaricamento.
        prospectModal.addEventListener('hidden.bs.modal', function() {
            if (prospectModal.dataset.created === '1') window.location.reload();
        });
        document.getElementById('prospect-form').addEventListener('submit', function(event) {
            event.preventDefault();
            submitProspect();
        });
    }
    const tbody = document.getElementById('vendors-table-body');
    tbody.addEventListener('click', function(event) {
        const button = event.target.closest('.btn-vendor-detail');
        if (button) openVendorDetail(button.dataset.vendorCode, button.dataset.vendorName);
    });
});
