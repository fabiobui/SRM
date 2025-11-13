#!/bin/bash

# Script per configurare l'autenticazione LDAP nel sistema VMS
echo "🚀 Configurazione LDAP per VMS"
echo "================================"

# Controlla se siamo nella directory corretta
if [ ! -f "manage.py" ]; then
    echo "❌ Errore: Esegui questo script dalla directory root del progetto Django"
    exit 1
fi

# Installa le dipendenze LDAP
echo "📦 Installazione dipendenze LDAP..."

# Per sistemi Ubuntu/Debian
if command -v apt-get &> /dev/null; then
    echo "🐧 Sistema Ubuntu/Debian rilevato"
    sudo apt-get update
    sudo apt-get install -y libldap2-dev libsasl2-dev libssl-dev
fi

# Per sistemi RedHat/CentOS/Fedora
if command -v yum &> /dev/null; then
    echo "🎩 Sistema RedHat/CentOS rilevato"
    sudo yum install -y openldap-devel libgsasl-devel openssl-devel
fi

if command -v dnf &> /dev/null; then
    echo "🎩 Sistema Fedora rilevato"
    sudo dnf install -y openldap-devel libgsasl-devel openssl-devel
fi

# Installa le dipendenze Python
echo "🐍 Installazione dipendenze Python..."
pip install django-auth-ldap python-ldap ldap3

echo "✅ Dipendenze installate con successo!"

# Crea il file di configurazione LDAP se non esiste
if [ ! -f ".env.ldap" ]; then
    echo "📝 Creazione file di configurazione LDAP..."
    cp .env.ldap.example .env.ldap
    echo "📄 File .env.ldap creato. Modifica le configurazioni secondo il tuo server LDAP."
else
    echo "📄 File .env.ldap già esistente."
fi

echo ""
echo "🎉 Configurazione LDAP completata!"
echo ""
echo "📋 PROSSIMI PASSI:"
echo "1. Modifica il file .env.ldap con le configurazioni del tuo server LDAP"
echo "2. Aggiungi le configurazioni LDAP al tuo file .env principale:"
echo "   cat .env.ldap >> .env"
echo "3. Esegui le migrazioni: python manage.py migrate"
echo "4. Testa la connessione: python manage.py test_ldap"
echo "5. Testa l'autenticazione: python manage.py test_ldap --test-user email@example.com --password password"
echo ""
echo "📚 Per maggiori informazioni sulla configurazione LDAP, consulta la documentazione."