/*
 * Set Servizi applier
 * -------------------
 * Dropdown "Set Servizi" nel tab "Servizi" del VendorAdmin. Scegliendo un set
 * (modello vendors.ServiceSet) e cliccando "Applica set" vengono create le
 * righe dell'inline per ogni servizio del set.
 */
window.vmsSetApplier({
    fieldSuffix: '-service_type',
    endpoint: 'service-sets/',
    label: 'Set Servizi'
});
