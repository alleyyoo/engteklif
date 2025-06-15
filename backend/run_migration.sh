#!/bin/bash
# run_migration.sh - Migration çalıştırma scripti

echo "🚀 EngTeklif - SQLite to MongoDB Migration"
echo "=========================================="

# Gerekli dosyaların varlığını kontrol et
if [ ! -f "materials.db" ]; then
    echo "❌ materials.db dosyası bulunamadı!"
    echo "   Lütfen materials.db dosyasını bu klasöre kopyalayın."
    exit 1
fi

if [ ! -f "migrate_materials.py" ]; then
    echo "❌ migrate_materials.py dosyası bulunamadı!"
    exit 1
fi

# Virtual environment kontrolü
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment aktif değil!"
    echo "   Aktifleştirmek için: source engteklif_env/bin/activate"
    read -p "Devam etmek istiyor musunuz? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# MongoDB'nin çalışıp çalışmadığını kontrol et
echo "🔍 MongoDB bağlantısı kontrol ediliyor..."
python3 -c "
import pymongo
try:
    client = pymongo.MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
    client.server_info()
    print('✅ MongoDB çalışıyor')
except Exception as e:
    print('❌ MongoDB bağlantısı başarısız:', e)
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ MongoDB'ye bağlanılamıyor!"
    echo "   MongoDB'yi başlatın: mongod --dbpath /your/db/path"
    exit 1
fi

# SQLite tabloları kontrol et
echo "🔍 SQLite tabloları kontrol ediliyor..."
python3 -c "
import sqlite3
conn = sqlite3.connect('materials.db')
cursor = conn.cursor()
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table';\")
tables = [row[0] for row in cursor.fetchall()]
print(f'📋 Bulunan tablolar: {tables}')
conn.close()
"

# Migration'ı çalıştır
echo ""
echo "🔄 Migration başlatılıyor..."
echo "Bu işlem birkaç dakika sürebilir..."
echo ""

python3 migrate_materials.py

# Sonucu kontrol et
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Migration başarıyla tamamlandı!"
    echo ""
    echo "📊 MongoDB'deki verileri kontrol etmek için:"
    echo "   mongo engteklif --eval 'db.materials.count()'"
    echo "   mongo engteklif --eval 'db.geometric_measurements.count()'"
    echo ""
    echo "🚀 Artık Flask uygulamanızı başlatabilirsiniz:"
    echo "   python app.py"
else
    echo ""
    echo "❌ Migration sırasında hata oluştu!"
    echo "   Lütfen hata mesajlarını kontrol edin."
    exit 1
fi