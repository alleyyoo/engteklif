# migrate_materials_fixed.py - PyMongo 4.x Compatible
import sqlite3
import pymongo
from datetime import datetime
import sys
import os

# MongoDB bağlantı ayarları
MONGO_URL = "mongodb://mongodb:27017/engteklif"
DATABASE_NAME = "engteklif"
SQLITE_DB_PATH = "materials.db"

def test_mongodb_connection():
    """MongoDB bağlantısını test et"""
    try:
        client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        return client, client[DATABASE_NAME]
    except Exception as e:
        print(f"❌ MongoDB bağlantı hatası: {e}")
        return None, None

def test_sqlite_connection():
    """SQLite bağlantısını test et"""
    try:
        if not os.path.exists(SQLITE_DB_PATH):
            print(f"❌ SQLite dosyası bulunamadı: {SQLITE_DB_PATH}")
            return None
        
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ SQLite bağlantı hatası: {e}")
        return None

def migrate_materials_table(sqlite_conn, mongo_db):
    """Materials tablosunu migrate et"""
    print("\n📦 Materials tablosu migrate ediliyor...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM materials")
    materials = cursor.fetchall()
    
    if not materials:
        print("⚠️  Materials tablosu boş")
        return 0
    
    materials_collection = mongo_db.materials
    migrated_count = 0
    
    for material in materials:
        try:
            # Aliases'ları array'e çevir
            aliases = []
            if material["aliases"]:
                aliases = [alias.strip() for alias in material["aliases"].split(",") if alias.strip()]
            
            material_doc = {
                "name": material["name"],
                "aliases": aliases,
                "density": float(material["density"]) if material["density"] else None,
                "price_per_kg": None,
                "description": None,
                "category": None,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "sqlite_id": material["id"]
            }
            
            # Duplicate kontrol
            existing = materials_collection.find_one({"name": material_doc["name"]})
            
            if existing:
                print(f"⚠️  Güncelleniyor: {material_doc['name']}")
                materials_collection.update_one(
                    {"name": material_doc["name"]},
                    {"$set": {
                        "aliases": material_doc["aliases"],
                        "density": material_doc["density"],
                        "updated_at": datetime.utcnow(),
                        "sqlite_id": material_doc["sqlite_id"]
                    }}
                )
            else:
                materials_collection.insert_one(material_doc)
                print(f"✅ Eklendi: {material_doc['name']}")
            
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Hata - {material['name']}: {e}")
    
    print(f"📊 Materials: {migrated_count} kayıt işlendi")
    return migrated_count

def migrate_prices_table(sqlite_conn, mongo_db):
    """Material prices migrate et"""
    print("\n💰 Material prices migrate ediliyor...")
    
    cursor = sqlite_conn.cursor()
    
    # Table exists check
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='material_prices';")
    if not cursor.fetchone():
        print("⚠️  material_prices tablosu yok")
        return 0
    
    cursor.execute("SELECT * FROM material_prices")
    prices = cursor.fetchall()
    
    if not prices:
        print("⚠️  Material prices boş")
        return 0
    
    materials_collection = mongo_db.materials
    updated_count = 0
    
    for price in prices:
        try:
            material_name = price["name"]
            price_value = float(price["ucret"]) if price["ucret"] else None
            
            if price_value is not None:
                result = materials_collection.update_one(
                    {"name": material_name},
                    {"$set": {
                        "price_per_kg": price_value,
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                if result.modified_count > 0:
                    print(f"✅ Fiyat: {material_name} = ${price_value}")
                    updated_count += 1
                else:
                    print(f"⚠️  Malzeme yok: {material_name}")
            
        except Exception as e:
            print(f"❌ Fiyat hatası - {price['name']}: {e}")
    
    print(f"📊 Prices: {updated_count} güncelleme")
    return updated_count

def migrate_measurements_table(sqlite_conn, mongo_db):
    """Teknik ölçümler migrate et"""
    print("\n📏 Geometric measurements migrate ediliyor...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teknik_olcumler';")
    if not cursor.fetchone():
        print("⚠️  teknik_olcumler tablosu yok")
        return 0
    
    cursor.execute("SELECT * FROM teknik_olcumler")
    measurements = cursor.fetchall()
    
    if not measurements:
        print("⚠️  Teknik ölçümler boş")
        return 0
    
    measurements_collection = mongo_db.geometric_measurements
    migrated_count = 0
    
    for measurement in measurements:
        try:
            measurement_doc = {
                "type": measurement["tur"],
                "nominal_value": str(measurement["nominal_deger"]),
                "upper_deviation": float(measurement["ust_sapma"]) if measurement["ust_sapma"] else None,
                "lower_deviation": float(measurement["alt_sapma"]) if measurement["alt_sapma"] else None,
                "multiplier": float(measurement["carpan"]) if measurement["carpan"] else 1.0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "sqlite_id": measurement["id"]
            }
            
            existing = measurements_collection.find_one({
                "type": measurement_doc["type"],
                "nominal_value": measurement_doc["nominal_value"]
            })
            
            if not existing:
                measurements_collection.insert_one(measurement_doc)
                print(f"✅ Ölçüm: {measurement_doc['type']} - {measurement_doc['nominal_value']}")
                migrated_count += 1
            else:
                print(f"⚠️  Mevcut: {measurement_doc['type']} - {measurement_doc['nominal_value']}")
            
        except Exception as e:
            print(f"❌ Ölçüm hatası - {measurement['tur']}: {e}")
    
    print(f"📊 Measurements: {migrated_count} eklendi")
    return migrated_count

def create_mongodb_indexes(mongo_db):
    """MongoDB indexleri oluştur"""
    print("\n🔍 MongoDB indexleri oluşturuluyor...")
    
    try:
        # Materials indexes
        mongo_db.materials.create_index("name", unique=True)
        mongo_db.materials.create_index("aliases")
        mongo_db.materials.create_index("is_active")
        print("✅ Materials indexleri OK")
        
        # Measurements indexes
        mongo_db.geometric_measurements.create_index([("type", 1), ("nominal_value", 1)])
        mongo_db.geometric_measurements.create_index("type")
        print("✅ Measurements indexleri OK")
        
    except Exception as e:
        print(f"⚠️  Index hatası: {e}")

def verify_data(mongo_db):
    """Verileri doğrula"""
    print("\n🔍 Veriler doğrulanıyor...")
    
    try:
        materials_count = mongo_db.materials.count_documents({})
        materials_with_prices = mongo_db.materials.count_documents({"price_per_kg": {"$ne": None}})
        measurements_count = mongo_db.geometric_measurements.count_documents({})
        
        print(f"📊 Sonuçlar:")
        print(f"   Materials: {materials_count}")
        print(f"   With prices: {materials_with_prices}")
        print(f"   Measurements: {measurements_count}")
        
        # Örnek veri
        sample = mongo_db.materials.find_one()
        if sample:
            print(f"📋 Örnek: {sample.get('name')} (density: {sample.get('density')})")
        
    except Exception as e:
        print(f"❌ Doğrulama hatası: {e}")

def main():
    """Ana fonksiyon"""
    print("🚀 SQLite → MongoDB Migration (PyMongo 4.x)")
    print("=" * 50)
    
    # Bağlantı testleri
    print("🔍 Bağlantılar test ediliyor...")
    
    client, mongo_db = test_mongodb_connection()
    if client is None:
        print("❌ MongoDB bağlantısı başarısız!")
        sys.exit(1)
    print("✅ MongoDB bağlantısı OK")
    
    sqlite_conn = test_sqlite_connection()
    if sqlite_conn is None:
        print("❌ SQLite bağlantısı başarısız!")
        sys.exit(1)
    print("✅ SQLite bağlantısı OK")
    
    try:
        # Migration'ları çalıştır
        total = 0
        total += migrate_materials_table(sqlite_conn, mongo_db)
        total += migrate_prices_table(sqlite_conn, mongo_db)
        total += migrate_measurements_table(sqlite_conn, mongo_db)
        
        # Index ve doğrulama
        create_mongodb_indexes(mongo_db)
        verify_data(mongo_db)
        
        print(f"\n🎉 Migration başarılı!")
        print(f"📊 Toplam işlenen: {total} kayıt")
        
    except Exception as e:
        print(f"❌ Migration hatası: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        if sqlite_conn:
            sqlite_conn.close()
        if client:
            client.close()
        print("✅ Bağlantılar kapatıldı")

if __name__ == "__main__":
    main()