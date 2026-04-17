# SRM — Manuale Utente Amministratore

> Guida operativa per la gestione dei fornitori tramite l'interfaccia di amministrazione.

---

## Sommario

1. [Accesso al sistema](#1-accesso-al-sistema)
2. [Dashboard e navigazione](#2-dashboard-e-navigazione)
3. [Anagrafica Fornitore](#3-anagrafica-fornitore)
   - 3.1 [Creare un nuovo fornitore](#31-creare-un-nuovo-fornitore)
   - 3.2 [Informazioni Base](#32-informazioni-base)
   - 3.3 [Contatti](#33-contatti)
   - 3.4 [Indirizzo (Sede)](#34-indirizzo-sede)
   - 3.5 [Stato Contrattuale](#35-stato-contrattuale)
   - 3.6 [Gestione e Zone di Competenza](#36-gestione-e-zone-di-competenza)
   - 3.7 [Servizi Medici](#37-servizi-medici)
   - 3.8 [Qualifica e Audit](#38-qualifica-e-audit)
4. [Lista Fornitori — ricerca e filtri](#4-lista-fornitori--ricerca-e-filtri)
5. [Azioni massive sui fornitori](#5-azioni-massive-sui-fornitori)
6. [Servizi del Fornitore](#6-servizi-del-fornitore)
7. [Requisiti Professionali (Competenze)](#7-requisiti-professionali-competenze)
   - 7.1 [Catalogo Requisiti](#71-catalogo-requisiti)
   - 7.2 [Assegnare requisiti a un fornitore](#72-assegnare-requisiti-a-un-fornitore)
8. [Documenti](#8-documenti)
   - 8.1 [Tipi di Documento](#81-tipi-di-documento)
   - 8.2 [Caricare un documento per un fornitore](#82-caricare-un-documento-per-un-fornitore)
9. [Contratti](#9-contratti)
10. [Valutazioni Fornitore](#10-valutazioni-fornitore)
11. [Ordini di Acquisto (Purchase Orders)](#11-ordini-di-acquisto-purchase-orders)
12. [Storico Performance](#12-storico-performance)
13. [Gestione Utenti](#13-gestione-utenti)
14. [Tabelle di Supporto](#14-tabelle-di-supporto)
    - 14.1 [Categorie Merceologiche](#141-categorie-merceologiche)
    - 14.2 [Tipologie / Servizi](#142-tipologie--servizi)
    - 14.3 [Titoli di Studio](#143-titoli-di-studio)
    - 14.4 [Nazioni, Regioni e Province](#144-nazioni-regioni-e-province)
    - 14.5 [Zone di Competenza](#145-zone-di-competenza)
    - 14.6 [Criteri e Frequenze di Valutazione](#146-criteri-e-frequenze-di-valutazione)
    - 14.7 [Valutatori](#147-valutatori)

---

## 1. Accesso al sistema

Aprire il browser e navigare all'indirizzo del sistema (es. `https://srm.esempio.it/admin/`).

Inserire le proprie credenziali:

| Campo    | Descrizione                     |
|----------|---------------------------------|
| **Email**    | L'indirizzo email aziendale     |
| **Password** | La password assegnata           |

> **Nota:** il sistema supporta anche l'autenticazione LDAP. Se il proprio account è di tipo LDAP, utilizzare le credenziali di dominio.

<!-- 📸 SCREENSHOT: Pagina di login -->

---

## 2. Dashboard e navigazione

Dopo il login si accede alla dashboard principale. Il menu laterale sinistro elenca tutte le sezioni disponibili.

Le sezioni principali sono:

| Sezione | Cosa contiene |
|---------|---------------|
| **Vendors** | Fornitori, Servizi, Requisiti, Contratti, Valutazioni |
| **Documents** | Tipi di Documento e Documenti caricati |
| **Purchase Orders** | Ordini di acquisto |
| **Historical Performances** | Storico delle performance |
| **Users** | Gestione utenti del sistema |

<!-- 📸 SCREENSHOT: Dashboard principale con menu laterale -->

---

## 3. Anagrafica Fornitore

### 3.1 Creare un nuovo fornitore

1. Dal menu laterale, cliccare su **Vendors → Fornitori**
2. Cliccare il pulsante **AGGIUNGI FORNITORE** in alto a destra
3. Si apre il form di creazione con diverse sezioni (fieldset)

> **Il codice fornitore** (`vendor_code`) viene generato automaticamente dal sistema e non è modificabile.

<!-- 📸 SCREENSHOT: Pulsante "Aggiungi Fornitore" nella lista -->

---

### 3.2 Informazioni Base

Questa è la prima sezione del form, contiene i dati identificativi del fornitore.

| Campo | Obbligatorio | Descrizione |
|-------|:---:|-------------|
| **Codice Fornitore** | Auto | Generato automaticamente, non modificabile |
| **Vecchio Codice** | No | Eventuale codice proveniente da sistemi precedenti |
| **Nome** | Sì | Ragione sociale o nome completo |
| **Tipo Fornitore** | Sì | Selezionare dal menu a tendina (default: *Società*) |
| **Partita IVA** | No | Partita IVA del fornitore |
| **Codice Fiscale** | No | Codice fiscale |
| **Titolo di Studio** | No | Selezionare il titolo di studio dal catalogo (utile per professionisti) |
| **Categoria** | No | Categoria merceologica di appartenenza |
| **Livello di Rischio** | No | `Basso`, `Medio` o `Alto` |
| **Valutazione Finale** | No | `Da Valutare`, `Negativo`, `Positivo`, `Molto Positivo` |
| **Attivo** | Sì | Spuntare per rendere il fornitore operativo |

**Tipi Fornitore disponibili:**

| Valore | Quando usarlo |
|--------|---------------|
| Società | Aziende e imprese |
| Professionista | Libero professionista con P.IVA |
| Dipendente | Collaboratore interno |
| Dipendente + Libero professionista | Ruolo misto |
| Disoccupato | Collaboratore non occupato |
| Libero Professionista | Professionista autonomo |
| Presso Studio | Professionista associato a uno studio |
| Prestazione Occasionale | Collaborazione occasionale |
| Società/professionista | Ibrido società-professionista |
| Internazionale | Fornitore estero |

<!-- 📸 SCREENSHOT: Sezione "Informazioni Base" del form fornitore -->

---

### 3.3 Contatti

| Campo | Obbligatorio | Descrizione |
|-------|:---:|-------------|
| **Email** | No | Email principale del fornitore |
| **Telefono** | No | Numero di telefono |
| **Contatto di Riferimento** | No | Nome della persona di riferimento |
| **Sito Web** | No | URL del sito web |
| **Indirizzo** | No | Selezionare un indirizzo dalla lente di ricerca (vedi [§3.4](#34-indirizzo-sede)) |
| **Dettagli Contatto** | No | Note aggiuntive sui contatti |

<!-- 📸 SCREENSHOT: Sezione "Contatti" del form fornitore -->

---

### 3.4 Indirizzo (Sede)

L'indirizzo del fornitore è un'entità separata. Per associare un indirizzo:

1. Cliccare l'icona **lente** accanto al campo *Indirizzo*
2. Cercare un indirizzo esistente oppure crearne uno nuovo cliccando **+**
3. Compilare i campi del nuovo indirizzo:

| Campo | Descrizione |
|-------|-------------|
| **Via** | Indirizzo principale |
| **Via (riga 2)** | Completamento indirizzo (opzionale) |
| **Città** | Città |
| **Provincia** | Provincia o stato |
| **Regione** | Regione |
| **CAP** | Codice avviamento postale |
| **Nazione** | Default: *Italia* |
| **Tipo Indirizzo** | `Legale`, `Operativo`, `Fatturazione`, `Spedizione`, `Altro` |

> **Coordinate GPS** (latitudine e longitudine) sono opzionali e disponibili in una sezione collassabile.

<!-- 📸 SCREENSHOT: Popup di creazione indirizzo -->

---

### 3.5 Stato Contrattuale

Questa sezione traccia lo stato dell'iter contrattuale con il fornitore.

| Campo | Descrizione |
|-------|-------------|
| **Stato Contrattuale** | Selezionare dallo stato corrente (vedi tabella sotto) |
| **Data Inizio Contratto** | Data di decorrenza |
| **Data Fine Contratto** | Data di scadenza |
| **Termini Contrattuali** | Note sui termini |
| **Persona di Riferimento** | Referente interno per il contratto |

**Stati Contrattuali:**

| Codice | Stato | Significato |
|:---:|-------|-------------|
| 00 | Da verificare | Stato iniziale — verifica in corso |
| 02 | Fare RAI | È necessario effettuare la RAI |
| 03 | RAI Effettuata | RAI completata, in attesa di contratto |
| 04 | Contrattualizzato | Fornitore con contratto attivo |
| 05 | Da contrattualizzare ad esigenza | Disponibile, da contrattualizzare quando necessario |
| 06 | Contratto Scaduto | Il contratto è scaduto |
| 99 | Non Usare | Fornitore disabilitato / non utilizzare |

<!-- 📸 SCREENSHOT: Sezione "Stato Contrattuale" -->

---

### 3.6 Gestione e Zone di Competenza

| Campo | Descrizione |
|-------|-------------|
| **Zone di Competenza** | Selezionare una o più zone geografiche di operatività (autocomplete) |
| **Zona Competenza (legacy)** | Campo testuale libero per compatibilità |
| **Aggiornamento Gestione** | Note sull'ultimo aggiornamento gestionale |
| **Descrizione Attività** | Descrizione delle attività svolte dal fornitore |

> Le **Zone di Competenza** sono definite tramite regole geografiche (Nazione / Regione / Provincia) con logica include/exclude. Vedere [§14.5](#145-zone-di-competenza) per la configurazione.

<!-- 📸 SCREENSHOT: Sezione "Gestione" con zone di competenza -->

---

### 3.7 Servizi Medici

> Questa sezione è **collassata** di default e va aperta solo per fornitori del settore medico/sanitario.

Contiene campi specifici per professionisti e strutture mediche:

| Campo | Descrizione |
|-------|-------------|
| **Cluster Corso** | Tipo di corso (es. Antincendio, Primo Soccorso, ecc.) |
| **Dispositivo Mobile** | Il fornitore dispone di dispositivo mobile |
| **Servizio Ambulatoriale** | Descrizione del servizio ambulatoriale |
| **Servizio Laboratorio** | Fornitore con servizio di laboratorio |
| **Laboratorio Indipendente** | Il laboratorio è indipendente |
| **Anno Abilitazione Medico** | Anno di abilitazione alla professione |
| **Servizio Medico** | Tipo di servizio medico erogato |
| **Altro Servizio Medico** | Descrizione di servizi non in elenco |
| **Iscrizione Albo Medico** | Dettagli iscrizione all'albo |
| **CV Medico** | Presenza CV |

<!-- 📸 SCREENSHOT: Sezione "Servizi Medici" espansa (se applicabile) -->

---

### 3.8 Qualifica e Audit

Questa sezione gestisce il processo di qualificazione e gli audit periodici.

| Campo | Modificabile | Descrizione |
|-------|:---:|-------------|
| **Stato Qualifica** | Sì | `In Attesa`, `Approvato`, `Rifiutato` |
| **Punteggio Qualifica** | Sì | Valore numerico da 0 a 100 |
| **Data Qualifica** | Sì | Data in cui è stata effettuata la qualifica |
| **Scadenza Qualifica** | Sì | Data di scadenza della qualifica |
| **Data Ultimo Audit** | Sì | Data dell'ultimo audit effettuato |
| **Prossimo Audit Previsto** | Sì | Data entro cui effettuare il prossimo audit |
| **Qualificato** | Solo lettura | ✅ se stato = *Approvato* e qualifica non scaduta |
| **Audit Scaduto** | Solo lettura | ✅ se la data del prossimo audit è passata |
| **Note di Revisione** | Sì | Annotazioni sulla revisione |

<!-- 📸 SCREENSHOT: Sezione "Qualifica e Audit" -->

---

## 4. Lista Fornitori — ricerca e filtri

La lista fornitori mostra le colonne principali:

| Colonna | Descrizione |
|---------|-------------|
| Codice | Codice fornitore univoco |
| Nome | Ragione sociale |
| Categoria | Categoria merceologica |
| Stato Qualifica | In Attesa / Approvato / Rifiutato |
| Livello Rischio | Basso / Medio / Alto |
| Qualificato | Icona ✅ o ❌ |
| Attivo | Stato attivo/disattivo |
| Punteggio | Punteggio di qualifica |

**Ricerca:** digitare nel campo di ricerca in alto per cercare per *codice fornitore*, *nome*, *partita IVA*, *codice fiscale* o *email*.

**Filtri laterali** (pannello destro):

- Stato Qualifica
- Livello di Rischio
- Attivo (Sì/No)
- Categoria
- Tipo Fornitore
- Stato Contrattuale
- Valutazione Finale

> **Suggerimento:** combinare più filtri per restringere rapidamente la ricerca. Ad esempio: *Stato Qualifica = Approvato* + *Attivo = Sì* per vedere solo i fornitori operativi.

<!-- 📸 SCREENSHOT: Lista fornitori con filtri laterali attivi -->

---

## 5. Azioni massive sui fornitori

Nella lista fornitori è possibile selezionare più righe e applicare **azioni massive** dal menu a tendina in alto:

| Azione | Effetto |
|--------|---------|
| **Approva fornitori selezionati** | Imposta lo stato qualifica su *Approvato* per tutti i selezionati |
| **Rifiuta fornitori selezionati** | Imposta lo stato qualifica su *Rifiutato* |
| **Programma audit** | Imposta la data del prossimo audit a 30 giorni da oggi |

**Come fare:**

1. Spuntare le caselle dei fornitori desiderati
2. Dal menu a tendina *Azione*, selezionare l'azione
3. Cliccare **Esegui**
4. Verificare il messaggio di conferma in alto

<!-- 📸 SCREENSHOT: Menu azioni massive con fornitori selezionati -->

---

## 6. Servizi del Fornitore

I servizi vengono gestiti **direttamente nella scheda del fornitore**, tramite la sezione inline in basso.

Ogni riga della tabella rappresenta un servizio erogato:

| Campo | Descrizione |
|-------|-------------|
| **Tipologia/Servizio** | Selezionare dal catalogo dei servizi |
| **Primario** | Spuntare se è il servizio principale del fornitore |
| **Tariffa Oraria** | Costo orario in € (opzionale) |
| **Data Inizio** | Da quando il fornitore eroga questo servizio |
| **Data Fine** | Eventuale data di cessazione |
| **Contratto** | Contratto collegato (opzionale) |
| **Note** | Note libere |

**Per aggiungere un servizio:** cliccare il link *Aggiungi un altro Servizio Fornitore* in fondo alla sezione inline.

**Per rimuovere un servizio:** spuntare la casella *Elimina* sulla riga corrispondente e salvare.

> Un cerchio verde (✓) nella colonna *Attivo* indica che la data odierna è compresa nel periodo inizio-fine.

<!-- 📸 SCREENSHOT: Inline servizi nella scheda fornitore -->

---

## 7. Requisiti Professionali (Competenze)

### 7.1 Catalogo Requisiti

Prima di assegnare requisiti ai fornitori, verificare il catalogo.

Da **Vendors → Requisiti Professionali** si accede all'elenco completo.

Ogni requisito ha:

| Campo | Descrizione |
|-------|-------------|
| **Codice** | Codice univoco del requisito |
| **Nome** | Denominazione |
| **Categoria** | `Sicurezza`, `Qualità`, `Tecnico`, `Energia`, `Ambiente`, `Audit`, `Altro` |
| **Obbligatorio** | Se è mandatorio per i fornitori delle categorie collegate |
| **Richiede Certificazione** | Se serve un certificato a supporto |
| **Richiede Rinnovo** | Se ha una scadenza e va rinnovato |
| **Attivo** | Se è attualmente in uso |

> I campi *Obbligatorio* e *Attivo* sono modificabili direttamente dalla lista, senza aprire la scheda.

<!-- 📸 SCREENSHOT: Lista catalogo requisiti -->

---

### 7.2 Assegnare requisiti a un fornitore

I requisiti si assegnano **dalla scheda del fornitore**, nella sezione inline dedicata.

Per ogni requisito assegnato compilare:

| Campo | Descrizione |
|-------|-------------|
| **Requisito** | Selezionare dal catalogo |
| **Tipo:** È Competenza | Spuntare se è una competenza professionale |
| **Tipo:** È Qualifica | Spuntare se è una qualifica |
| **Tipo:** È Iscrizione Albo | Spuntare se è un'iscrizione a un albo |
| **Possiede Competenza** | Il fornitore dichiara di possedere il requisito |
| **Ha Certificazione** | Il fornitore ha un certificato che lo attesta |
| **Numero Certificato** | Numero identificativo del certificato |
| **Ente Certificatore** | Nome dell'ente che ha rilasciato il certificato |
| **Data Rilascio** | Data di emissione del certificato |
| **Data Scadenza** | Data di scadenza del certificato |
| **Verificato** | Spuntare dopo la verifica dell'ufficio |
| **Verificato Da** | Nome di chi ha verificato |
| **Data Verifica** | Data della verifica |
| **File Documento** | Caricare il file del certificato |
| **Note** | Note libere |

**Stato scadenza:** nella lista viene mostrato un badge colorato:

| Colore | Significato |
|--------|-------------|
| 🟢 Verde | Valido |
| 🟡 Giallo | In scadenza (entro 90 giorni) |
| 🟠 Arancione | In scadenza imminente (entro 30 giorni) |
| 🔴 Rosso | Scaduto |
| ⚪ Grigio | Nessuna scadenza impostata |

<!-- 📸 SCREENSHOT: Inline requisiti con badge scadenza nella scheda fornitore -->

---

## 8. Documenti

### 8.1 Tipi di Documento

Da **Documents → Tipi di Documento** si configura il catalogo dei documenti gestiti dal sistema.

| Campo | Descrizione |
|-------|-------------|
| **Codice** | Codice univoco |
| **Nome** | Denominazione del tipo di documento |
| **Categoria** | `Legale`, `Finanziario`, `Sicurezza`, `Qualità`, `Tecnico`, `Assicurativo`, `Certificazione`, `Altro` |
| **Obbligatorio** | Se il documento è richiesto |
| **Richiede Rinnovo** | Se ha una scadenza |
| **Validità (giorni)** | Durata standard in giorni (default: 365) |
| **Giorni Promemoria** | Quanti giorni prima della scadenza inviare il promemoria (default: 30) |
| **Categorie Applicabili** | A quali categorie merceologiche si applica questo tipo di documento |
| **Template** | File template scaricabile dal fornitore |
| **Istruzioni** | Istruzioni per la compilazione |

> I campi *Attivo* e *Obbligatorio* sono modificabili direttamente dalla lista.

<!-- 📸 SCREENSHOT: Lista tipi di documento -->

---

### 8.2 Caricare un documento per un fornitore

I documenti vengono caricati **dalla scheda del fornitore**, nella sezione inline.

| Campo | Descrizione |
|-------|-------------|
| **Tipo Documento** | Selezionare dal catalogo |
| **File** | Caricare il file (PDF, immagini, ecc.) |
| **Stato** | `In Attesa`, `Caricato`, `Approvato`, `Rifiutato`, `Scaduto` |
| **Data Rilascio** | Data di emissione del documento |
| **Data Scadenza** | Data di scadenza |
| **Revisionato Da** | Utente che ha eseguito la revisione |
| **Data Revisione** | Data della revisione |
| **Note** | Note aggiuntive |

**Flusso tipico:**

1. Caricare il file e impostare stato **Caricato**
2. Verificare il documento e impostare stato **Approvato** o **Rifiutato**
3. Se il documento scade, il sistema lo segnalerà automaticamente

> Nella scheda del fornitore sono visibili (in sola lettura) i conteggi automatici: *Documenti validi*, *Documenti scaduti*, *Documenti in scadenza*, *Documenti obbligatori mancanti*.

<!-- 📸 SCREENSHOT: Inline documenti nella scheda fornitore -->

---

## 9. Contratti

I contratti sono gestibili sia dalla sezione dedicata (**Vendors → Contratti**) sia dalla scheda del fornitore (inline).

| Campo | Descrizione |
|-------|-------------|
| **Numero Contratto** | Codice univoco del contratto |
| **Titolo** | Descrizione breve del contratto |
| **Fornitore** | Fornitore collegato |
| **Stato** | `Bozza`, `Attivo`, `Scaduto`, `Terminato`, `Sospeso` |
| **Data Inizio** | Decorrenza del contratto |
| **Data Fine** | Scadenza |
| **Importo** | Valore economico in € |
| **Note** | Note libere |

<!-- 📸 SCREENSHOT: Lista contratti o inline nella scheda fornitore -->

---

## 10. Valutazioni Fornitore

Le valutazioni si assegnano **dalla scheda del fornitore**, nella sezione inline, oppure dalla sezione dedicata **Vendors → Valutazioni Fornitori**.

Ogni valutazione associa un **criterio** a un **punteggio**:

| Campo | Descrizione |
|-------|-------------|
| **Criterio** | Selezionare dal catalogo (vedi [§14.6](#146-criteri-e-frequenze-di-valutazione)) |
| **Punteggio** | Scala da 1 a 8 |
| **Valutatore** | Chi ha effettuato la valutazione |
| **Frequenza** | Ogni quanti mesi ripetere la valutazione |
| **Note** | Commenti sulla valutazione |
| **Data** | Compilata automaticamente alla creazione |

**Scala di valutazione:**

| Punteggio | Giudizio |
|:---------:|----------|
| 1 | Scarso |
| 2 | Insufficiente |
| 3 | Non sufficiente |
| 4 | Al limite |
| 5 | Sufficiente |
| 6 | Buono |
| 7 | Ottimo |
| 8 | Eccellente |

> Per ogni coppia fornitore-criterio è ammessa una sola valutazione. Per aggiornare il punteggio, modificare la riga esistente.

<!-- 📸 SCREENSHOT: Inline valutazioni nella scheda fornitore -->

---

## 11. Ordini di Acquisto (Purchase Orders)

Da **Purchase Orders → Ordini di Acquisto**.

| Campo | Descrizione |
|-------|-------------|
| **Numero OdA** | Generato automaticamente, non modificabile |
| **Fornitore** | Selezionare il fornitore |
| **Stato** | `In Attesa`, `Emesso`, `Confermato`, `Consegnato`, `Annullato` |
| **Valutazione Qualità** | Da 1 a 5 (dopo la consegna) |
| **Data Ordine** | Data di creazione (default: oggi) |
| **Data Consegna Prevista** | Calcolata automaticamente a +21 giorni se non specificata |
| **Data Consegna Effettiva** | Da compilare alla ricezione |
| **Data Emissione** | Quando l'ordine è stato emesso |
| **Data Conferma** | Quando il fornitore ha confermato |
| **Articoli (Items)** | Campo JSON con l'elenco degli articoli |
| **Quantità** | Quantità totale (minimo 1) |

<!-- 📸 SCREENSHOT: Form ordine di acquisto -->

---

## 12. Storico Performance

Da **Historical Performances → Storico Performance**.

Questa sezione è in **sola lettura** e mostra l'evoluzione nel tempo delle metriche di performance di ciascun fornitore:

| Metrica | Descrizione | Range |
|---------|-------------|-------|
| **Tasso Consegna Puntuale** | Percentuale consegne nei tempi | 0–100% |
| **Media Valutazione Qualità** | Punteggio medio qualità | 0–5 |
| **Tempo Medio di Risposta** | Tempo medio in ore | ≥ 0 |
| **Tasso di Completamento** | Percentuale ordini completati | 0–100% |

> Questi dati vengono calcolati e aggiornati automaticamente dal sistema.

<!-- 📸 SCREENSHOT: Lista storico performance -->

---

## 13. Gestione Utenti

Da **Users → Utenti**.

### Creare un nuovo utente

1. Cliccare **AGGIUNGI UTENTE**
2. Compilare le informazioni base:

| Campo | Descrizione |
|-------|-------------|
| **Email** | Indirizzo email (sarà usato come username) |
| **Nome** | Nome completo |
| **Tipo Autenticazione** | *Locale* (password interna) oppure *LDAP* (autenticazione di dominio) |
| **Ruolo** | `Admin`, `BackOffice User`, `Vendor` |
| **Fornitore** | Solo per ruolo *Vendor*: selezionare il fornitore collegato |
| **Password** | Solo per utenti locali |

### Ruoli e permessi

| Ruolo | Accesso Admin | Gestione Fornitori | Gestione Documenti |
|-------|:---:|:---:|:---:|
| **Admin** | ✅ | ✅ | ✅ |
| **BackOffice User** | ✅ | ✅ | ✅ |
| **Vendor** | ❌ | Solo il proprio | Solo i propri |

> Gli utenti LDAP hanno email e nome in sola lettura (gestiti dal server di dominio).

<!-- 📸 SCREENSHOT: Form creazione utente -->

---

## 14. Tabelle di Supporto

Queste tabelle contengono i dati di riferimento utilizzati nelle altre sezioni.

### 14.1 Categorie Merceologiche

**Vendors → Categorie Merceologiche**

Struttura ad albero (genitore → figlio). Ogni categoria ha:

- **Codice** e **Nome**
- **Categoria padre** (opzionale, per la gerarchia)
- **Colore** (badge visivo nella lista)
- **Livello di Rischio di Default** (`Basso`, `Medio`, `Alto`)
- **Richiede Certificazione** (Sì/No)

<!-- 📸 SCREENSHOT: Lista categorie merceologiche -->

---

### 14.2 Tipologie / Servizi

**Vendors → Tipologie/Servizi**

Catalogo gerarchico dei servizi erogabili. I servizi senza genitore sono le *categorie*, i figli sono i servizi specifici.

- I campi **Attivo** e **Ordinamento** sono modificabili direttamente dalla lista.

<!-- 📸 SCREENSHOT: Lista tipologie/servizi -->

---

### 14.3 Titoli di Studio

**Vendors → Titoli di Studio**

Catalogo dei titoli di studio con livello EQF. Struttura gerarchica (genitore → figlio).

---

### 14.4 Nazioni, Regioni e Province

**Vendors → Nazioni / Regioni / Province**

Dati geografici usati per gli indirizzi e le zone di competenza.

- Le **Nazioni** hanno un codice ISO a 3 lettere
- Le **Regioni** sono collegate a una nazione
- Le **Province** sono collegate a una regione (sigla provincia)

---

### 14.5 Zone di Competenza

**Vendors → Zone di Competenza**

Ogni zona è definita da un insieme di **regole** che includono o escludono aree geografiche:

| Tipo Regola | Effetto |
|-------------|---------|
| **INCLUDE** | L'area è coperta dalla zona |
| **EXCLUDE** | L'area è esclusa dalla zona |

Le regole possono operare a livello di Nazione, Regione o Provincia.

**Esempio:** una zona "Nord Italia" potrebbe avere:
- INCLUDE → Regione Lombardia
- INCLUDE → Regione Piemonte
- INCLUDE → Regione Veneto
- EXCLUDE → Provincia di Belluno

<!-- 📸 SCREENSHOT: Scheda zona di competenza con regole inline -->

---

### 14.6 Criteri e Frequenze di Valutazione

**Vendors → Criteri di Valutazione**

I criteri sono raggruppati per categoria:

| Codice Categoria | Descrizione |
|:---:|-------------|
| COMM | Commerciale |
| CONS | Consulting |
| FCB | FCB |
| MED | MED |
| PROD_NONTEC | Prodotto non tecnologico |
| PROD_TEC | Prodotto tecnologico |

**Vendors → Frequenze di Valutazione**

Definiscono ogni quanti mesi ripetere la valutazione (es. 6, 12, 24 mesi).

---

### 14.7 Valutatori

**Vendors → Valutatori**

Elenco delle persone abilitate a effettuare le valutazioni dei fornitori:

| Campo | Descrizione |
|-------|-------------|
| **Cognome** | Cognome del valutatore |
| **Nome** | Nome del valutatore |
| **Email** | Email |
| **Ruolo** | Ruolo aziendale |
| **Dipartimento** | Dipartimento di appartenenza |
| **Attivo** | Se è attualmente abilitato a valutare |

---

> **Hai bisogno di aiuto?** Contatta l'amministratore di sistema.
