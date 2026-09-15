# Testing Guide - Filtri Avanzati Dashboard

## 🧪 Guida al Testing della Nuova Funzionalità

### Pre-requisiti
- Server Django in esecuzione
- Database con fornitori popolato
- Browser moderno (Chrome/Firefox/Safari/Edge)
- User autenticato con accesso alla dashboard

---

## 🚀 Test di Avvio Rapido

### 1. Accesso alla Dashboard
```bash
# Avvia il server se non già in esecuzione
python manage.py runserver

# Naviga a:
http://localhost:8000/vendors/dashboard/
```

**Verifica Visiva**:
- ✅ La pagina si carica senza errori
- ✅ Le statistiche in alto mostrano i conteggi corretti
- ✅ I grafici vengono renderizzati
- ✅ La card "Filtri Avanzati" è visibile

---

### 2. Test Apertura Pannello Filtri

**Azione**: Clicca su "Mostra" nel pannello "Filtri Avanzati"

**Risultato Atteso**:
- ✅ Il pannello si espande con animazione smooth
- ✅ Il pulsante cambia in "Nascondi"
- ✅ Compare automaticamente una riga filtro vuota
- ✅ Nessun errore nella console

**Console Check**:
```javascript
// Apri DevTools (F12) → Console
// Non devono apparire errori
```

---

### 3. Test Aggiunta Filtro Semplice

**Scenario**: Filtrare fornitori per città

**Steps**:
1. Apri il pannello filtri
2. Nel primo dropdown "Campo", seleziona **"Città"**
3. Nel secondo dropdown "Operatore", seleziona **"è uguale a"**
4. Nel campo "Valore", scrivi **"Milano"** (o una città presente nel tuo DB)
5. Clicca su **"Applica Filtri"**

**Risultato Atteso**:
- ✅ Badge contatore mostra "1" accanto a "Filtri Avanzati"
- ✅ Appare sezione "Filtri Attivi" con badge viola
- ✅ Badge mostra: "Città è uguale a "Milano" ✕"
- ✅ Tabella aggiornata con solo fornitori di Milano
- ✅ Contatore "Selezionati" aggiornato
- ✅ Statistiche ricalcolate

**Debug**:
```javascript
// Console
console.log(advancedFilters);
// Dovrebbe mostrare: [{field: "address.city", operator: "equals", value: "Milano", label: "Città"}]
```

---

### 4. Test Filtri Multipli

**Scenario**: Fornitori attivi di Milano

**Steps**:
1. (Continua dal test precedente con filtro "Città = Milano")
2. Clicca su **"Aggiungi Filtro"**
3. Nel nuovo filtro:
   - Campo: **"Attivo"**
   - Operatore: **"è vero"**
4. Clicca su **"Applica Filtri"**

**Risultato Atteso**:
- ✅ Badge contatore mostra "2"
- ✅ Due badge viola nei "Filtri Attivi"
- ✅ Tabella mostra solo fornitori attivi di Milano
- ✅ Entrambi i filtri applicati in AND logic

---

### 5. Test Operatori su Campi Numerici

**Scenario**: Fornitori con alta qualità

**Steps**:
1. Cancella i filtri precedenti (pulsante "Cancella Tutti")
2. Aggiungi nuovo filtro:
   - Campo: **"Valutazione Qualità"**
   - Operatore: **"è maggiore o uguale a"**
   - Valore: **"4"**
3. Applica filtri

**Risultato Atteso**:
- ✅ Mostra solo fornitori con quality_rating_avg >= 4
- ✅ Badge mostra valore numerico correttamente
- ✅ Nessun fornitore con qualità inferiore

**Verifica Dati**:
```javascript
// Console
filteredVendors.forEach(v => {
    console.log(`${v.name}: ${v.quality_rating_avg}`);
    // Tutti i valori dovrebbero essere >= 4
});
```

---

### 6. Test Operatore "è vuoto"

**Scenario**: Trovare fornitori senza email

**Steps**:
1. Nuovo filtro:
   - Campo: **"Email"**
   - Operatore: **"è vuoto"**
2. Nota: il campo "Valore" dovrebbe nascondersi
3. Applica filtri

**Risultato Atteso**:
- ✅ Campo valore nascosto quando "è vuoto" è selezionato
- ✅ Badge non mostra valore (solo "Email è vuoto")
- ✅ Tabella mostra fornitori con email null/vuoto

---

### 7. Test Select con Opzioni

**Scenario**: Filtrare per tipo fornitore

**Steps**:
1. Nuovo filtro:
   - Campo: **"Tipo Fornitore"**
2. Verifica: il campo valore diventa un dropdown
3. Operatore: **"è uguale a"**
4. Valore: seleziona **"Società"** dal dropdown
5. Applica

**Risultato Atteso**:
- ✅ Campo valore trasformato in select
- ✅ Dropdown popolato con opzioni corrette
- ✅ Filtro applicato correttamente

---

### 8. Test Rimozione Filtro Singolo

**Scenario**: Rimuovere un filtro specifico

**Setup**:
1. Applica 3 filtri diversi
2. Verifica che tutti e 3 siano nei "Filtri Attivi"

**Steps**:
1. Clicca sulla **✕** nel badge del secondo filtro
2. Osserva i risultati

**Risultato Atteso**:
- ✅ Filtro rimosso dalla lista attiva
- ✅ Badge contatore decrementato (3 → 2)
- ✅ Tabella riaggiornata senza quel filtro
- ✅ Altri filtri ancora attivi

---

### 9. Test Cancella Tutti

**Steps**:
1. Applica alcuni filtri
2. Aggiungi anche filtri dai grafici (clicca su un grafico)
3. Clicca su **"Cancella tutti i filtri"** nella sezione "Filtri Attivi"

**Risultato Atteso**:
- ✅ Tutti i filtri avanzati rimossi
- ✅ Tutti i filtri grafici rimossi
- ✅ Badge contatore nascosto
- ✅ Sezione "Filtri Attivi" nascosta
- ✅ Tabella mostra tutti i fornitori
- ✅ Statistiche resettate

---

### 10. Test Integrazione con Ricerca

**Scenario**: Combinare filtri avanzati con ricerca testuale

**Steps**:
1. Applica filtro: Regione = "Lombardia"
2. Nella barra di ricerca, digita "consulting"
3. Osserva i risultati

**Risultato Atteso**:
- ✅ Mostra solo fornitori della Lombardia il cui nome contiene "consulting"
- ✅ Entrambi i filtri attivi simultaneamente
- ✅ Conteggio "Selezionati" corretto

---

### 11. Test Export Excel

**Scenario**: Verificare che l'export rispetti i filtri

**Steps**:
1. Applica filtri: Città = "Roma", Attivo = vero
2. Verifica conteggio (es. 45 fornitori)
3. Clicca su pulsante **"Esporta Excel"**
4. Apri il file scaricato

**Risultato Atteso**:
- ✅ File Excel scaricato
- ✅ Contiene esattamente 45 righe (+ header)
- ✅ Tutti i fornitori sono di Roma e attivi
- ✅ Nessun altro fornitore presente

---

### 12. Test Operatori di Testo

**Scenario**: Test operatori "inizia con", "finisce con", "contiene"

**Test A - Inizia con**:
```
Campo: Nome
Operatore: inizia con
Valore: "Acme"
→ Dovrebbe mostrare: "Acme S.r.l.", "Acme Consulting", ecc.
```

**Test B - Finisce con**:
```
Campo: Email
Operatore: finisce con
Valore: "@gmail.com"
→ Dovrebbe mostrare solo fornitori con email Gmail
```

**Test C - Contiene**:
```
Campo: Nome
Operatore: contiene
Valore: "tech"
→ Dovrebbe mostrare: "ABC Technologies", "TechSoft", "Biotech Labs", ecc.
```

---

### 13. Test Campi Nested (Indirizzo)

**Scenario**: Filtrare su campi nested come address.city

**Steps**:
1. Campo: **"Provincia"** (che corrisponde a address.state_province)
2. Operatore: **"è uguale a"**
3. Valore: **"MI"** o altra sigla provincia
4. Applica

**Risultato Atteso**:
- ✅ Filtra correttamente su campo nested
- ✅ Gestisce fornitori senza indirizzo (esclusi)

---

### 14. Test Responsive Mobile

**Steps**:
1. Apri DevTools (F12)
2. Attiva Device Toolbar (Ctrl+Shift+M)
3. Seleziona "iPhone 12 Pro" o altro device
4. Testa tutte le funzionalità

**Risultato Atteso**:
- ✅ Pannello filtri responsive
- ✅ Dropdown utilizzabili
- ✅ Pulsanti cliccabili
- ✅ Badge leggibili
- ✅ Tabella con scroll orizzontale

---

### 15. Test Edge Cases

**Test A - Campo Vuoto**:
```
Lascia il campo "Valore" vuoto (per operatori che richiedono valore)
Clicca "Applica Filtri"
→ Filtro non dovrebbe essere applicato
```

**Test B - Tutti i Campi Non Selezionati**:
```
Riga filtro completamente vuota
Clicca "Applica Filtri"
→ Filtro ignorato, nessun errore
```

**Test C - Valore Non Numerico su Campo Numerico**:
```
Campo: Valutazione Qualità
Operatore: è maggiore di
Valore: "abc" (testo invece di numero)
→ Dovrebbe gestire gracefully (ignorare o convertire)
```

**Test D - Caratteri Speciali**:
```
Campo: Nome
Operatore: contiene
Valore: "O'Brien & Co."
→ Dovrebbe gestire apostrofi e caratteri speciali
```

---

## 🐛 Checklist Debugging

Se qualcosa non funziona, verifica:

### Console Errors
```javascript
// Apri Console (F12)
// Cerca errori in rosso

// Se vedi "advancedFilters is not defined":
→ Problema nell'inizializzazione variabili

// Se vedi "Cannot read property 'value' of null":
→ Elemento DOM non trovato, verifica ID
```

### Network Tab
```
// Verifica che i file JS/CSS siano caricati
dashboard.js: 200 OK
dashboard.css: 200 OK

// Verifica eventuali 404
```

### Element Inspection
```html
<!-- Verifica che il pannello esista -->
<div id="advanced-filters-body">...</div>

<!-- Verifica ID univoci -->
<select id="filter-field-1">
<select id="filter-operator-1">
<input id="filter-value-1">
```

---

## 📊 Test di Performance

### Test con Dataset Grande
```javascript
// Simula 1000 fornitori
// Applica 5 filtri simultaneamente
// Misura tempo di risposta

console.time('filter-apply');
applyAdvancedFilters();
console.timeEnd('filter-apply');

// Dovrebbe essere < 100ms
```

### Memory Leak Check
```javascript
// Apri DevTools → Performance
// Registra sessione
// Aggiungi/rimuovi 50 filtri
// Verifica memoria stabile
```

---

## ✅ Checklist Testing Completa

### Funzionalità Base
- [ ] Apertura/chiusura pannello
- [ ] Aggiunta riga filtro
- [ ] Rimozione riga filtro
- [ ] Selezione campo
- [ ] Selezione operatore
- [ ] Input valore
- [ ] Applica filtri
- [ ] Cancella tutti

### Tipi di Campo
- [ ] Campo testo
- [ ] Campo numero
- [ ] Campo select
- [ ] Campo booleano
- [ ] Campo nested (address.*)

### Operatori
- [ ] contiene
- [ ] non contiene
- [ ] è uguale a
- [ ] è diverso da
- [ ] inizia con
- [ ] finisce con
- [ ] è vuoto
- [ ] non è vuoto
- [ ] è maggiore di
- [ ] è minore di
- [ ] è maggiore o uguale
- [ ] è minore o uguale
- [ ] è vero
- [ ] è falso

### Integrazione
- [ ] Filtri + Grafici
- [ ] Filtri + Ricerca
- [ ] Filtri + Export Excel
- [ ] Multipli filtri (AND logic)

### UI/UX
- [ ] Badge contatore
- [ ] Badge filtri attivi
- [ ] Rimozione singola (✕)
- [ ] Animazioni smooth
- [ ] Responsive mobile
- [ ] Accessibilità keyboard

### Edge Cases
- [ ] Campo vuoto
- [ ] Caratteri speciali
- [ ] Fornitori senza dati
- [ ] Filtri contraddittori (0 risultati)

---

## 🎓 Test Script Automatico (Opzionale)

```javascript
// Script da incollare in Console per test rapido

function quickTest() {
    console.log('🧪 Starting Quick Test...');
    
    // Test 1: Open panel
    toggleAdvancedFilters();
    console.log('✅ Panel opened');
    
    // Test 2: Add filter
    addFilterRow();
    console.log('✅ Filter row added');
    
    // Test 3: Set values
    document.getElementById('filter-field-1').value = 'address.city';
    document.getElementById('filter-field-1').dispatchEvent(new Event('change'));
    
    setTimeout(() => {
        document.getElementById('filter-operator-1').value = 'equals';
        document.getElementById('filter-value-1').value = 'Milano';
        console.log('✅ Values set');
        
        // Test 4: Apply
        applyAdvancedFilters();
        console.log('✅ Filters applied');
        console.log('📊 Filtered vendors:', filteredVendors.length);
        
        // Test 5: Clear
        setTimeout(() => {
            clearAdvancedFilters();
            console.log('✅ Filters cleared');
            console.log('🎉 Quick Test Completed!');
        }, 1000);
    }, 500);
}

// Esegui test
quickTest();
```

---

## 📝 Report Bug Template

Se trovi un bug, segnala con questo formato:

```markdown
**Bug**: [Descrizione breve]

**Steps to Reproduce**:
1. Passo 1
2. Passo 2
3. Passo 3

**Expected**: [Cosa dovrebbe succedere]

**Actual**: [Cosa succede realmente]

**Browser**: Chrome 120 / Firefox 121 / ecc.

**Console Errors**:
```
[Copia errori dalla console]
```

**Screenshot**: [Se disponibile]
```

---

**Documento**: Testing Guide v1.0  
**Data**: 13 Novembre 2025  
**Tipo**: Manual & Automated Testing
