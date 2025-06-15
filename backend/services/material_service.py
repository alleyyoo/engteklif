# services/material_service.py (FIXED)
from typing import List, Dict, Any
from models.material import Material, MaterialCreate, MaterialUpdate
from bson import ObjectId

class MaterialService:
    
    @staticmethod
    def create_material(material_data: MaterialCreate) -> Dict[str, Any]:
        """Yeni malzeme oluştur"""
        try:
            # İsim kontrolü
            if Material.name_exists(material_data.name):
                return {
                    "success": False,
                    "message": "Bu malzeme adı zaten kullanılıyor"
                }
            
            material = Material.create_material(material_data.dict())
            return {
                "success": True,
                "message": "Malzeme başarıyla oluşturuldu",
                "material": material
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Malzeme oluşturulurken hata: {str(e)}"
            }
    
    @staticmethod
    def get_all_materials(page: int = 1, limit: int = 50, search: str = None, category: str = None) -> Dict[str, Any]:
        """Tüm malzemeleri getir"""
        try:
            skip = (page - 1) * limit
            
            if search:
                materials = Material.search_materials(search, category)
                # Manuel pagination for search results
                total = len(materials)
                materials = materials[skip:skip + limit]
            else:
                materials = Material.get_all_materials(limit, skip)
                total = Material.get_count()
            
            return {
                "success": True,
                "materials": materials,
                "pagination": {
                    "current_page": page,
                    "total_pages": (total + limit - 1) // limit,
                    "total_items": total,
                    "items_per_page": limit
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Malzemeler getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def get_material_by_id(material_id: str) -> Dict[str, Any]:
        """ID ile malzeme getir"""
        try:
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID'si"
                }
            
            material = Material.find_by_id(material_id)
            if not material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            return {
                "success": True,
                "material": material
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Malzeme getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def get_material_by_name(material_name: str) -> Dict[str, Any]:
        """İsim ile malzeme getir"""
        try:
            material = Material.find_by_name(material_name)
            if not material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            return {
                "success": True,
                "material": material
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Malzeme getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def update_material(material_id: str, update_data: MaterialUpdate) -> Dict[str, Any]:
        """Malzeme güncelle"""
        try:
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID'si"
                }
            
            # Mevcut malzeme kontrolü
            existing_material = Material.find_by_id(material_id)
            if not existing_material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            # İsim değişikliği kontrolü
            filtered_data = {k: v for k, v in update_data.dict().items() if v is not None}
            
            if 'name' in filtered_data and filtered_data['name'] != existing_material['name']:
                if Material.name_exists(filtered_data['name'], material_id):
                    return {
                        "success": False,
                        "message": "Bu malzeme adı zaten kullanılıyor"
                    }
            
            if not filtered_data:
                return {
                    "success": False,
                    "message": "Güncellenecek veri bulunamadı"
                }
            
            success = Material.update_material(material_id, filtered_data)
            if success:
                material = Material.find_by_id(material_id)
                return {
                    "success": True,
                    "message": "Malzeme başarıyla güncellendi",
                    "material": material
                }
            else:
                return {
                    "success": False,
                    "message": "Güncelleme başarısız"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Güncelleme sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def delete_material(material_id: str) -> Dict[str, Any]:
        """Malzeme sil"""
        try:
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID'si"
                }
            
            # Mevcut malzeme kontrolü
            existing_material = Material.find_by_id(material_id)
            if not existing_material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            success = Material.delete_material(material_id)
            if success:
                return {
                    "success": True,
                    "message": "Malzeme başarıyla silindi"
                }
            else:
                return {
                    "success": False,
                    "message": "Silme işlemi başarısız"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Silme sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def get_categories() -> Dict[str, Any]:
        """Malzeme kategorilerini getir"""
        try:
            categories = Material.get_categories()
            return {
                "success": True,
                "categories": sorted(categories) if categories else []
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Kategoriler getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def bulk_update_prices(price_updates: Dict[str, float]) -> Dict[str, Any]:
        """Toplu fiyat güncelleme"""
        try:
            if not price_updates:
                return {
                    "success": False,
                    "message": "Güncellenecek fiyat bilgisi yok"
                }
            
            # Fiyat değerlerini kontrol et
            for name, price in price_updates.items():
                if not isinstance(price, (int, float)) or price < 0:
                    return {
                        "success": False,
                        "message": f"Geçersiz fiyat değeri: {name} = {price}"
                    }
            
            updated_count = Material.bulk_update_prices(price_updates)
            return {
                "success": True,
                "message": f"{updated_count} malzeme fiyatı güncellendi",
                "updated_count": updated_count,
                "total_requested": len(price_updates)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Toplu fiyat güncelleme hatası: {str(e)}"
            }
    
    @staticmethod
    def get_materials_for_analysis() -> Dict[str, Any]:
        """Analiz için malzeme verilerini getir"""
        try:
            keyword_list, alias_map = Material.get_materials_for_matching()
            material_prices = Material.get_material_prices()
            
            # Aktif malzeme sayısı
            active_count = Material.get_count(active_only=True)
            
            return {
                "success": True,
                "keyword_list": keyword_list,
                "alias_map": alias_map,
                "material_prices": material_prices,
                "stats": {
                    "total_keywords": len(keyword_list),
                    "total_aliases": len(alias_map),
                    "materials_with_prices": len(material_prices),
                    "active_materials": active_count
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Analiz verileri getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def add_aliases_to_material(material_id: str, new_aliases: List[str]) -> Dict[str, Any]:
        """Malzemeye alias ekle"""
        try:
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID'si"
                }
            
            if not new_aliases:
                return {
                    "success": False,
                    "message": "Eklenecek alias bulunamadı"
                }
            
            material = Material.find_by_id(material_id)
            if not material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            current_aliases = material.get('aliases', [])
            
            # Yeni alias'ları temizle ve ekle
            cleaned_aliases = [alias.strip() for alias in new_aliases if alias.strip()]
            if not cleaned_aliases:
                return {
                    "success": False,
                    "message": "Geçerli alias bulunamadı"
                }
            
            # Mevcut alias'ları ve yenileri birleştir, tekrarları kaldır
            all_aliases = list(set(current_aliases + cleaned_aliases))
            
            success = Material.update_material(material_id, {"aliases": all_aliases})
            if success:
                updated_material = Material.find_by_id(material_id)
                added_count = len(all_aliases) - len(current_aliases)
                return {
                    "success": True,
                    "message": f"{added_count} alias başarıyla eklendi",
                    "material": updated_material,
                    "added_aliases": cleaned_aliases
                }
            else:
                return {
                    "success": False,
                    "message": "Alias ekleme başarısız"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Alias ekleme hatası: {str(e)}"
            }
    
    @staticmethod
    def remove_alias_from_material(material_id: str, alias_to_remove: str) -> Dict[str, Any]:
        """Malzemeden alias sil"""
        try:
            if not ObjectId.is_valid(material_id):
                return {
                    "success": False,
                    "message": "Geçersiz malzeme ID'si"
                }
            
            if not alias_to_remove.strip():
                return {
                    "success": False,
                    "message": "Silinecek alias belirtilmedi"
                }
            
            material = Material.find_by_id(material_id)
            if not material:
                return {
                    "success": False,
                    "message": "Malzeme bulunamadı"
                }
            
            current_aliases = material.get('aliases', [])
            if not current_aliases:
                return {
                    "success": False,
                    "message": "Malzemenin alias'ı bulunmuyor"
                }
            
            # Case-insensitive alias silme
            updated_aliases = [
                alias for alias in current_aliases 
                if alias.strip().lower() != alias_to_remove.strip().lower()
            ]
            
            if len(updated_aliases) == len(current_aliases):
                return {
                    "success": False,
                    "message": f"Alias '{alias_to_remove}' bulunamadı"
                }
            
            success = Material.update_material(material_id, {"aliases": updated_aliases})
            if success:
                updated_material = Material.find_by_id(material_id)
                return {
                    "success": True,
                    "message": f"Alias '{alias_to_remove}' başarıyla silindi",
                    "material": updated_material
                }
            else:
                return {
                    "success": False,
                    "message": "Alias silme başarısız"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Alias silme hatası: {str(e)}"
            }
    
    @staticmethod
    def get_material_statistics() -> Dict[str, Any]:
        """Malzeme istatistikleri"""
        try:
            total_materials = Material.get_count(active_only=False)
            active_materials = Material.get_count(active_only=True)
            inactive_materials = total_materials - active_materials
            
            categories = Material.get_categories()
            materials_with_prices = len(Material.get_material_prices())
            
            # Yoğunluğu olan malzemeler
            collection = Material.get_collection()
            materials_with_density = collection.count_documents({
                "is_active": True,
                "density": {"$ne": None, "$gt": 0}
            })
            
            return {
                "success": True,
                "statistics": {
                    "total_materials": total_materials,
                    "active_materials": active_materials,
                    "inactive_materials": inactive_materials,
                    "materials_with_prices": materials_with_prices,
                    "materials_with_density": materials_with_density,
                    "total_categories": len(categories),
                    "categories": categories
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"İstatistikler getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def validate_material_data(material_data: dict) -> Dict[str, Any]:
        """Malzeme verilerini doğrula"""
        try:
            errors = []
            
            # İsim kontrolü
            if not material_data.get('name', '').strip():
                errors.append("Malzeme adı gerekli")
            
            # Yoğunluk kontrolü
            density = material_data.get('density')
            if density is not None:
                if not isinstance(density, (int, float)) or density <= 0:
                    errors.append("Yoğunluk pozitif bir sayı olmalı")
            
            # Fiyat kontrolü
            price = material_data.get('price_per_kg')
            if price is not None:
                if not isinstance(price, (int, float)) or price < 0:
                    errors.append("Fiyat sıfır veya pozitif bir sayı olmalı")
            
            # Alias kontrolü
            aliases = material_data.get('aliases', [])
            if aliases and not isinstance(aliases, list):
                errors.append("Alias'lar liste formatında olmalı")
            
            return {
                "success": len(errors) == 0,
                "errors": errors,
                "message": "Doğrulama başarılı" if len(errors) == 0 else "Doğrulama hatası"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Doğrulama sırasında hata: {str(e)}"
            }