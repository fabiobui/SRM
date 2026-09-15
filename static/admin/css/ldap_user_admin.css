/**
 * JavaScript per la gestione dinamica del form di creazione utenti LDAP/Locali
 */

document.addEventListener('DOMContentLoaded', function() {
    // Inizializza la visibilità dei campi al caricamento della pagina
    const userTypeField = document.getElementById('id_user_type');
    const roleField = document.getElementById('id_role');
    
    if (userTypeField) {
        togglePasswordFields(userTypeField.value);
        userTypeField.addEventListener('change', function() {
            togglePasswordFields(this.value);
        });
    }
    
    if (roleField) {
        toggleVendorField(roleField.value);
        roleField.addEventListener('change', function() {
            toggleVendorField(this.value);
        });
    }
});

/**
 * Mostra/nasconde i campi password in base al tipo di utente
 */
function togglePasswordFields(userType) {
    const password1Row = document.querySelector('.field-password1');
    const password2Row = document.querySelector('.field-password2');
    const password1Field = document.getElementById('id_password1');
    const password2Field = document.getElementById('id_password2');
    
    if (userType === 'ldap') {
        // Nasconde i campi password per utenti LDAP
        if (password1Row) password1Row.style.display = 'none';
        if (password2Row) password2Row.style.display = 'none';
        
        // Rimuove la validazione required
        if (password1Field) password1Field.required = false;
        if (password2Field) password2Field.required = false;
        
        // Mostra un messaggio informativo
        showLdapInfo();
    } else {
        // Mostra i campi password per utenti locali
        if (password1Row) password1Row.style.display = 'block';
        if (password2Row) password2Row.style.display = 'block';
        
        // Aggiunge la validazione required
        if (password1Field) password1Field.required = true;
        if (password2Field) password2Field.required = true;
        
        // Nasconde il messaggio informativo
        hideLdapInfo();
    }
}

/**
 * Mostra/nasconde il campo vendor in base al ruolo
 */
function toggleVendorField(role) {
    const vendorRow = document.querySelector('.field-vendor');
    const vendorField = document.getElementById('id_vendor');
    
    if (role === 'vendor') {
        // Mostra il campo vendor per utenti vendor
        if (vendorRow) {
            vendorRow.style.display = 'block';
            vendorRow.classList.add('required');
        }
        if (vendorField) vendorField.required = true;
    } else {
        // Nasconde il campo vendor per altri ruoli
        if (vendorRow) {
            vendorRow.style.display = 'none';
            vendorRow.classList.remove('required');
        }
        if (vendorField) {
            vendorField.required = false;
            vendorField.value = '';
        }
    }
}

/**
 * Mostra un messaggio informativo per utenti LDAP
 */
function showLdapInfo() {
    // Rimuove il messaggio esistente se presente
    hideLdapInfo();
    
    const userTypeRow = document.querySelector('.field-user_type');
    if (userTypeRow) {
        const infoDiv = document.createElement('div');
        infoDiv.id = 'ldap-info-message';
        infoDiv.className = 'help';
        infoDiv.innerHTML = '<strong>Nota:</strong> Per gli utenti LDAP, l\'autenticazione avviene tramite il server LDAP configurato. La password verrà gestita automaticamente dal sistema LDAP.';
        infoDiv.style.marginTop = '10px';
        infoDiv.style.padding = '10px';
        infoDiv.style.backgroundColor = '#e7f3ff';
        infoDiv.style.border = '1px solid #b3d9ff';
        infoDiv.style.borderRadius = '4px';
        
        userTypeRow.appendChild(infoDiv);
    }
}

/**
 * Nasconde il messaggio informativo per utenti LDAP
 */
function hideLdapInfo() {
    const existingInfo = document.getElementById('ldap-info-message');
    if (existingInfo) {
        existingInfo.remove();
    }
}

/**
 * Valida il form prima dell'invio
 */
document.addEventListener('submit', function(e) {
    const form = e.target;
    if (form.classList.contains('form-horizontal')) {
        const userType = document.getElementById('id_user_type');
        const role = document.getElementById('id_role');
        const vendor = document.getElementById('id_vendor');
        const password1 = document.getElementById('id_password1');
        
        // Validazione per utenti locali
        if (userType && userType.value === 'local') {
            if (!password1 || !password1.value.trim()) {
                alert('La password è obbligatoria per gli utenti locali.');
                e.preventDefault();
                return false;
            }
        }
        
        // Validazione per utenti vendor
        if (role && role.value === 'vendor') {
            if (!vendor || !vendor.value) {
                alert('Seleziona un fornitore per gli utenti di tipo "Fornitore".');
                e.preventDefault();
                return false;
            }
        }
    }
});