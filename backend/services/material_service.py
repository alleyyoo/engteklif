# services/material_service.py - FIXED VERSION
from typing import Dict, List, Any, Optional
from models.material import Material, MaterialCreate, MaterialUpdate
from bson import ObjectId
import traceback

class MaterialService:
    
    @classmethod
    def get_all_materials(cls, page: int = 1, limit: int = 50, search: str = "", category: str = "") -> Dict[str, Any]:
        """Tüm malzemeleri getir - is_active olmadan"""
        try:
            print(f"[MaterialService] 🔍 Getting materials: page={page}, limit={limit}, search='{search}', category='{category}'")
            
            from models.material import Material
            collection = Material.get_collection()
            
            # ✅ is_active kontrolü kaldırıldı
            query = {}  # Boş query - tüm dokümanlar
            
            # Search ekle
            if search and search.strip():
                search_pattern = {"$regex": search.strip(), "$options": "i"}
                query["$or"] = [
                    {"name": search_pattern},
                    {"aliases": search_pattern},
                    {"description": search_pattern}
                ]
            
            # Category ekle
            if category and category.strip():
                query["category"] = category.strip()
            
            print(f"[MaterialService] 🔍 MongoDB Query: {query}")
            
            # Pagination
            skip = (page - 1) * limit
            
            # Execute query
            cursor = collection.find(query).sort("name", 1).skip(skip).limit(limit)
            materials = list(cursor)
            
            print(f"[MaterialService] 📊 Raw MongoDB documents: {len(materials)}")
            
            # ID conversion
            for material in materials:
                if '_id' in material:
                    material['id'] = str(material['_id'])
                    del material['_id']
                    print(f"[MaterialService] 🔄 Processed: {material.get('name', 'no_name')}")
            
            # Total count (is_active olmadan)
            total_count = collection.count_documents(query)
            
            print(f"[MaterialService] ✅ Found {len(materials)} materials (total: {total_count})")
            
            return {
                "success": True,
                "materials": materials,
                "pagination": {
                    "current_page": page,
                    "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 1,
                    "total_items": total_count,
                    "items_per_page": limit
                },
                "filters": {
                    "search": search,
                    "category": category
                }
            }
            
        except Exception as e:
            error_msg = f"Malzemeler getirilemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            import traceback
            print(f"[MaterialService] 📋 Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": error_msg,
                "materials": []
            }
    
    @classmethod
    def get_material_by_id(cls, material_id: str) -> Dict[str, Any]:
        """ID ile malzeme getir"""
        try:
            print(f"[MaterialService] 🔍 Getting material by ID: {material_id}")
            
            # ObjectId formatını kontrol et
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID formatı"
                }
            
            material = Material.find_by_id(material_id)
            
            if material:
                print(f"[MaterialService] ✅ Material found: {material['name']}")
                return {
                    "success": True,
                    "material": material
                }
            else:
                print(f"[MaterialService] ❌ Material not found: {material_id}")
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
                
        except Exception as e:
            error_msg = f"Malzeme getirilemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    def get_material_by_name(cls, name: str) -> Dict[str, Any]:
        """İsim ile malzeme getir"""
        try:
            print(f"[MaterialService] 🔍 Getting material by name: {name}")
            
            material = Material.find_by_name(name)
            
            if material:
                print(f"[MaterialService] ✅ Material found: {material['name']}")
                return {
                    "success": True,
                    "material": material
                }
            else:
                print(f"[MaterialService] ❌ Material not found: {name}")
                return {
                    "success": False,
                    "message": f"'{name}' malzemesi bulunamadı"
                }
                
        except Exception as e:
            error_msg = f"Malzeme getirilemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    def create_material(cls, material_data: dict) -> Dict[str, Any]:
        """Yeni malzeme oluştur"""
        try:
            print(f"[MaterialService] 🆕 Creating material: {material_data}")
            
            # Pydantic validation
            material_create = MaterialCreate(**material_data)
            
            # İsim kontrolü
            if Material.name_exists(material_create.name):
                return {
                    "success": False,
                    "message": f"'{material_create.name}' isimli malzeme zaten mevcut"
                }
            
            # Malzeme oluştur
            material = Material.create_material(material_create.dict())
            
            if material:
                print(f"[MaterialService] ✅ Material created: {material['name']} (ID: {material['id']})")
                return {
                    "success": True,
                    "message": "Malzeme başarıyla oluşturuldu",
                    "material": material
                }
            else:
                return {
                    "success": False,
                    "message": "Malzeme oluşturulamadı"
                }
                
        except Exception as e:
            error_msg = f"Malzeme oluşturulamadı: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    def update_material(cls, material_id: str, update_data: dict) -> Dict[str, Any]:
        """Malzeme güncelle"""
        try:
            print(f"[MaterialService] 🔧 Updating material {material_id}: {update_data}")
            
            # ObjectId formatını kontrol et
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID formatı"
                }
            
            # Mevcut malzemeyi kontrol et
            existing_material = Material.find_by_id(material_id)
            if not existing_material:
                return {
                    "success": False,
                    "message": "Güncellenecek malzeme bulunamadı"
                }
            
            # İsim değişikliği kontrolü
            if 'name' in update_data and update_data['name'] != existing_material['name']:
                if Material.name_exists(update_data['name'], exclude_id=material_id):
                    return {
                        "success": False,
                        "message": f"'{update_data['name']}' isimli malzeme zaten mevcut"
                    }
            
            # Pydantic validation (sadece gönderilen alanlar için)
            try:
                MaterialUpdate(**update_data)
            except Exception as validation_error:
                return {
                    "success": False,
                    "message": f"Veri doğrulama hatası: {str(validation_error)}"
                }
            
            # Güncelle
            success = Material.update_material(material_id, update_data)
            
            if success:
                # Güncellenmiş malzemeyi getir
                updated_material = Material.find_by_id(material_id)
                print(f"[MaterialService] ✅ Material updated: {updated_material['name']}")
                return {
                    "success": True,
                    "message": "Malzeme başarıyla güncellendi",
                    "material": updated_material
                }
            else:
                return {
                    "success": False,
                    "message": "Malzeme güncellenemedi"
                }
                
        except Exception as e:
            error_msg = f"Malzeme güncellenemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    def delete_material(cls, material_id: str) -> Dict[str, Any]:
        """Malzeme sil (soft delete)"""
        try:
            print(f"[MaterialService] 🗑️ Deleting material: {material_id}")
            
            # ObjectId formatını kontrol et
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID formatı"
                }
            
            # Mevcut malzemeyi kontrol et
            existing_material = Material.find_by_id(material_id)
            if not existing_material:
                return {
                    "success": False,
                    "message": "Silinecek malzeme bulunamadı"
                }
            
            # Soft delete (is_active = False)
            success = Material.delete_material(material_id)
            
            if success:
                print(f"[MaterialService] ✅ Material deleted: {existing_material['name']}")
                return {
                    "success": True,
                    "message": f"'{existing_material['name']}' malzemesi başarıyla silindi"
                }
            else:
                return {
                    "success": False,
                    "message": "Malzeme silinemedi"
                }
                
        except Exception as e:
            error_msg = f"Malzeme silinemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    def get_categories(cls) -> Dict[str, Any]:
        """Malzeme kategorilerini getir"""
        try:
            print("[MaterialService] 📂 Getting categories")
            
            categories = Material.get_categories()
            
            print(f"[MaterialService] ✅ Found {len(categories)} categories")
            return {
                "success": True,
                "categories": categories
            }
            
        except Exception as e:
            error_msg = f"Kategoriler getirilemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "categories": []
            }
    
    @classmethod
    def bulk_update_prices(cls, price_updates: Dict[str, float]) -> Dict[str, Any]:
        """Toplu fiyat güncelleme"""
        try:
            print(f"[MaterialService] 💰 Bulk updating prices: {len(price_updates)} items")
            
            updated_count = Material.bulk_update_prices(price_updates)
            
            print(f"[MaterialService] ✅ Bulk update completed: {updated_count} items updated")
            return {
                "success": True,
                "message": f"{updated_count} malzeme fiyatı güncellendi",
                "updated_count": updated_count
            }
            
        except Exception as e:
            error_msg = f"Toplu fiyat güncellemesi başarısız: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "updated_count": 0
            }
    
    @classmethod
    def add_aliases_to_material(cls, material_id: str, new_aliases: List[str]) -> Dict[str, Any]:
        """Malzemeye alias ekle"""
        try:
            print(f"[MaterialService] 🏷️ Adding aliases to {material_id}: {new_aliases}")
            
            # ObjectId formatını kontrol et
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID formatı"
                }
            
            # Mevcut malzemeyi getir
            material = Material.find_by_id(material_id)
            if not material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            # Mevcut aliasları al
            current_aliases = material.get('aliases', [])
            
            # Yeni aliasları ekle (duplikasyon kontrolü)
            all_aliases = list(set(current_aliases + new_aliases))
            
            # Güncelle
            success = Material.update_material(material_id, {"aliases": all_aliases})
            
            if success:
                # Güncellenmiş malzemeyi getir
                updated_material = Material.find_by_id(material_id)
                print(f"[MaterialService] ✅ Aliases added to {material['name']}")
                return {
                    "success": True,
                    "message": "Aliaslar başarıyla eklendi",
                    "material": updated_material
                }
            else:
                return {
                    "success": False,
                    "message": "Aliaslar eklenemedi"
                }
                
        except Exception as e:
            error_msg = f"Alias eklenemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    def remove_alias_from_material(cls, material_id: str, alias_to_remove: str) -> Dict[str, Any]:
        """Malzemeden alias sil"""
        try:
            print(f"[MaterialService] 🗑️ Removing alias '{alias_to_remove}' from {material_id}")
            
            # ObjectId formatını kontrol et
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID formatı"
                }
            
            # Mevcut malzemeyi getir
            material = Material.find_by_id(material_id)
            if not material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            # Mevcut aliasları al
            current_aliases = material.get('aliases', [])
            
            # Alias'ı çıkar
            updated_aliases = [alias for alias in current_aliases if alias != alias_to_remove]
            
            # Güncelle
            success = Material.update_material(material_id, {"aliases": updated_aliases})
            
            if success:
                # Güncellenmiş malzemeyi getir
                updated_material = Material.find_by_id(material_id)
                print(f"[MaterialService] ✅ Alias '{alias_to_remove}' removed from {material['name']}")
                return {
                    "success": True,
                    "message": "Alias başarıyla silindi",
                    "material": updated_material
                }
            else:
                return {
                    "success": False,
                    "message": "Alias silinemedi"
                }
                
        except Exception as e:
            error_msg = f"Alias silinemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    @classmethod
    def get_materials_for_analysis(cls) -> Dict[str, Any]:
        """Analiz için malzeme verilerini getir"""
        try:
            print("[MaterialService] 📊 Getting materials for analysis")
            
            # Sadece aktif malzemeleri al
            materials = Material.get_all_materials(limit=10000, active_only=True)
            
            # Analiz için gerekli alanları filtrele
            analysis_materials = []
            for material in materials:
                analysis_materials.append({
                    "id": material['id'],
                    "name": material['name'],
                    "aliases": material.get('aliases', []),
                    "density": material.get('density'),
                    "price_per_kg": material.get('price_per_kg'),
                    "category": material.get('category')
                })
            
            print(f"[MaterialService] ✅ Analysis materials: {len(analysis_materials)} items")
            return {
                "success": True,
                "materials": analysis_materials,
                "total_count": len(analysis_materials)
            }
            
        except Exception as e:
            error_msg = f"Analiz malzemeleri getirilemedi: {str(e)}"
            print(f"[MaterialService] ❌ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "materials": []
            }