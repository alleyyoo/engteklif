# controllers/material_controller.py - FIXED VERSION
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from bson import ObjectId
from models.user import User, UserRole
from services.material_service import MaterialService
import traceback
from datetime import datetime

material_bp = Blueprint('materials', __name__, url_prefix='/api/materials')

def get_current_user():
    """Mevcut kullanıcıyı getir"""
    current_user_id = get_jwt_identity()
    return User.find_by_id(current_user_id)

@material_bp.route('', methods=['GET'])
@jwt_required()
def get_materials():
    """Tüm malzemeleri getir"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        search = request.args.get('search', '', type=str)
        category = request.args.get('category', '', type=str)
        
        print(f"[MATERIALS] 📄 Request: page={page}, limit={limit}, search='{search}', category='{category}'")
        
        result = MaterialService.get_all_materials(page, limit, search, category)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Found {len(result['materials'])} materials")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Error: {result['message']}")
            return jsonify(result), 400
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        print(f"[MATERIALS] 📋 Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('', methods=['POST'])
@jwt_required()
def create_material():
    """Yeni malzeme oluştur"""
    try:
        current_user = get_current_user()
        
        # Sadece admin oluşturabilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        print(f"[MATERIALS] 🆕 Creating material: {data}")
        
        result = MaterialService.create_material(data)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Material created: {result['material']['name']}")
            return jsonify(result), 201
        else:
            print(f"[MATERIALS] ❌ Creation failed: {result['message']}")
            return jsonify(result), 400
            
    except ValidationError as e:
        error_details = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        print(f"[MATERIALS] 🔍 Validation error: {error_details}")
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": error_details
        }), 400
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/<material_id>', methods=['GET'])
@jwt_required()
def get_material(material_id):
    """Belirli bir malzemeyi getir"""
    try:
        print(f"[MATERIALS] 🔍 Getting material: {material_id}")
        
        result = MaterialService.get_material_by_id(material_id)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Material found: {result['material']['name']}")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Material not found: {material_id}")
            return jsonify(result), 404
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/<material_id>', methods=['PUT'])
@jwt_required()
def update_material(material_id):
    """Malzeme güncelle"""
    try:
        current_user = get_current_user()
        
        # Sadece admin güncelleyebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Güncellenecek veri gönderilmedi"
            }), 400
        
        print(f"[MATERIALS] 🔧 Updating material {material_id}: {data}")
        
        result = MaterialService.update_material(material_id, data)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Material updated: {result['material']['name']}")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Update failed: {result['message']}")
            return jsonify(result), 400
            
    except ValidationError as e:
        error_details = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        print(f"[MATERIALS] 🔍 Validation error: {error_details}")
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": error_details
        }), 400
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/<material_id>', methods=['DELETE'])
@jwt_required()
def delete_material(material_id):
    """Malzeme sil"""
    try:
        current_user = get_current_user()
        
        # Sadece admin silebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        print(f"[MATERIALS] 🗑️ Deleting material: {material_id}")
        
        result = MaterialService.delete_material(material_id)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Material deleted: {material_id}")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Delete failed: {result['message']}")
            return jsonify(result), 400
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Malzeme kategorilerini getir"""
    try:
        print("[MATERIALS] 📂 Getting categories")
        
        result = MaterialService.get_categories()
        
        if result['success']:
            print(f"[MATERIALS] ✅ Found {len(result['categories'])} categories")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Categories error: {result['message']}")
            return jsonify(result), 400
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/bulk-update-prices', methods=['POST'])
@jwt_required()
def bulk_update_prices():
    """Toplu fiyat güncelleme"""
    try:
        current_user = get_current_user()
        
        # Sadece admin güncelleyebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        data = request.get_json()
        if not data or 'price_updates' not in data:
            return jsonify({
                "success": False,
                "message": "Fiyat güncelleme verisi gönderilmedi"
            }), 400
        
        price_updates = data['price_updates']
        if not isinstance(price_updates, dict):
            return jsonify({
                "success": False,
                "message": "Geçersiz fiyat güncellleme formatı"
            }), 400
        
        print(f"[MATERIALS] 💰 Bulk updating prices: {len(price_updates)} items")
        
        result = MaterialService.bulk_update_prices(price_updates)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Bulk update completed: {result.get('updated_count', 0)} items")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Bulk update failed: {result['message']}")
            return jsonify(result), 400
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/<material_id>/aliases', methods=['POST'])
@jwt_required()
def add_aliases(material_id):
    """Malzemeye alias ekle"""
    try:
        current_user = get_current_user()
        
        # Sadece admin ekleyebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        data = request.get_json()
        if not data or 'aliases' not in data:
            return jsonify({
                "success": False,
                "message": "Alias listesi gönderilmedi"
            }), 400
        
        new_aliases = data['aliases']
        if not isinstance(new_aliases, list):
            return jsonify({
                "success": False,
                "message": "Alias listesi geçersiz formatda"
            }), 400
        
        print(f"[MATERIALS] 🏷️ Adding aliases to {material_id}: {new_aliases}")
        
        result = MaterialService.add_aliases_to_material(material_id, new_aliases)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Aliases added to {material_id}")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Alias addition failed: {result['message']}")
            return jsonify(result), 400
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/<material_id>/aliases/<alias>', methods=['DELETE'])
@jwt_required()
def remove_alias(material_id, alias):
    """Malzemeden alias sil"""
    try:
        current_user = get_current_user()
        
        # Sadece admin silebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        print(f"[MATERIALS] 🗑️ Removing alias '{alias}' from {material_id}")
        
        result = MaterialService.remove_alias_from_material(material_id, alias)
        
        if result['success']:
            print(f"[MATERIALS] ✅ Alias '{alias}' removed from {material_id}")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Alias removal failed: {result['message']}")
            return jsonify(result), 400
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/analysis-data', methods=['GET'])
@jwt_required()
def get_analysis_data():
    """Analiz için malzeme verilerini getir"""
    try:
        print("[MATERIALS] 📊 Getting analysis data")
        
        result = MaterialService.get_materials_for_analysis()
        
        if result['success']:
            print(f"[MATERIALS] ✅ Analysis data: {len(result.get('materials', []))} materials")
            return jsonify(result), 200
        else:
            print(f"[MATERIALS] ❌ Analysis data error: {result['message']}")
            return jsonify(result), 400
            
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        print(f"[MATERIALS] 💥 Exception: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

# Health check endpoint
@material_bp.route('/health', methods=['GET'])
def health_check():
    """Material API sağlık kontrolü"""
    try:
        from utils.database import db
        # Database bağlantısını test et
        db.get_db().command('ping')
        
        return jsonify({
            "success": True,
            "message": "Materials API çalışıyor",
            "database": "connected",
            "endpoints": {
                "GET /api/materials": "Tüm malzemeleri listele",
                "POST /api/materials": "Yeni malzeme oluştur",
                "GET /api/materials/{id}": "Malzeme detayı",
                "PUT /api/materials/{id}": "Malzeme güncelle", 
                "DELETE /api/materials/{id}": "Malzeme sil",
                "POST /api/materials/{id}/aliases": "Alias ekle",
                "DELETE /api/materials/{id}/aliases/{alias}": "Alias sil"
            }
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Materials API hatası: {str(e)}",
            "database": "disconnected"
        }), 500
    
    
@material_bp.route('/refresh-cache', methods=['POST'])
@jwt_required()
def refresh_material_cache():
    """✅ Malzeme cache'ini yenile - Analiz sistemi için kritik"""
    try:
        current_user = get_current_user()
        
        # Sadece admin cache yenileyebilir (güvenlik için)
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        print("[CACHE-REFRESH] 🔄 Material cache refresh başlatılıyor...")
        
        # Material analysis service cache'ini yenile
        try:
            from services.material_analysis import MaterialAnalysisService
            
            # Service instance oluştur
            service = MaterialAnalysisService()
            
            # Cache'i yenile
            service.refresh_material_cache()
            
            # Veritabanından mevcut malzeme sayısını al
            material_count = MaterialService.get_all_materials(limit=10000)
            total_materials = len(material_count.get('materials', [])) if material_count.get('success') else 0
            
            print(f"[CACHE-REFRESH] ✅ Cache başarıyla yenilendi: {total_materials} malzeme")
            
            return jsonify({
                "success": True,
                "message": f"Malzeme cache başarıyla yenilendi. {total_materials} malzeme analiz sisteminde aktif.",
                "cache_refreshed": True,
                "material_count": total_materials,
                "refresh_time": datetime.utcnow().isoformat(),
                "admin_user": current_user.get('username', 'unknown')
            }), 200
            
        except Exception as service_error:
            print(f"[CACHE-REFRESH] ❌ Service error: {service_error}")
            return jsonify({
                "success": False,
                "message": f"Material analysis service hatası: {str(service_error)}"
            }), 500
        
    except Exception as e:
        error_msg = f"Cache yenileme hatası: {str(e)}"
        print(f"[CACHE-REFRESH] ❌ Error: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@material_bp.route('/cache-status', methods=['GET'])
@jwt_required()
def get_cache_status():
    """✅ Malzeme cache durumunu kontrol et"""
    try:
        print("[CACHE-STATUS] 📊 Cache status kontrolü...")
        
        # Material count from database
        material_result = MaterialService.get_all_materials(limit=10000)
        db_material_count = len(material_result.get('materials', [])) if material_result.get('success') else 0
        
        # Cache status from service
        cache_info = {
            "database_material_count": db_material_count,
            "cache_status": "unknown",
            "analysis_service_ready": False,
            "last_refresh": None
        }
        
        try:
            from services.material_analysis import MaterialAnalysisService
            service = MaterialAnalysisService()
            
            # Cache'den malzeme sayısını al
            cached_materials = service._get_materials_cached()
            cache_material_count = len(cached_materials) if cached_materials else 0
            
            cache_info.update({
                "cache_material_count": cache_material_count,
                "cache_status": "active" if cache_material_count > 0 else "empty",
                "analysis_service_ready": True,
                "cache_db_sync": cache_material_count == db_material_count
            })
            
            print(f"[CACHE-STATUS] ✅ Status: DB={db_material_count}, Cache={cache_material_count}")
            
        except Exception as service_error:
            print(f"[CACHE-STATUS] ⚠️ Service check failed: {service_error}")
            cache_info["service_error"] = str(service_error)
        
        return jsonify({
            "success": True,
            "cache_info": cache_info,
            "recommendations": get_cache_recommendations(cache_info)
        }), 200
        
    except Exception as e:
        error_msg = f"Cache status check hatası: {str(e)}"
        print(f"[CACHE-STATUS] ❌ Error: {error_msg}")
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

def get_cache_recommendations(cache_info):
    """Cache durumuna göre öneriler"""
    recommendations = []
    
    if not cache_info.get("analysis_service_ready"):
        recommendations.append({
            "type": "error",
            "message": "Malzeme analiz servisi çalışmıyor",
            "action": "Servisi yeniden başlatın"
        })
    
    elif cache_info.get("cache_status") == "empty":
        recommendations.append({
            "type": "warning", 
            "message": "Cache boş - malzemeler analiz edilemez",
            "action": "Cache Yenile butonuna tıklayın"
        })
    
    elif not cache_info.get("cache_db_sync", True):
        recommendations.append({
            "type": "info",
            "message": f"Cache senkronize değil (DB: {cache_info.get('database_material_count')}, Cache: {cache_info.get('cache_material_count')})",
            "action": "Cache'i yenileyin"
        })
    
    elif cache_info.get("cache_status") == "active":
        recommendations.append({
            "type": "success",
            "message": "Cache aktif ve güncel",
            "action": "Yeni malzemeler eklendikten sonra cache'i yenileyin"
        })
    
    return recommendations