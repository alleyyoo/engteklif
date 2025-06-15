from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from models.material import MaterialCreate, MaterialUpdate
from services.material_service import MaterialService
from models.user import User, UserRole

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
        search = request.args.get('search', None, type=str)
        category = request.args.get('category', None, type=str)
        
        result = MaterialService.get_all_materials(page, limit, search, category)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
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
        
        material_data = MaterialCreate(**data)
        result = MaterialService.create_material(material_data)
        
        if result['success']:
            return jsonify(result), 201
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

@material_bp.route('/<material_id>', methods=['GET'])
@jwt_required()
def get_material(material_id):
    """Belirli bir malzemeyi getir"""
    try:
        result = MaterialService.get_material_by_id(material_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
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
        
        update_data = MaterialUpdate(**data)
        result = MaterialService.update_material(material_id, update_data)
        
        if result['success']:
            return jsonify(result), 200
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
        
        result = MaterialService.delete_material(material_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@material_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Malzeme kategorilerini getir"""
    try:
        result = MaterialService.get_categories()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
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
        
        result = MaterialService.add_aliases_to_material(material_id, new_aliases)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
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
        
        result = MaterialService.remove_alias_from_material(material_id, alias)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@material_bp.route('/analysis-data', methods=['GET'])
@jwt_required()
def get_analysis_data():
    """Analiz için malzeme verilerini getir"""
    try:
        result = MaterialService.get_materials_for_analysis()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500