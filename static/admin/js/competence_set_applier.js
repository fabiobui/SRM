/*
 * Set Requisiti Professionali applier
 * -----------------------------------
 * Dropdown "Set Requisiti" nel tab "Requisiti Professionali" del VendorAdmin.
 * Scegliendo un set (modello vendors.CompetenceSet) e cliccando "Applica set"
 * vengono create le righe dell'inline per ogni requisito del set.
 */
window.vmsSetApplier({
    fieldSuffix: '-competence',
    endpoint: 'competence-sets/',
    label: 'Set Requisiti'
});
