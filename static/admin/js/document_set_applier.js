/*
 * Set Documentale applier
 * -----------------------
 * Dropdown "Set Documentale" nel tab "Documenti" del VendorAdmin. Scegliendo un
 * set (modello documents.DocumentSet) e cliccando "Applica set" vengono create
 * le righe dell'inline Documenti per ogni tipo di documento del set,
 * impostando lo stato predefinito del set.
 */
window.vmsSetApplier({
    fieldSuffix: '-document_type',
    endpoint: 'document-sets/',
    label: 'Set Documentale',
    itemsKey: 'document_types',
    onRow: function (row, set) {
        var sel = row.querySelector('select[name$="-status"]');
        if (sel) {
            sel.value = set.default_status || 'PENDING';
            window.vmsSetApplier.notifyChange(sel);
        }
    }
});
