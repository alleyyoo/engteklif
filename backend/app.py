# app.py - FIXED VERSION WITH 3D VIEWER SUPPORT
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from utils.database import db
from services.auth_service import AuthService

# Import controllers
from controllers.auth_controller import auth_bp
from controllers.user_controller import user_bp
from controllers.geometric_measurement_controller import geometric_bp
from controllers.cost_calculation_controller import cost_bp
from controllers.material_controller import material_bp
from controllers.file_upload_controller import upload_bp

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object(Config)
    
    # CORS setup
    CORS(app, origins=["http://localhost:3000"])
    
    # JWT setup
    jwt = JWTManager(app)
    
    # Database connection
    db.connect()
    
    # Create admin user if not exists
    AuthService.create_admin_if_not_exists()
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(geometric_bp)
    app.register_blueprint(material_bp)
    app.register_blueprint(cost_bp)
    app.register_blueprint(upload_bp)

    # ===== STATIC FILE SERVING - FIXED =====
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Static dosyaları serve et"""
        try:
            return send_from_directory('static', filename)
        except Exception as e:
            print(f"Static dosya hatası: {e}")
            return jsonify({
                "success": False,
                "message": f"Dosya bulunamadı: {filename}"
            }), 404
    
    # ===== 3D VIEWER ROUTES - FIXED =====
    @app.route('/3d-viewer')
    def viewer_page():
        """3D viewer ana sayfası"""
        return send_from_directory('static', '3d-viewer.html')
    
    @app.route('/3d-viewer/<analysis_id>')
    def viewer_with_analysis(analysis_id):
        """Belirli analiz için 3D viewer"""
        try:
            from flask import Response
            viewer_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>3D Model Viewer - EngTeklif</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ margin: 0; overflow: hidden; }}
                    iframe {{ width: 100vw; height: 100vh; border: none; }}
                </style>
            </head>
            <body>
                <iframe src="/static/3d-viewer.html?analysis_id={analysis_id}"></iframe>
            </body>
            </html>
            '''
            return Response(viewer_html, mimetype='text/html')
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"3D viewer hatası: {str(e)}"
            }), 500
    
    # ===== MAIN ROUTES =====
    @app.route('/')
    def home():
        return jsonify({
            "message": "EngTeklif API çalışıyor! 🚀",
            "version": "2.0",
            "description": "Mühendislik Teklif ve Dosya Analiz Sistemi",
            "features": [
                "✅ 3D STEP dosya analizi",
                "✅ PDF malzeme tanıma",
                "✅ Maliyet hesaplama",
                "✅ 3D model görselleştirme",
                "✅ Wireframe 3D viewer",
                "✅ Malzeme veritabanı"
            ],
            "endpoints": {
                "auth": {
                    "login": "/api/auth/login",
                    "register": "/api/auth/register",
                    "me": "/api/auth/me",
                    "refresh": "/api/auth/refresh",
                    "logout": "/api/auth/logout",
                    "change_password": "/api/auth/change-password",
                    "profile": "/api/auth/profile"
                },
                "geometric_measurements": {
                    "list": "/api/geometric-measurements",
                    "create": "/api/geometric-measurements",
                    "get": "/api/geometric-measurements/{id}",
                    "update": "/api/geometric-measurements/{id}",
                    "delete": "/api/geometric-measurements/{id}",
                    "types": "/api/geometric-measurements/types",
                    "find_matching": "/api/geometric-measurements/find-matching"
                },
                "users": {
                    "list": "/api/users",
                    "get": "/api/users/{id}",
                    "update": "/api/users/{id}",
                    "delete": "/api/users/{id}",
                    "activate": "/api/users/{id}/activate",
                    "deactivate": "/api/users/{id}/deactivate",
                    "change_role": "/api/users/{id}/role",
                    "stats": "/api/users/stats"
                },
                "materials": {
                    "list": "/api/materials",
                    "create": "/api/materials",
                    "get": "/api/materials/{id}",
                    "update": "/api/materials/{id}",
                    "delete": "/api/materials/{id}",
                    "categories": "/api/materials/categories",
                    "bulk_prices": "/api/materials/bulk-update-prices",
                    "add_aliases": "/api/materials/{id}/aliases",
                    "remove_alias": "/api/materials/{id}/aliases/{alias}",
                    "analysis_data": "/api/materials/analysis-data"
                },
                "cost_calculation": {
                    "basic": "/api/cost-calculation/basic",
                    "comprehensive": "/api/cost-calculation/comprehensive",
                    "batch": "/api/cost-calculation/batch",
                    "estimate_time": "/api/cost-calculation/estimate-machining-time",
                    "quick_estimate": "/api/cost-calculation/quick-estimate",
                    "materials": "/api/cost-calculation/supported-materials",
                    "material_info": "/api/cost-calculation/material-info/{name}",
                    "presets": "/api/cost-calculation/calculation-presets",
                    "validate": "/api/cost-calculation/validate-inputs"
                },
                "file_upload": {
                    "single": "/api/upload/single",
                    "multiple": "/api/upload/multiple", 
                    "analyze": "/api/upload/analyze/{analysis_id}",
                    "status": "/api/upload/status/{analysis_id}",
                    "my_uploads": "/api/upload/my-uploads",
                    "delete": "/api/upload/delete/{analysis_id}",
                    "supported_formats": "/api/upload/supported-formats",
                    "wireframe": "/api/upload/wireframe/{analysis_id}",
                    "render": "/api/upload/render/{analysis_id}",
                    "3d_viewer": "/api/upload/3d-viewer/{analysis_id}"
                },
                "3d_viewer": {
                    "main": "/3d-viewer",
                    "with_analysis": "/3d-viewer/{analysis_id}",
                    "static_files": "/static/{filename}"
                }
            }
        })
    
    @app.route('/health')
    def health():
        try:
            # MongoDB bağlantı testi
            db.get_db().command('ping')
            
            # Koleksiyon sayıları
            collections_info = {}
            database = db.get_db()
            
            try:
                collections_info = {
                    "users": database.users.count_documents({}),
                    "materials": database.materials.count_documents({}),
                    "geometric_measurements": database.geometric_measurements.count_documents({}),
                    "file_analyses": database.file_analyses.count_documents({})
                }
            except Exception:
                collections_info = {"error": "Collection count failed"}
            
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "collections": collections_info,
                "features": {
                    "3d_viewer": "active",
                    "step_analysis": "active",
                    "material_analysis": "active",
                    "cost_calculation": "active"
                },
                "timestamp": "2025-01-01T00:00:00Z"
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": "2025-01-01T00:00:00Z"
            }), 500
    
    @app.route('/api/info')
    def api_info():
        """API bilgileri ve sürüm detayları"""
        return jsonify({
            "api_name": "EngTeklif API",
            "version": "2.0.0",
            "description": "Mühendislik dosya analizi ve teklif yönetim sistemi",
            "database": "MongoDB",
            "framework": "Flask",
            "features": [
                "Kullanıcı yönetimi ve yetkilendirme",
                "PDF/DOC dosya analizi",
                "STEP/CAD dosya işleme",
                "3D model görselleştirme",
                "Wireframe 3D viewer",
                "Malzeme tanıma ve fiyatlama",
                "Geometrik tolerans yönetimi",
                "Maliyet hesaplama",
                "Excel export/import",
                "Real-time 3D rendering"
            ],
            "supported_file_types": [
                "PDF", "DOC", "DOCX", "STEP", "STP"
            ],
            "3d_capabilities": {
                "wireframe_viewer": "Three.js tabanlı 3D görüntüleme",
                "step_analysis": "CadQuery ile geometrik analiz",
                "render_generation": "Matplotlib ile görsel oluşturma",
                "interactive_controls": "Orbit, zoom, pan kontrolleri"
            },
            "authentication": "JWT Bearer Token",
            "documentation": "/api/docs"
        })
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "message": "Token süresi dolmuş",
            "error_code": "TOKEN_EXPIRED"
        }), 401
    
    @jwt.invalid_token_loader  
    def invalid_token_callback(error):
        return jsonify({
            "success": False,
            "message": "Geçersiz token",
            "error_code": "INVALID_TOKEN"
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "success": False,
            "message": "Yetkilendirme token'ı gerekli",
            "error_code": "MISSING_TOKEN"
        }), 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "message": "Fresh token gerekli",
            "error_code": "FRESH_TOKEN_REQUIRED"
        }), 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "message": "Token iptal edilmiş",
            "error_code": "TOKEN_REVOKED"
        }), 401
    
    # Global error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "message": "Geçersiz istek",
            "error": "Bad Request",
            "status_code": 400
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "message": "Endpoint bulunamadı",
            "error": "Not Found",
            "status_code": 404,
            "available_endpoints": {
                "api": "/api/info",
                "3d_viewer": "/3d-viewer",
                "health": "/health"
            }
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "success": False,
            "message": "HTTP method'u desteklenmiyor",
            "error": "Method Not Allowed",
            "status_code": 405
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "success": False,
            "message": "Sunucu hatası",
            "error": "Internal Server Error",
            "status_code": 500
        }), 500
    
    # Request logging middleware
    @app.before_request
    def log_request_info():
        import logging
        from flask import request
        
        # Basic request logging
        logging.info(f"Request: {request.method} {request.url}")
    
    @app.after_request
    def after_request(response):
        # CORS headers
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        # Security headers
        response.headers.add('X-Content-Type-Options', 'nosniff')
        response.headers.add('X-Frame-Options', 'DENY')
        response.headers.add('X-XSS-Protection', '1; mode=block')
        
        return response
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    import os
    
    # Development settings
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    
    print("🚀 EngTeklif API başlatılıyor...")
    print(f"📊 Debug mode: {debug_mode}")
    print(f"🌐 CORS origin: http://localhost:3000")
    print(f"🗄️  Database: {Config.DATABASE_NAME}")
    print("📐 3D Viewer: ACTIVE")
    print("🔧 STEP Analysis: ACTIVE")
    print("🎯 Wireframe Rendering: ACTIVE")
    print("=" * 50)
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=debug_mode, 
        use_reloader=debug_mode
    )