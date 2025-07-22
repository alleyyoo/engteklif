# app.py - ENHANCED VERSION WITH INTEGRATED STEP VIEWER + ACCESS TOKEN ROUTE
from flask import Flask, jsonify, send_from_directory, redirect, url_for
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
from controllers.material_price_controller import material_price_bp
from controllers.cmm_controller import cmm_bp

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object(Config)
    
    # CORS setup
    CORS(app, origins=["http://localhost:3001", "http://localhost:5051"])
    
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
    app.register_blueprint(material_price_bp)
    app.register_blueprint(cmm_bp)

    # ===== STATIC FILE SERVING - ENHANCED =====
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
    
    # ===== STEP VIEWER ROUTES - ENHANCED WITH ACCESS TOKEN =====
    @app.route('/step-viewer')
    def step_viewer_main():
        """✅ STEP Viewer Ana Sayfası - Enhanced"""
        try:
            return send_from_directory('static', 'step_viewer.html')
        except Exception as e:
            print(f"STEP viewer dosya hatası: {e}")
            return jsonify({
                "success": False,
                "message": "STEP viewer dosyası bulunamadı"
            }), 404
    
    @app.route('/step-viewer/<analysis_id>')
    def step_viewer_with_analysis(analysis_id):
        """✅ Belirli analiz için STEP viewer - Analysis ID ile direkt viewer"""
        try:
            # Analysis ID'yi validate et
            if not analysis_id or len(analysis_id) < 5:
                return jsonify({
                    "success": False,
                    "message": "Geçersiz analiz ID'si"
                }), 400
            
            # Direkt step_viewer.html'i döndür, analysis_id URL'den alınacak
            return send_from_directory('static', 'step_viewer.html')
                
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"STEP viewer hatası: {str(e)}"
            }), 500
    
    @app.route('/step-viewer/<analysis_id>/<access_token>')
    def step_viewer_with_access_token(analysis_id, access_token):
        """✅ YENİ - Access token ile STEP viewer erişimi"""
        try:
            # Analysis ID'yi validate et
            if not analysis_id or len(analysis_id) < 5:
                return jsonify({
                    "success": False,
                    "message": "Geçersiz analiz ID'si"
                }), 400
            
            # Access token'ı validate et
            if not access_token or len(access_token) < 10:
                return jsonify({
                    "success": False,
                    "message": "Geçersiz access token"
                }), 400
            
            print(f"[STEP-VIEWER] 🔐 Token ile erişim: {analysis_id} - Token: {access_token[:10]}...")
            
            # Direkt step_viewer.html'i döndür
            # JavaScript, URL'den analysis_id ve access_token'ı otomatik parse edecek
            return send_from_directory('static', 'step_viewer.html')
                
        except Exception as e:
            print(f"[STEP-VIEWER] ❌ Token ile erişim hatası: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"STEP viewer hatası: {str(e)}"
            }), 500
    
    @app.route('/3d-viewer')
    def legacy_3d_viewer():
        """Legacy 3D viewer redirect"""
        return redirect(url_for('step_viewer_main'))
    
    @app.route('/3d-viewer/<analysis_id>')
    def legacy_3d_viewer_with_analysis(analysis_id):
        """Legacy 3D viewer with analysis redirect"""
        return redirect(url_for('step_viewer_with_analysis', analysis_id=analysis_id))
    
    @app.route('/3d-viewer/<analysis_id>/<access_token>')
    def legacy_3d_viewer_with_token(analysis_id, access_token):
        """✅ YENİ - Legacy 3D viewer with access token redirect"""
        return redirect(url_for('step_viewer_with_access_token', 
                              analysis_id=analysis_id, 
                              access_token=access_token))
    
    # ===== STEP VIEWER API ENDPOINTS =====
    @app.route('/api/step-viewer/status')
    def step_viewer_status():
        """STEP viewer durumu"""
        try:
            import os
            viewer_path = os.path.join('static', 'step_viewer.html')
            viewer_exists = os.path.exists(viewer_path)
            
            return jsonify({
                "success": True,
                "viewer_available": viewer_exists,
                "viewer_path": "/step-viewer",
                "features": {
                    "file_upload": True,
                    "measurement_tools": True,
                    "multiple_views": True,
                    "wireframe_mode": True,
                    "lighting_control": True,
                    "standard_views": True,
                    "access_token_support": True  # ✅ YENİ
                },
                "supported_formats": [".step", ".stp"],
                "integration": "backend_static",
                "access_methods": {
                    "direct": "/step-viewer/{analysis_id}",
                    "with_token": "/step-viewer/{analysis_id}/{access_token}"  # ✅ YENİ
                }
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"STEP viewer durum hatası: {str(e)}"
            }), 500
    
    @app.route('/api/step-viewer/config/<analysis_id>')
    def get_step_viewer_config(analysis_id):
        """Belirli analiz için STEP viewer konfigürasyonu"""
        try:
            from models.file_analysis import FileAnalysis
            
            # Analiz kaydını bul
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis:
                return jsonify({
                    "success": False,
                    "message": "Analiz bulunamadı"
                }), 404
            
            # STEP viewer için konfigürasyon
            config = {
                "analysis_id": analysis_id,
                "file_info": {
                    "original_filename": analysis.get('original_filename'),
                    "file_type": analysis.get('file_type'),
                    "file_size": analysis.get('file_size')
                },
                "step_analysis": analysis.get('step_analysis', {}),
                "enhanced_renders": analysis.get('enhanced_renders', {}),
                "model_paths": {
                    "stl": f"/static/stepviews/{analysis_id}/model_{analysis_id}.stl",
                    "viewer_html": f"/static/stepviews/{analysis_id}/viewer.html"
                },
                "viewer_settings": {
                    "auto_fit": True,
                    "show_grid": False,
                    "show_axes": True,
                    "lighting": "enhanced",
                    "material": "aluminum"
                }
            }
            
            return jsonify({
                "success": True,
                "config": config
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Konfigürasyon hatası: {str(e)}"
            }), 500
    
    # ===== ACCESS TOKEN AUTHENTICATION FOR API =====
    @app.route('/api/step-viewer/config/<analysis_id>/<access_token>')
    def get_step_viewer_config_with_token(analysis_id, access_token):
        """✅ YENİ - Access token ile STEP viewer konfigürasyonu"""
        try:
            from models.file_analysis import FileAnalysis
            from utils.auth_utils import decode_token
            
            # Access token'ı validate et
            token_result = decode_token(access_token)
            if not token_result['success']:
                return jsonify({
                    "success": False,
                    "message": f"Geçersiz access token: {token_result['message']}"
                }), 401
            
            # Token'dan user_id al
            user_id = token_result['payload'].get('sub') or token_result['payload'].get('user_id')
            if not user_id:
                return jsonify({
                    "success": False,
                    "message": "Token'da user_id bulunamadı"
                }), 401
            
            # Analiz kaydını bul
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis:
                return jsonify({
                    "success": False,
                    "message": "Analiz bulunamadı"
                }), 404
            
            # Kullanıcı yetkisi kontrolü
            if analysis['user_id'] != user_id:
                return jsonify({
                    "success": False,
                    "message": "Bu analiz için erişim yetkiniz yok"
                }), 403
            
            print(f"[CONFIG] ✅ Token ile erişim onaylandı: {analysis_id} - User: {user_id}")
            
            # STEP viewer için konfigürasyon (aynı config)
            config = {
                "analysis_id": analysis_id,
                "file_info": {
                    "original_filename": analysis.get('original_filename'),
                    "file_type": analysis.get('file_type'),
                    "file_size": analysis.get('file_size')
                },
                "step_analysis": analysis.get('step_analysis', {}),
                "enhanced_renders": analysis.get('enhanced_renders', {}),
                "model_paths": {
                    "stl": f"/static/stepviews/{analysis_id}/model_{analysis_id}.stl",
                    "viewer_html": f"/static/stepviews/{analysis_id}/viewer.html"
                },
                "viewer_settings": {
                    "auto_fit": True,
                    "show_grid": False,
                    "show_axes": True,
                    "lighting": "enhanced",
                    "material": "aluminum"
                },
                "authenticated": True  # ✅ Token ile doğrulandı
            }
            
            return jsonify({
                "success": True,
                "config": config
            })
            
        except Exception as e:
            print(f"[CONFIG] ❌ Token ile config hatası: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"Konfigürasyon hatası: {str(e)}"
            }), 500
    
    # ===== MAIN ROUTES =====
    @app.route('/')
    def home():
        return jsonify({
            "message": "EngTeklif API çalışıyor! 🚀",
            "version": "2.1",
            "description": "Mühendislik Teklif ve Dosya Analiz Sistemi - Enhanced STEP Viewer with Access Token",
            "features": [
                "✅ 3D STEP dosya analizi",
                "✅ PDF malzeme tanıma", 
                "✅ Maliyet hesaplama",
                "✅ Enhanced 3D STEP viewer",
                "✅ Interactive measurement tools",
                "✅ Multi-view rendering",
                "✅ Malzeme veritabanı",
                "✅ Real-time 3D visualization",
                "✅ Access token authentication"  # ✅ YENİ
            ],
            "step_viewer": {
                "main_url": "/step-viewer",
                "with_analysis": "/step-viewer/{analysis_id}",
                "with_token": "/step-viewer/{analysis_id}/{access_token}",  # ✅ YENİ
                "api_status": "/api/step-viewer/status",
                "features": [
                    "File upload integration",
                    "Real-time measurement",
                    "Standard view presets", 
                    "Wireframe/solid modes",
                    "Dynamic lighting",
                    "Responsive design",
                    "Token-based authentication"  # ✅ YENİ
                ]
            },
            "endpoints": {
                "step_viewer": {
                    "main": "/step-viewer",
                    "with_analysis": "/step-viewer/{analysis_id}",
                    "with_token": "/step-viewer/{analysis_id}/{access_token}",  # ✅ YENİ
                    "status": "/api/step-viewer/status",
                    "config": "/api/step-viewer/config/{analysis_id}",
                    "config_with_token": "/api/step-viewer/config/{analysis_id}/{access_token}"  # ✅ YENİ
                },
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
            
            # STEP viewer durumu
            import os
            step_viewer_status = {
                "step_viewer_html": os.path.exists('static/step_viewer.html'),
                "static_directory": os.path.exists('static'),
                "stepviews_directory": os.path.exists('static/stepviews')
            }
            
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "collections": collections_info,
                "step_viewer": step_viewer_status,
                "features": {
                    "enhanced_step_viewer": "active",
                    "step_analysis": "active",
                    "material_analysis": "active",
                    "cost_calculation": "active",
                    "3d_rendering": "active",
                    "measurement_tools": "active",
                    "access_token_auth": "active"  # ✅ YENİ
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
            "version": "2.1.0",
            "description": "Mühendislik dosya analizi ve teklif yönetim sistemi - Enhanced STEP Viewer with Access Token",
            "database": "MongoDB",
            "framework": "Flask",
            "features": [
                "Kullanıcı yönetimi ve yetkilendirme",
                "PDF/DOC dosya analizi",
                "STEP/CAD dosya işleme",
                "Enhanced 3D STEP model görselleştirme",
                "Interactive measurement tools",
                "Multi-view 3D rendering",
                "Malzeme tanıma ve fiyatlama",
                "Geometrik tolerans yönetimi",
                "Maliyet hesaplama",
                "Excel export/import",
                "Real-time 3D visualization",
                "Access token authentication"  # ✅ YENİ
            ],
            "supported_file_types": [
                "PDF", "DOC", "DOCX", "STEP", "STP"
            ],
            "step_viewer_capabilities": {
                "interactive_3d": "Three.js tabanlı gerçek zamanlı görselleştirme",
                "file_upload": "Drag & drop STEP dosya yükleme",
                "measurement_tools": "İnteraktif mesafe ölçüm araçları",
                "view_presets": "Standart mühendislik görünümleri (Front, Top, Iso, vb.)",
                "wireframe_mode": "Wireframe/solid görünüm geçişi",
                "lighting_control": "Dinamik ışıklandırma kontrolü",
                "responsive_design": "Mobil ve masaüstü uyumlu",
                "backend_integration": "Flask backend ile tam entegrasyon",
                "token_authentication": "JWT token tabanlı güvenli erişim"  # ✅ YENİ
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
                "step_viewer": "/step-viewer",
                "step_viewer_with_token": "/step-viewer/{analysis_id}/{access_token}",  # ✅ YENİ
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
    print(f"🌐 CORS origins: http://188.132.220.35:3001, http://188.132.220.35:5051")
    print(f"🗄️  Database: {Config.DATABASE_NAME}")
    print("📐 Enhanced STEP Viewer: ACTIVE")
    print("🔧 STEP Analysis: ACTIVE")
    print("🎯 Interactive 3D Viewer: ACTIVE")
    print("📏 Measurement Tools: ACTIVE")
    print("🎨 Multi-view Rendering: ACTIVE")
    print("🔐 Access Token Authentication: ACTIVE")  # ✅ YENİ
    print("=" * 60)
    print("🔗 STEP Viewer URLs:")
    print("   Main Viewer: http://localhost:5051/step-viewer")
    print("   With Analysis: http://localhost:5051/step-viewer/{analysis_id}")
    print("   With Token: http://localhost:5051/step-viewer/{analysis_id}/{access_token}")  # ✅ YENİ
    print("   API Status: http://localhost:5051/api/step-viewer/status")
    print("=" * 60)
    print("🔐 Authentication:")
    print("   Config API: /api/step-viewer/config/{analysis_id}")
    print("   Config with Token: /api/step-viewer/config/{analysis_id}/{access_token}")  # ✅ YENİ
    print("=" * 60)
    
    app.run(
        host='0.0.0.0', 
        port=5050, 
        debug=debug_mode, 
        use_reloader=debug_mode
    )