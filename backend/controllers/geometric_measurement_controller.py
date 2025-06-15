from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from models.geometric_measurement import GeometricMeasurementCreate, GeometricMeasurementUpdate
from services.geometric_measurement_service import GeometricMeasurementService
from models.user import User, UserRole

geometric_bp = Blueprint('geometric', __name__, url_prefix='/api/geometric-measurements')

def get_current_user():
    """Mevcut kullanıcıyı getir"""
    current_user_id = get_jwt_identity()
    return User.find_by_id(current_user_id)

@geometric_bp.route('', methods=['GET'])
@jwt_required()
def get_measurements():
    """Tüm ölçümleri getir"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        search = request.args.get('search', None, type=str)
        
        result = GeometricMeasurementService.get_all_measurements(page, limit, search)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@geometric_bp.route('', methods=['POST'])
@jwt_required()
def create_measurement():
    """Yeni ölçüm oluştur"""
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
        
        measurement_data = GeometricMeasurementCreate(**data)
        result = GeometricMeasurementService.create_measurement(measurement_data)
        
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

@geometric_bp.route('/<measurement_id>', methods=['GET'])
@jwt_required()
def get_measurement(measurement_id):
    """Belirli bir ölçümü getir"""
    try:
        result = GeometricMeasurementService.get_measurement_by_id(measurement_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@geometric_bp.route('/<measurement_id>', methods=['PUT'])
@jwt_required()
def update_measurement(measurement_id):
    """Ölçüm güncelle"""
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
        
        update_data = GeometricMeasurementUpdate(**data)
        result = GeometricMeasurementService.update_measurement(measurement_id, update_data)
        
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

@geometric_bp.route('/<measurement_id>', methods=['DELETE'])
@jwt_required()
def delete_measurement(measurement_id):
    """Ölçüm sil"""
    try:
        current_user = get_current_user()
        
        # Sadece admin silebilir
        if current_user['role'] != UserRole.ADMIN:
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        result = GeometricMeasurementService.delete_measurement(measurement_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@geometric_bp.route('/types', methods=['GET'])
@jwt_required()
def get_measurement_types():
    """Ölçüm türlerini getir"""
    try:
        result = GeometricMeasurementService.get_measurement_types()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@geometric_bp.route('/find-matching', methods=['POST'])
@jwt_required()
def find_matching_measurement():
    """Değere uygun ölçüm bul"""
    try:
        data = request.get_json()
        if not data or 'type' not in data or 'value' not in data:
            return jsonify({
                "success": False,
                "message": "Tür ve değer gerekli"
            }), 400
        
        measurement_type = data['type']
        value = float(data['value'])
        
        result = GeometricMeasurementService.find_matching_measurement(measurement_type, value)
        
        return jsonify(result), 200
            
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Geçersiz değer formatı"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500