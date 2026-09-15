# Filtri Avanzati Dashboard - Guida Utente

## Panoramica

La dashboard dei fornitori ora include una sezione di **Filtri Avanzati** simile a Redmine, che permette di applicare filtri complessi su qualsiasi campo del database dei fornitori.

## Caratteristiche Principali

### 1. Pannello Filtri Espandibile
- Posizionato sotto le statistiche principali
- Mostra/nascondi con un click
- Badge con contatore filtri attivi

### 2. Filtri Multipli
- Aggiungi quanti filtri vuoi con il pulsante "Aggiungi Filtro"
- Ogni filtro è composto da:
  - **Campo**: il campo del database su cui filtrare
  - **Operatore**: tipo di confronto da applicare
  - **Valore**: valore da cercare (quando richiesto)

### 3. Campi Disponibili

#### Informazioni Generali
- **Nome**: nome del fornitore
- **Codice Fornitore**: codice univoco
- **Tipo Fornitore**: società, professionista, ecc.
- **Email**: indirizzo email
- **Telefono**: numero di telefono
- **Partita IVA**: P.IVA
- **Codice Fiscale**: C.F.

#### Stato e Valutazione
- **Stato Qualifica**: PENDING, APPROVED, REJECTED
- **Valutazione Finale**: DA VALUTARE, NEGATIVO, POSITIVO, MOLTO POSITIVO
- **Valutazione Qualità**: punteggio medio qualità (0-5)
- **Tasso Adempimento**: percentuale (0-100)
- **Attivo**: se il fornitore è attivo
- **Consulente ICO**: se è un consulente ICO
- **Stato Contrattuale**: stato del contratto

#### Localizzazione
- **Città**: città del fornitore
- **Regione**: regione
- **Provincia**: provincia
- **Paese**: paese

#### Classificazione
- **Categoria**: categoria merceologica
- **Tipo Servizio**: tipologia di servizio offerto

### 4. Operatori per Tipo di Campo

#### Campi di Testo
- **contiene**: il campo contiene il testo specificato
- **non contiene**: il campo non contiene il testo
- **è uguale a**: corrispondenza esatta
- **è diverso da**: qualsiasi valore tranne quello specificato
- **inizia con**: il campo inizia con il testo
- **finisce con**: il campo finisce con il testo
- **è vuoto**: campo senza valore
- **non è vuoto**: campo con un valore

#### Campi Numerici
- **è uguale a**: valore esatto
- **è diverso da**: qualsiasi valore tranne quello specificato
- **è maggiore di**: valore superiore
- **è minore di**: valore inferiore
- **è maggiore o uguale a**: valore uguale o superiore
- **è minore o uguale a**: valore uguale o inferiore
- **è vuoto**: campo nullo
- **non è vuoto**: campo con un valore

#### Campi di Selezione (Dropdown)
- **è uguale a**: valore selezionato
- **è diverso da**: qualsiasi altro valore
- **è vuoto**: nessuna selezione
- **non è vuoto**: qualsiasi selezione

#### Campi Booleani (Sì/No)
- **è vero**: campo impostato a vero
- **è falso**: campo impostato a falso o nullo

## Come Utilizzare i Filtri

### Aggiungere un Filtro

1. Clicca su "**Mostra**" per espandere il pannello filtri
2. Clicca su "**Aggiungi Filtro**" (verde con icona +)
3. Seleziona il **campo** dal primo dropdown
4. Seleziona l'**operatore** dal secondo dropdown
5. Inserisci il **valore** (se richiesto dall'operatore)
6. Clicca su "**Applica Filtri**" (blu con icona ✓)

### Esempi Pratici

#### Esempio 1: Trovare tutti i fornitori attivi di Milano
```
Campo: Città
Operatore: è uguale a
Valore: Milano

Campo: Attivo
Operatore: è vero
```

#### Esempio 2: Fornitori con valutazione positiva e tasso adempimento alto
```
Campo: Valutazione Finale
Operatore: è uguale a
Valore: MOLTO POSITIVO

Campo: Tasso Adempimento
Operatore: è maggiore o uguale a
Valore: 80
```

#### Esempio 3: Società senza Partita IVA
```
Campo: Tipo Fornitore
Operatore: è uguale a
Valore: Società

Campo: Partita IVA
Operatore: è vuoto
```

#### Esempio 4: Fornitori della Lombardia con email Gmail
```
Campo: Regione
Operatore: è uguale a
Valore: Lombardia

Campo: Email
Operatore: finisce con
Valore: @gmail.com
```

### Rimuovere un Filtro

- **Singolo filtro**: clicca sull'icona cestino (🗑️) nella riga del filtro
- **Tutti i filtri avanzati**: clicca su "**Cancella Tutti**"
- **Filtro attivo**: clicca sulla "**✕**" nel badge del filtro applicato

### Visualizzare i Filtri Attivi

I filtri attivi sono visualizzati in due modi:

1. **Badge nel pannello**: numero di filtri attivi accanto al titolo
2. **Sezione "Filtri Attivi"**: mostra tutti i filtri applicati con badge colorati
   - **Filtri standard** (da grafici): badge grigi
   - **Filtri avanzati**: badge viola/gradiente

## Integrazione con Altri Filtri

I filtri avanzati lavorano in combinazione con:
- **Filtri dai grafici**: clic sui grafici per filtrare
- **Barra di ricerca**: ricerca full-text
- **Filtri rapidi**: dalle card statistiche

Tutti i filtri sono applicati in modalità **AND** (devono essere tutti soddisfatti).

## Funzionalità Aggiuntive

### Cancella Tutti i Filtri
Il pulsante "**Cancella tutti i filtri**" nella sezione "Filtri Attivi" rimuove:
- Tutti i filtri avanzati
- Tutti i filtri dai grafici
- Il testo della ricerca

### Esportazione Excel
L'esportazione in Excel rispetta tutti i filtri applicati, inclusi quelli avanzati.

### Aggiornamento Dinamico
Quando applichi i filtri:
- La tabella viene aggiornata immediatamente
- Le statistiche vengono ricalcolate
- I grafici si aggiornano per riflettere i dati filtrati
- Il contatore "Selezionati" mostra il numero di fornitori che soddisfano i criteri

## Note Tecniche

### Compatibilità Browser
- Testato su Chrome, Firefox, Safari, Edge moderni
- Richiede JavaScript abilitato

### Performance
- Filtri applicati lato client per prestazioni ottimali
- Nessun caricamento aggiuntivo dal server
- Risposta istantanea anche con molti filtri

### Limitazioni
- I filtri su campi nested (es. `address.city`) possono non funzionare se il fornitore non ha un indirizzo
- I campi null/vuoti vengono gestiti automaticamente dagli operatori "è vuoto"/"non è vuoto"

## Suggerimenti per l'Uso

1. **Inizia con filtri ampi**: applica prima i filtri più generici, poi affina
2. **Combina operatori**: usa "è uguale a" per valori precisi, "contiene" per ricerche più ampie
3. **Salva filtri comuni**: considera di documentare combinazioni di filtri usate frequentemente
4. **Verifica risultati**: controlla sempre il numero di fornitori selezionati dopo aver applicato i filtri
5. **Usa "non è vuoto"**: per assicurarti che un campo sia compilato

## Risoluzione Problemi

### Nessun risultato trovato
- Verifica che i valori inseriti siano corretti
- Rimuovi un filtro alla volta per identificare quello troppo restrittivo
- Controlla gli operatori (es. "è uguale a" vs "contiene")

### I filtri non si applicano
- Assicurati di cliccare su "**Applica Filtri**" dopo aver configurato i filtri
- Verifica che ogni filtro abbia campo, operatore e valore (se richiesto) impostati

### Badge filtri non aggiornato
- Ricarica la pagina se il badge non si aggiorna
- Verifica la console JavaScript per eventuali errori

## Roadmap Future

Funzionalità in sviluppo:
- [ ] Salvataggio di set di filtri personalizzati
- [ ] Condivisione URL con filtri pre-impostati
- [ ] Filtri su date (es. data contratto, data qualifica)
- [ ] Operatore OR tra gruppi di filtri
- [ ] Export configurazione filtri in JSON

---

**Versione**: 1.0  
**Data**: 13 Novembre 2025  
**Autore**: Sistema SRM - Vendor Management
