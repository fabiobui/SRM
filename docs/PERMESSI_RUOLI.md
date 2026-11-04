# Ruoli, gruppi e permessi

Questo documento descrive come sono organizzati accessi e permessi di SRM e perché. I test che fissano
questi comportamenti sono in [tests/test_permessi_ruoli.py](../tests/test_permessi_ruoli.py) e in
[vendor_management_system/users/tests/test_role_groups.py](../vendor_management_system/users/tests/test_role_groups.py).

## Un solo concetto: il ruolo

Il campo `User.role` è la fonte di verità. Gli altri elementi si ricavano da lui a ogni salvataggio:

| Ruolo (`role`) | Gruppo Django | Staff (`/admin/`) | Area di atterraggio |
|---|---|---|---|
| `admin` — Admin | `Admin` | sì | `/admin/` |
| `bo_user` — BO User | `BO User` | no | `/vendors/dashboard/` e `/portale/backoffice/dashboard/` |
| `buyer` — Buyer | `Buyer` | no | `/vendors/dashboard/` (solo quella) |
| `vendor` — Fornitore | `Vendors` | no | Portale fornitori `/portale/` |

- Il **gruppo** viene riallineato in `User.save()` (`sync_role_group`): se lo assegni a mano, al salvataggio
  torna quello del ruolo.
- Lo **staff** è `True` solo per gli Admin e per i superuser (`User.save()`).
- Il login **LDAP** assegna il ruolo dai gruppi AD solo alla **creazione** dell'utente; agli accessi
  successivi il ruolo non viene riscritto (altrimenti un Admin tornava BO User e perdeva `/admin/`).
- Nel form utente gruppo e staff sono di sola lettura; il superuser si imposta solo da un altro superuser.

## Cosa può fare ciascun ruolo

| Richiesta | Admin | BO User | Buyer | Fornitore | Anonimo |
|---|:--:|:--:|:--:|:--:|:--:|
| Pannello `/admin/` (modelli fornitori, utenti, ecc.) | sì | no | no | no | no |
| Creare l'utenza portale di un fornitore (accesso portale) | sì | no | no | no | no |
| Gestire gruppi e permessi Django | no | no | no | no | no |
| Impostare o togliere il superuser | no | no | no | no | no |
| Dashboard fornitori `/vendors/dashboard/` e export Excel | sì | sì | sì | no | no |
| Scheda fornitore in sola lettura e "Aggiungi fornitore prospetto" (dalla dashboard) | sì | sì | sì | 403 | 401 |
| API dashboard `/vendors/dashboard-vendors/` e `/vendors/dashboard-stats/` | sì | sì | 403 | 403 | 401 |
| Dashboard back office `/portale/backoffice/dashboard/` | sì | sì | no | no | no |
| API REST `/vendors/`, `/users/`, `/purchase-orders/` (token) | sì | sì | 403 | 403 | 401 |
| Portale fornitori `/portale/` (solo i propri dati) | no | no | no | sì | no |

Il pannello `/admin/` mostra solo le sezioni per cui l'utente ha permessi: per il BO User non compare nulla,
perché non è staff.

## Permessi Django nei gruppi

I permessi stanno nei gruppi, non nei singoli utenti: si gestiscono in un solo punto, in
[vendor_management_system/users/roles.py](../vendor_management_system/users/roles.py).

- **Admin**: tutti i permessi (add, change, delete, view) delle app `ADMIN_APP_LABELS`: users, vendors,
  vendors_analysis, purchase_orders, historical_performances, services, competences, portal, documents.
  Restano fuori `auth` (gruppi e permessi), `admin`, `contenttypes`, `sessions`, `authtoken` e
  `django_celery_beat`: li gestisce solo un superuser.
- **BO User**, **Buyer** e **Vendors**: nessun permesso Django. Il loro accesso passa dalle viste, che controllano il ruolo.

I gruppi vengono creati e allineati a ogni `migrate` (segnale `post_migrate` in
[vendor_management_system/users/apps.py](../vendor_management_system/users/apps.py)). Un
`manage.py migrate` dopo un deploy riporta quindi i permessi allo stato del codice. Un permesso aggiunto a mano
al gruppo `Admin` viene tolto al prossimo migrate: per cambiarlo, modifica `roles.py`.

## Il superuser

Il superuser fa tutto ciò che fa un Admin, più quanto segue, che non serve nell'uso quotidiano:

- gestire gruppi e permessi Django (`auth`);
- impostare o togliere `is_superuser` su un utente;
- modificare o eliminare un altro superuser;
- gestire le app escluse da `ADMIN_APP_LABELS` (token API, job pianificati di `django_celery_beat`).

Il superuser si crea da riga di comando (`manage.py createsuperuser`) e si tiene per le emergenze.

## Controlli di accesso sulle viste

- Viste funzionali: `backoffice_required` (redirect) e `backoffice_api_required` (JSON 401/403); per le funzioni
  della dashboard aperte anche al Buyer `dashboard_required` e `dashboard_api_required`, in
  [vendor_management_system/core/permissions.py](../vendor_management_system/core/permissions.py).
- Viste basate su classi: `BackOfficeRequiredMixin`, `VendorRequiredMixin`, `AdminRequiredMixin`.
- API REST DRF: `IsBackOfficeUser`, usata da tutte le viewset di `vendors`, `users` e `purchase_orders`.

Chi aggiunge una vista che espone dati fornitori deve usare uno di questi controlli, non il solo
`@login_required`.

Il **Buyer** vede solo la dashboard: `is_backoffice` (usata da API REST e dashboard back office) non lo include,
`is_dashboard_user` sì. Il Buyer può essere scelto come utente di gestione del fornitore, e lo diventa
automaticamente per i fornitori prospetto che crea.

## Migrazione dei dati

La migrazione `users.0005_gruppi_ruoli_staff` rinomina i gruppi `Administrators` → `Admin` e
`BackOffice Users` → `BO User`, rifà le appartenenze a partire dal ruolo e ricalcola lo staff. Effetto
voluto: gli utenti BO che avevano lo staff perdono l'accesso a `/admin/`, dove vedevano solo i link alle
dashboard.
