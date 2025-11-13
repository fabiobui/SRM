# Esempi Pratici - Filtri Avanzati Dashboard Fornitori

Questa guida fornisce esempi concreti di utilizzo dei filtri avanzati per rispondere a domande di business comuni.

## 📋 Indice Esempi

1. [Qualità e Performance](#qualità-e-performance)
2. [Localizzazione Geografica](#localizzazione-geografica)
3. [Stato Contrattuale](#stato-contrattuale)
4. [Dati Amministrativi](#dati-amministrativi)
5. [Ricerche Complesse](#ricerche-complesse)

---

## 🎯 Qualità e Performance

### Esempio 1: Fornitori Eccellenti
**Obiettivo**: Trovare fornitori con valutazione "MOLTO POSITIVO" e alto tasso di adempimento

```
Filtro 1:
  Campo: Valutazione Finale
  Operatore: è uguale a
  Valore: MOLTO POSITIVO

Filtro 2:
  Campo: Tasso Adempimento
  Operatore: è maggiore o uguale a
  Valore: 90
```

**Caso d'uso**: Identificare i fornitori top performer per progetti critici

---

### Esempio 2: Fornitori da Monitorare
**Obiettivo**: Fornitori attivi ma con bassa qualità

```
Filtro 1:
  Campo: Attivo
  Operatore: è vero

Filtro 2:
  Campo: Valutazione Qualità
  Operatore: è minore di
  Valore: 3

Filtro 3:
  Campo: Valutazione Finale
  Operatore: è diverso da
  Valore: MOLTO POSITIVO
```

**Caso d'uso**: Piano di miglioramento fornitori

---

### Esempio 3: Fornitori Non Valutati
**Obiettivo**: Identificare fornitori senza valutazione

```
Filtro 1:
  Campo: Valutazione Finale
  Operatore: è uguale a
  Valore: DA VALUTARE

Filtro 2:
  Campo: Attivo
  Operatore: è vero
```

**Caso d'uso**: Pianificare audit e valutazioni

---

## 🗺️ Localizzazione Geografica

### Esempio 4: Fornitori Lombardi
**Obiettivo**: Tutti i fornitori della Lombardia per progetto locale

```
Filtro 1:
  Campo: Regione
  Operatore: è uguale a
  Valore: Lombardia

Filtro 2:
  Campo: Attivo
  Operatore: è vero
```

**Caso d'uso**: Gara d'appalto regionale

---

### Esempio 5: Fornitori Multi-Sede (Milano-Roma)
**Obiettivo**: Fornitori nelle principali città italiane

```
Filtro 1:
  Campo: Città
  Operatore: contiene
  Valore: Milano

// OPPURE creare due ricerche separate e unire i risultati
```

**Note**: Per OR logic, effettuare ricerche separate

---

### Esempio 6: Fornitori Esteri
**Obiettivo**: Tutti i fornitori non italiani

```
Filtro 1:
  Campo: Paese
  Operatore: è diverso da
  Valore: Italia

Filtro 2:
  Campo: Paese
  Operatore: non è vuoto
```

**Caso d'uso**: Analisi fornitori internazionali

---

## 📄 Stato Contrattuale

### Esempio 7: Contratti in Scadenza
**Obiettivo**: Fornitori con stato contrattuale critico

```
Filtro 1:
  Campo: Stato Contrattuale
  Operatore: è uguale a
  Valore: 06
  
// Nota: 06 = Contratto Scaduto

Filtro 2:
  Campo: Attivo
  Operatore: è vero
```

**Caso d'uso**: Rinnovo contratti urgente

---

### Esempio 8: Fornitori Contrattualizzati e Qualificati
**Obiettivo**: Fornitori pronti all'uso

```
Filtro 1:
  Campo: Stato Contrattuale
  Operatore: è uguale a
  Valore: 04
  
// Nota: 04 = Contrattualizzato

Filtro 2:
  Campo: Stato Qualifica
  Operatore: è uguale a
  Valore: APPROVED
```

**Caso d'uso**: Shortlist fornitori per nuovo progetto

---

### Esempio 9: Fornitori in Attesa di RAI
**Obiettivo**: Pipeline contrattuale

```
Filtro 1:
  Campo: Stato Contrattuale
  Operatore: è uguale a
  Valore: 02
  
// Nota: 02 = Fare RAI
```

**Caso d'uso**: Follow-up processo di qualifica

---

## 🏢 Dati Amministrativi

### Esempio 10: Società Senza Partita IVA
**Obiettivo**: Identificare dati mancanti

```
Filtro 1:
  Campo: Tipo Fornitore
  Operatore: è uguale a
  Valore: Società

Filtro 2:
  Campo: Partita IVA
  Operatore: è vuoto
```

**Caso d'uso**: Data quality - completamento database

---

### Esempio 11: Fornitori con Email Gmail
**Obiettivo**: Filtrare per dominio email

```
Filtro 1:
  Campo: Email
  Operatore: finisce con
  Valore: @gmail.com

Filtro 2:
  Campo: Attivo
  Operatore: è vero
```

**Caso d'uso**: Analisi professionalità (email aziendale vs personale)

---

### Esempio 12: Professionisti con Codice Fiscale
**Obiettivo**: Liberi professionisti regolari

```
Filtro 1:
  Campo: Tipo Fornitore
  Operatore: contiene
  Valore: Professionista

Filtro 2:
  Campo: Codice Fiscale
  Operatore: non è vuoto
```

**Caso d'uso**: Verifica compliance fiscale

---

## 🔍 Ricerche Complesse

### Esempio 13: Consulenti ICO Certificati
**Obiettivo**: Consulenti specializzati attivi

```
Filtro 1:
  Campo: Consulente ICO
  Operatore: è vero

Filtro 2:
  Campo: Valutazione Finale
  Operatore: è uguale a
  Valore: MOLTO POSITIVO

Filtro 3:
  Campo: Stato Qualifica
  Operatore: è uguale a
  Valore: APPROVED
```

**Caso d'uso**: Team project di consulenza

---

### Esempio 14: Fornitori Nuovo Ingresso (Codice Recente)
**Obiettivo**: Fornitori con codici alti (recenti)

```
Filtro 1:
  Campo: Codice Fornitore
  Operatore: è maggiore di
  Valore: VEND001000
  
// Assumendo numerazione sequenziale
```

**Caso d'uso**: Analisi onboarding recente

---

### Esempio 15: Fornitori Premium per Area
**Obiettivo**: Top fornitori di una specifica regione

```
Filtro 1:
  Campo: Regione
  Operatore: è uguale a
  Valore: Emilia-Romagna

Filtro 2:
  Campo: Valutazione Finale
  Operatore: è uguale a
  Valore: MOLTO POSITIVO

Filtro 3:
  Campo: Tasso Adempimento
  Operatore: è maggiore o uguale a
  Valore: 85
```

**Caso d'uso**: Strategic sourcing regionale

---

### Esempio 16: Fornitori in Difficoltà
**Obiettivo**: Alert list per azione correttiva

```
Filtro 1:
  Campo: Valutazione Finale
  Operatore: è uguale a
  Valore: NEGATIVO

Filtro 2:
  Campo: Attivo
  Operatore: è vero

Filtro 3:
  Campo: Stato Contrattuale
  Operatore: è uguale a
  Valore: 04
```

**Caso d'uso**: Risk management - piano di miglioramento o sostituzione

---

### Esempio 17: Fornitori Internazionali Premium
**Obiettivo**: Partner strategici esteri

```
Filtro 1:
  Campo: Tipo Fornitore
  Operatore: è uguale a
  Valore: Internazionale

Filtro 2:
  Campo: Valutazione Qualità
  Operatore: è maggiore o uguale a
  Valore: 4

Filtro 3:
  Campo: Stato Qualifica
  Operatore: è uguale a
  Valore: APPROVED
```

**Caso d'uso**: Espansione mercati internazionali

---

### Esempio 18: Gap Analysis - Categoria Senza Email
**Obiettivo**: Identificare gap informativi per categoria

```
Filtro 1:
  Campo: Categoria
  Operatore: contiene
  Valore: Consulenza
  
// O altra categoria specifica

Filtro 2:
  Campo: Email
  Operatore: è vuoto
```

**Caso d'uso**: Campagna di raccolta contatti

---

## 💡 Tips & Tricks

### Suggerimento 1: Combinazione Filtri Grafici + Avanzati
1. Clicca su un grafico (es. Regione "Lazio")
2. Aggiungi filtro avanzato (es. Tipo = "Società")
3. Risultato: Società del Lazio

### Suggerimento 2: Ricerca Veloce con "contiene"
Per nomi parziali o keyword:
```
Campo: Nome
Operatore: contiene
Valore: consulting
```

### Suggerimento 3: Filtri Negativi
Per escludere valori:
```
Campo: Valutazione Finale
Operatore: è diverso da
Valore: DA VALUTARE
```

### Suggerimento 4: Verifica Completezza Dati
```
Campo: Telefono
Operatore: è vuoto
```
Ripeti per ogni campo obbligatorio

### Suggerimento 5: Export per Report
1. Applica filtri desiderati
2. Verifica contatore "Selezionati"
3. Click "Esporta Excel"
4. File generato con solo i record filtrati

---

## 🎓 Workflow Comuni

### Workflow 1: Audit Trimestrale Fornitori
```
Step 1: Filtra fornitori attivi
  → Attivo = è vero

Step 2: Escludi già valutati di recente
  → Valutazione Finale ≠ DA VALUTARE

Step 3: Focus su regione specifica
  → Regione = [Tua Regione]

Step 4: Export e assegna a team audit
```

### Workflow 2: Selezione Fornitori per Gara
```
Step 1: Categoria merceologica
  → Categoria = contiene [keyword]

Step 2: Solo qualificati
  → Stato Qualifica = APPROVED

Step 3: Performance minima
  → Tasso Adempimento ≥ 75

Step 4: Locali (se richiesto)
  → Regione = [Tua Regione]

Step 5: Export shortlist
```

### Workflow 3: Pulizia Database
```
Step 1: Identifica record incompleti
  → Email = è vuoto
  → Telefono = è vuoto
  
Step 2: Filter per inattivi
  → Attivo = è falso

Step 3: Export per verifica
Step 4: Contatta o archivia
```

---

## 📊 Analisi Suggerite

### Analisi 1: Distribuzione Performance
1. Filtra: Qualità ≥ 4
2. Osserva distribuzione geografica
3. Confronta con Qualità < 3

### Analisi 2: Correlazione Tipo-Performance
1. Filtra: Tipo = Società
2. Nota statistiche performance
3. Ripeti per Tipo = Professionista
4. Confronta risultati

### Analisi 3: Coverage Geografica
1. Per ogni regione, filtra fornitori attivi
2. Verifica copertura servizi
3. Identifica gap territoriali

---

## 🆘 Troubleshooting Filtri

### Problema: Nessun Risultato
**Soluzione**: Rimuovi filtri uno alla volta per identificare quello troppo restrittivo

### Problema: Troppi Risultati
**Soluzione**: Aggiungi filtri più specifici (da generali a dettaglio)

### Problema: Dati Inattesi
**Soluzione**: Verifica operatore (es. "contiene" vs "è uguale a")

---

**Documento aggiornato**: 13 Novembre 2025  
**Versione**: 1.0  
**Autori**: Team SRM
