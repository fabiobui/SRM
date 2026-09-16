#!/bin/bash
# Script per testare la configurazione di produzione in locale

echo "🧪 Test Configurazione Produzione"
echo "================================="

# Backup dell'env attuale
cp .env .env.backup

# Modifica temporaneamente per produzione
sed -i 's/USE_FORNITORI_PREFIX=False/USE_FORNITORI_PREFIX=True/' .env
sed -i 's/DEBUG=True/DEBUG=False/' .env

echo "✅ Configurazione cambiata a produzione"

# Test URL generation
echo "📋 Test generazione URL..."
python manage.py test_url_config

echo ""
echo "🔄 Ripristino configurazione sviluppo..."

# Ripristina configurazione sviluppo
cp .env.backup .env
rm .env.backup

echo "✅ Configurazione ripristinata"
echo ""
echo "📝 Per produzione ricorda di:"
echo "   1. Impostare USE_FORNITORI_PREFIX=True"
echo "   2. Impostare DEBUG=False"
echo "   3. Configurare il web server per /fornitori"
echo "   4. Configurare i file statici"
