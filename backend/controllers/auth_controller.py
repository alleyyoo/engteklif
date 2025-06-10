from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from pydantic import ValidationError
from models.user import RegisterRequest, LoginRequest, User
from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Kullanıcı kaydı"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False, 
                "message": "Veri gönderilmedi"
            }), 400
        
        # Pydantic ile validate et
        register_request = RegisterRequest(**data)
        
        # Servis çağır
        result = AuthService.register_user(register_request)
        
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

@auth_bp.route('/login', methods=['POST'])
def login():
    """Kullanıcı girişi"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False, 
                "message": "Veri gönderilmedi"
            }), 400
        
        # Pydantic ile validate et
        login_request = LoginRequest(**data)
        
        # Servis çağır
        result = AuthService.login_user(login_request)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
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

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Mevcut kullanıcı bilgilerini getir"""
    try:
        current_user_id = get_jwt_identity()
        user = User.find_by_id(current_user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "Kullanıcı bulunamadı"
            }), 404
        
        return jsonify({
            "success": True,
            "user": user
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Token yenile"""
    try:
        current_user_id = get_jwt_identity()
        
        # Servis çağır
        result = AuthService.refresh_token(current_user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Çıkış yap"""
    try:
        current_user_id = get_jwt_identity()
        
        # Servis çağır
        result = AuthService.logout_user(current_user_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Şifre değiştir"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        current_user_id = get_jwt_identity()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({
                "success": False,
                "message": "Eski ve yeni şifre gerekli"
            }), 400
        
        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "message": "Yeni şifre en az 6 karakter olmalı"
            }), 400
        
        # Servis çağır
        result = AuthService.change_password(current_user_id, old_password, new_password)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Profil güncelle"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Güncellenecek veri gönderilmedi"
            }), 400
        
        current_user_id = get_jwt_identity()
        current_user = User.find_by_id(current_user_id)
        
        if not current_user:
            return jsonify({
                "success": False,
                "message": "Kullanıcı bulunamadı"
            }), 404
        
        # Güncellenebilir alanları filtrele
        allowed_fields = ['name', 'surname', 'email']
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not filtered_data:
            return jsonify({
                "success": False,
                "message": "Güncellenecek geçerli veri bulunamadı"
            }), 400
        
        # Email değişikliği kontrolü
        if 'email' in filtered_data and filtered_data['email'] != current_user['email']:
            if User.email_exists(filtered_data['email']):
                return jsonify({
                    "success": False,
                    "message": "Bu email adresi zaten kullanılıyor"
                }), 400
        
        # Güncelle
        success = User.update_user(current_user_id, filtered_data)
        
        if success:
            updated_user = User.find_by_id(current_user_id)
            return jsonify({
                "success": True,
                "message": "Profil başarıyla güncellendi",
                "user": updated_user
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Profil güncelleme başarısız"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@auth_bp.route('/check-username/<username>', methods=['GET'])
def check_username(username):
    """Username müsaitlik kontrolü"""
    try:
        if len(username) < 3:
            return jsonify({
                "success": False,
                "message": "Kullanıcı adı en az 3 karakter olmalı"
            }), 400
        
        exists = User.username_exists(username)
        
        return jsonify({
            "success": True,
            "available": not exists,
            "message": "Kullanıcı adı müsait değil" if exists else "Kullanıcı adı müsait"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@auth_bp.route('/check-email/<email>', methods=['GET'])
def check_email(email):
    """Email müsaitlik kontrolü"""
    try:
        exists = User.email_exists(email)
        
        return jsonify({
            "success": True,
            "available": not exists,
            "message": "Email adresi kullanımda" if exists else "Email adresi müsait"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500