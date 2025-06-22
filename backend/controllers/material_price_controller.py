# controllers/material_price_controller.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import BaseModel, Field, ValidationError
from typing import Optional
from models.user import User, UserRole
from services.material_service import MaterialService

material_price_bp = Blueprint('material_prices', __name__, url_prefix='/api/material-prices')

def get_current_user():
    """Mevcut kullanıcıyı getir"""
    current_user_id = get_jwt_identity()
    return User.find_by_id(current_user_id)

class MaterialPriceCreate(BaseModel):
    material_name: str = Field(..., min_length=1, description="Malzeme adı")
    price_per_kg: float = Field(..., ge=0, description="Kg başına fiyat (USD)")

class MaterialPriceUpdate(BaseModel):
    price_per_kg: float = Field(..., ge=0, description="Kg başına fiyat (USD)")

@material_price_bp.route('', methods=['GET'])
@jwt_required()
def get_material_prices():
    """Malzeme fiyatlarını getir"""
    try:
        result = MaterialService.get_all_materials(limit=1000)
        
        if result['success']:
            materials_with_prices = [
                {
                    "id": material['id'],
                    "material_name": material['name'],
                    "price": material.get('price_per_kg'),
                    "density": material.get('density'),
                    "category": material.get('category')
                }
                for material in result['materials']
                if material.get('price_per_kg') is not None
            ]
            
            return jsonify({
                "success": True,
                "prices": materials_with_prices,
                "total_count": len(materials_with_prices)
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@material_price_bp.route('', methods=['POST'])
@jwt_required()
def add_or_update_material_price():
    """Malzeme fiyatı ekle veya güncelle"""
    try:
        current_user = get_current_user()
        
        # Sadece admin ekleyebilir/güncelleyebilir
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
        
        price_data = MaterialPriceCreate(**data)
        
        # Malzemeyi bul
        material_result = MaterialService.get_material_by_name(price_data.material_name)
        
        if not material_result['success']:
            return jsonify({
                "success": False,
                "message": f"'{price_data.material_name}' malzemesi bulunamadı"
            }), 404
        
        material = material_result['material']
        
        # Fiyat bilgisini güncelle
        update_result = MaterialService.update_material(material['id'], {
            "price_per_kg": price_data.price_per_kg
        })
        
        if update_result['success']:
            return jsonify({
                "success": True,
                "message": "Fiyat başarıyla güncellendi",
                "material": update_result['material']
            }), 200
        else:
            return jsonify(update_result), 400
            
    except ValidationError as e:
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@material_price_bp.route('/<price_id>', methods=['PUT'])
@jwt_required()
def update_material_price(price_id):
    """Malzeme fiyatını güncelle"""
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
        
        price_update = MaterialPriceUpdate(**data)
        
        # Material ID'si aslında price_id burada
        result = MaterialService.update_material(price_id, {
            "price_per_kg": price_update.price_per_kg
        })
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": "Fiyat başarıyla güncellendi",
                "material": result['material']
            }), 200
        else:
            return jsonify(result), 400
            
    except ValidationError as e:
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@material_price_bp.route('/<price_id>', methods=['DELETE'])
@jwt_required()
def delete_material_price(price_id):
    """Malzeme fiyatını sil (sadece fiyat bilgisini temizle)"""
    try:
        current_user = get_current_user()
        
        # Sadece admin silebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        # Fiyat bilgisini null yap
        result = MaterialService.update_material(price_id, {
            "price_per_kg": None
        })
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": "Fiyat bilgisi silindi"
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@material_price_bp.route('/bulk-update', methods=['POST'])
@jwt_required()
def bulk_update_material_prices():
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
        
        price_updates = data['price_updates']  # Dict[material_name, price]
        
        if not isinstance(price_updates, dict):
            return jsonify({
                "success": False,
                "message": "Geçersiz fiyat güncelleme formatı"
            }), 400
        
        # MaterialService'deki bulk_update_prices metodunu kullan
        result = MaterialService.bulk_update_prices(price_updates)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@material_price_bp.route('/export', methods=['GET'])
@jwt_required()
def export_material_prices():
    """Malzeme fiyatlarını Excel'e aktar"""
    try:
        current_user = get_current_user()
        
        # Sadece admin export edebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        # Tüm malzemeleri fiyat bilgileriyle getir
        result = MaterialService.get_all_materials(limit=10000)
        
        if result['success']:
            try:
                import pandas as pd
                import io
                from datetime import datetime
                
                # DataFrame oluştur
                materials_data = []
                for material in result['materials']:
                    materials_data.append({
                        'Malzeme Adı': material['name'],
                        'Kategori': material.get('category', ''),
                        'Yoğunluk (g/cm³)': material.get('density', ''),
                        'Fiyat (USD/kg)': material.get('price_per_kg', ''),
                        'Aliaslar': ', '.join(material.get('aliases', [])),
                        'Durum': 'Aktif' if material.get('is_active', True) else 'Pasif'
                    })
                
                df = pd.DataFrame(materials_data)
                
                # Excel dosyası oluştur
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Malzeme Fiyatları', index=False)
                
                output.seek(0)
                
                # Dosya adı oluştur
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"malzeme_fiyatlari_{timestamp}.xlsx"
                
                from flask import send_file
                return send_file(
                    output,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=filename
                )
                
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "Excel export için pandas gerekli"
                }), 500
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Excel export hatası: {str(e)}"
        }), 500