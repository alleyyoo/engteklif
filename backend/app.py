from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from utils.database import db
from services.auth_service import AuthService
from controllers.auth_controller import auth_bp
from controllers.user_controller import user_bp

app = Flask(__name__)

app.config.from_object(Config)

CORS(app, origins=["http://localhost:3000"])

jwt = JWTManager(app)

db.connect()
AuthService.create_admin_if_not_exists()

app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)

@app.route('/')
def home():
    return jsonify({
        "message": "Flask API çalışıyor! 🚀",
        "endpoints": {
            "login": "/api/auth/login",
            "register": "/api/auth/register", 
            "users": "/api/users"
        }
    })

@app.route('/health')
def health():
    try:
        db.get_db().command('ping')
        return jsonify({"status": "healthy"}), 200
    except:
        return jsonify({"status": "unhealthy"}), 500

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"message": "Token süresi dolmuş"}), 401

@jwt.invalid_token_loader  
def invalid_token_callback(error):
    return jsonify({"message": "Geçersiz token"}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"message": "Token gerekli"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True)