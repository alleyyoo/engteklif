# controllers/file_upload_controller.py - UPDATED WITH 3D MODEL GENERATION

import os
import time
import uuid
from flask import Blueprint, request, jsonify, send_file, Response, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from typing import List, Dict, Any
from models.user import User
from models.file_analysis import FileAnalysis, FileAnalysisCreate
from services.material_analysis import MaterialAnalysisService, CostEstimationService
from services.model_3d_service import Model3DService 
import numpy as np
import math

# Blueprint oluştur
upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

# Konfigürasyon
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'step', 'stp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_REQUEST = 10

# Upload klasörünü oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("static", exist_ok=True)  # Render'lar için

def get_current_user():
    """Mevcut kullanıcıyı getir"""
    current_user_id = get_jwt_identity()
    return User.find_by_id(current_user_id)

def allowed_file(filename: str) -> bool:
    """Dosya uzantısı kontrolü"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename: str) -> str:
    """Dosya tipini belirle"""
    if '.' in filename:
        extension = filename.rsplit('.', 1)[1].lower()
        if extension == 'pdf':
            return 'pdf'
        elif extension in ['doc', 'docx']:
            return 'document'
        elif extension in ['step', 'stp']:
            return 'step'
    return 'unknown'

# ===== EXISTING ENDPOINTS =====

@upload_bp.route('/single', methods=['POST'])
@jwt_required()
def upload_single_file():
    """Tek dosya yükleme"""
    try:
        current_user = get_current_user()
        
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "Dosya bulunamadı"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "Dosya seçilmedi"
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": f"Desteklenmeyen dosya türü. İzin verilen: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Dosya boyutu kontrolü
        file.stream.seek(0, 2)
        file_size = file.stream.tell()
        file.stream.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                "success": False,
                "message": f"Dosya çok büyük. Maksimum boyut: {MAX_FILE_SIZE // (1024*1024)}MB"
            }), 400
        
        # Güvenli dosya adı oluştur
        original_filename = file.filename
        secure_name = secure_filename(original_filename)
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{secure_name}"
        
        # Dosyayı kaydet
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Dosya analizi kaydı oluştur
        file_analysis_data = FileAnalysisCreate(
            filename=unique_filename,
            original_filename=original_filename,
            file_type=get_file_type(original_filename),
            file_size=file_size,
            file_path=file_path
        )
        
        analysis_record = FileAnalysis.create_analysis({
            **file_analysis_data.dict(),
            "user_id": current_user['id'],
            "analysis_status": "uploaded"
        })
        
        return jsonify({
            "success": True,
            "message": "Dosya başarıyla yüklendi",
            "file_info": {
                "analysis_id": analysis_record['id'],
                "filename": unique_filename,
                "original_filename": original_filename,
                "file_type": get_file_type(original_filename),
                "file_size": file_size,
                "upload_time": analysis_record['created_at']
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Dosya yükleme hatası: {str(e)}"
        }), 500

@upload_bp.route('/multiple', methods=['POST'])
@jwt_required()
def upload_multiple_files():
    """Çoklu dosya yükleme"""
    try:
        current_user = get_current_user()
        
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({
                "success": False,
                "message": "Hiç dosya bulunamadı"
            }), 400
        
        if len(files) > MAX_FILES_PER_REQUEST:
            return jsonify({
                "success": False,
                "message": f"Çok fazla dosya. Maksimum: {MAX_FILES_PER_REQUEST}"
            }), 400
        
        successful_uploads = []
        failed_uploads = []
        
        for file in files:
            try:
                if file.filename == '':
                    failed_uploads.append({
                        "filename": "unknown",
                        "error": "Boş dosya adı"
                    })
                    continue
                
                if not allowed_file(file.filename):
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": "Desteklenmeyen dosya türü"
                    })
                    continue
                
                # Dosya boyutu kontrolü
                file.stream.seek(0, 2)
                file_size = file.stream.tell()
                file.stream.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": f"Dosya çok büyük (>{MAX_FILE_SIZE // (1024*1024)}MB)"
                    })
                    continue
                
                # Dosyayı kaydet
                original_filename = file.filename
                secure_name = secure_filename(original_filename)
                timestamp = int(time.time())
                unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{secure_name}"
                
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                
                # Analiz kaydı oluştur
                analysis_record = FileAnalysis.create_analysis({
                    "user_id": current_user['id'],
                    "filename": unique_filename,
                    "original_filename": original_filename,
                    "file_type": get_file_type(original_filename),
                    "file_size": file_size,
                    "file_path": file_path,
                    "analysis_status": "uploaded"
                })
                
                successful_uploads.append({
                    "analysis_id": analysis_record['id'],
                    "filename": unique_filename,
                    "original_filename": original_filename,
                    "file_type": get_file_type(original_filename),
                    "file_size": file_size
                })
                
            except Exception as e:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "message": f"{len(successful_uploads)} dosya başarıyla yüklendi",
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "summary": {
                "total_files": len(files),
                "successful": len(successful_uploads),
                "failed": len(failed_uploads)
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Çoklu dosya yükleme hatası: {str(e)}"
        }), 500

@upload_bp.route('/analyze/<analysis_id>', methods=['POST'])
@jwt_required()
def analyze_uploaded_file(analysis_id):
    """Yüklenmiş dosyayı analiz et"""
    try:
        current_user = get_current_user()
        
        # Analiz kaydını bul
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        # Dosya varlık kontrolü
        if not os.path.exists(analysis['file_path']):
            return jsonify({
                "success": False,
                "message": "Dosya sistemde bulunamadı"
            }), 404
        
        # Analiz durumu kontrolü
        if analysis['analysis_status'] == 'analyzing':
            return jsonify({
                "success": False,
                "message": "Dosya zaten analiz ediliyor"
            }), 409
        
        # Analiz durumunu güncelle
        FileAnalysis.update_analysis(analysis_id, {
            "analysis_status": "analyzing",
            "processing_time": None,
            "error_message": None
        })
        
        start_time = time.time()
        
        # Material Analysis Service kullan
        try:
            material_service = MaterialAnalysisService()
            
            # Kapsamlı analiz yap
            if analysis['file_type'] in ['pdf', 'document', 'step']:
                result = material_service.analyze_document_comprehensive(
                    analysis['file_path'], 
                    analysis['file_type'],
                    current_user['id']
                )
                
                # Başarılı analiz kontrolü
                analysis_success = not result.get('error')
                
                if analysis_success:
                    processing_time = time.time() - start_time
                    
                    # Sonuçları kaydet
                    update_data = {
                        "analysis_status": "completed",
                        "processing_time": processing_time,
                        "material_matches": result.get('material_matches', []),
                        "best_material_block": result.get('best_block', ''),
                        "rotation_count": result.get('rotation_count', 0),
                        "step_analysis": result.get('step_analysis', {}),
                        "cost_estimation": result.get('cost_estimation', {}),
                        "ai_price_prediction": result.get('ai_price_prediction', {}),
                        "isometric_view": result.get('isometric_view'),
                        "processing_log": result.get('processing_log', []),
                        "step_file_hash": result.get('step_file_hash'),
                        "all_material_calculations": result.get('all_material_calculations', []),
                        "material_options": result.get('material_options', [])
                    }
                    
                    FileAnalysis.update_analysis(analysis_id, update_data)
                    
                    # ✅ 3D MODEL GENERATION - AUTOMATIC AFTER SUCCESSFUL ANALYSIS
                    try:
                        model_service = Model3DService()
                        model_result = model_service.generate_3d_views_from_analysis(
                            analysis_id, 
                            views=['isometric']  # İlk olarak sadece isometric
                        )
                        
                        if model_result['success']:
                            print(f"[SUCCESS] ✅ 3D model oluşturuldu: {analysis_id}")
                        else:
                            print(f"[WARN] 3D model oluşturulamadı: {model_result.get('message')}")
                            
                    except Exception as model_error:
                        print(f"[ERROR] 3D model oluşturma hatası: {model_error}")
                        # 3D model hatası ana analizi etkilemez
                    
                    # Güncellenmiş analizi döndür
                    updated_analysis = FileAnalysis.find_by_id(analysis_id)
                    
                    return jsonify({
                        "success": True,
                        "message": "Analiz başarıyla tamamlandı",
                        "analysis": updated_analysis,
                        "processing_time": processing_time,
                        "analysis_details": {
                            "material_matches_count": len(result.get('material_matches', [])),
                            "step_analysis_available": bool(result.get('step_analysis')),
                            "cost_estimation_available": bool(result.get('cost_estimation')),
                            "processing_steps": len(result.get('processing_log', [])),
                            "all_material_calculations_count": len(result.get('all_material_calculations', [])),
                            "material_options_count": len(result.get('material_options', [])),
                            "3d_render_available": bool(result.get('isometric_view')),
                            "3d_model_generated": updated_analysis.get('3d_views_generated', False)
                        }
                    }), 200
                    
                else:
                    # Analiz hatası
                    error_msg = result.get('error', 'Bilinmeyen analiz hatası')
                    
                    FileAnalysis.update_analysis(analysis_id, {
                        "analysis_status": "failed",
                        "error_message": error_msg,
                        "processing_time": time.time() - start_time
                    })
                    
                    return jsonify({
                        "success": False,
                        "message": f"Analiz hatası: {error_msg}",
                        "error_details": result.get('processing_log', [])
                    }), 500
            else:
                # Desteklenmeyen dosya türü
                FileAnalysis.update_analysis(analysis_id, {
                    "analysis_status": "failed",
                    "error_message": "Desteklenmeyen dosya türü"
                })
                
                return jsonify({
                    "success": False,
                    "message": "Desteklenmeyen dosya türü"
                }), 400
                
        except Exception as analysis_error:
            # Material Analysis hatası
            error_message = f"Material Analysis hatası: {str(analysis_error)}"
            
            FileAnalysis.update_analysis(analysis_id, {
                "analysis_status": "failed",
                "error_message": error_message,
                "processing_time": time.time() - start_time
            })
            
            return jsonify({
                "success": False,
                "message": error_message
            }), 500
        
    except Exception as e:
        # Genel hata durumunda analiz durumunu güncelle
        try:
            FileAnalysis.update_analysis(analysis_id, {
                "analysis_status": "failed",
                "error_message": str(e)
            })
        except:
            pass
            
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen analiz hatası: {str(e)}"
        }), 500

# ===== 3D MODEL ENDPOINTS - YENİ =====

@upload_bp.route('/generate-3d-model/<analysis_id>', methods=['POST'])
@jwt_required()
def generate_3d_model(analysis_id):
    """
    3D model oluştur - app.py'deki isometric_view benzeri
    """
    try:
        current_user = get_current_user()
        
        # Analiz kaydını kontrol et
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        # STEP analizi var mı kontrol et
        step_analysis = analysis.get('step_analysis', {})
        if not step_analysis or step_analysis.get('error'):
            return jsonify({
                "success": False,
                "message": "STEP analizi mevcut değil"
            }), 404
        
        # Görünüm türlerini al (default: isometric)
        data = request.get_json() or {}
        views = data.get('views', ['isometric'])
        
        # 3D Model Service kullan
        model_service = Model3DService()
        result = model_service.generate_3d_views_from_analysis(analysis_id, views)
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": result['message'],
                "views": result['views'],
                "session_id": result['session_id'],
                "total_generated": len(result['views'])
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": result['message']
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"3D model oluşturma hatası: {str(e)}"
        }), 500

@upload_bp.route('/wireframe/<analysis_id>', methods=['GET'])
@jwt_required()
def get_wireframe_data_enhanced(analysis_id):
    """STEP/PDF dosyası için gelişmiş wireframe data getir"""
    try:
        current_user = get_current_user()
        
        # Analiz kaydını bul
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        # STEP analizi kontrolü
        step_analysis = analysis.get('step_analysis', {})
        if not step_analysis:
            return jsonify({
                "success": False,
                "message": "STEP analizi mevcut değil"
            }), 404
        
        wireframe_data = None
        
        # STEP dosyası varsa önce onu dene
        file_path = analysis.get('file_path')
        if file_path and os.path.exists(file_path) and file_path.lower().endswith(('.step', '.stp')):
            try:
                # Gerçek STEP dosyasından wireframe
                wireframe_data = create_step_wireframe_data_enhanced(file_path)
                print(f"[INFO] STEP dosyasından wireframe oluşturuldu: {analysis_id}")
            except Exception as step_error:
                print(f"[WARN] STEP wireframe hatası: {step_error}")
        
        # STEP wireframe başarısızsa, analiz verilerinden oluştur
        if not wireframe_data:
            if step_analysis.get('error'):
                # PDF'den gelen tahmini veriler
                wireframe_data = create_pdf_wireframe_data(step_analysis)
                print(f"[INFO] PDF analizi verilerinden wireframe oluşturuldu: {analysis_id}")
            else:
                # STEP analizi verilerinden
                wireframe_data = create_wireframe_from_step_analysis(step_analysis)
                print(f"[INFO] STEP analizi verilerinden wireframe oluşturuldu: {analysis_id}")
        
        if wireframe_data:
            return jsonify({
                "success": True,
                "wireframe_data": wireframe_data,
                "step_analysis": step_analysis,
                "material_info": {
                    "matches": analysis.get('material_matches', []),
                    "calculations": analysis.get('all_material_calculations', []),
                    "material_used": analysis.get('best_material', 'Bilinmiyor')
                },
                "file_info": {
                    "original_filename": analysis.get('original_filename', ''),
                    "file_type": analysis.get('file_type', ''),
                    "analysis_method": step_analysis.get('method', 'unknown')
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Wireframe data oluşturulamadı"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Wireframe data hatası: {str(e)}"
        }), 500

@upload_bp.route('/3d-viewer-data/<analysis_id>', methods=['GET'])
@jwt_required()
def get_3d_viewer_data(analysis_id):
    """3D viewer için tam veri seti"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({"success": False, "message": "Analiz bulunamadı"}), 404
        
        if analysis['user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Erişim yetkisi yok"}), 403
        
        step_analysis = analysis.get('step_analysis', {})
        
        # Wireframe data oluştur
        wireframe_data = None
        file_path = analysis.get('file_path')
        
        if file_path and os.path.exists(file_path) and file_path.lower().endswith(('.step', '.stp')):
            wireframe_data = create_step_wireframe_data_enhanced(file_path)
        elif step_analysis:
            wireframe_data = create_wireframe_from_step_analysis(step_analysis)
        
        # Material calculations
        material_calculations = analysis.get('all_material_calculations', [])
        best_material = None
        if material_calculations:
            # En ucuz malzemeyi bul
            best_material = min(material_calculations, key=lambda x: x.get('material_cost', float('inf')))
        
        # Dimensions
        dimensions = {
            "x_mm": step_analysis.get("X (mm)", 0),
            "y_mm": step_analysis.get("Y (mm)", 0), 
            "z_mm": step_analysis.get("Z (mm)", 0),
            "volume_mm3": step_analysis.get("Prizma Hacmi (mm³)", 0),
            "surface_area_mm2": step_analysis.get("Toplam Yüzey Alanı (mm²)", 0),
            "waste_volume_mm3": step_analysis.get("Talaş Hacmi (mm³)", 0),
            "waste_ratio_percent": step_analysis.get("Talaş Oranı (%)", 0)
        }
        
        return jsonify({
            "success": True,
            "analysis_id": analysis_id,
            "wireframe_data": wireframe_data,
            "dimensions": dimensions,
            "materials": {
                "all_calculations": material_calculations,
                "best_material": best_material,
                "matches": analysis.get('material_matches', [])
            },
            "file_info": {
                "original_filename": analysis.get('original_filename'),
                "file_type": analysis.get('file_type'),
                "file_size": analysis.get('file_size'),
                "processing_time": analysis.get('processing_time')
            },
            "cost_estimation": analysis.get('cost_estimation', {}),
            "ai_prediction": analysis.get('ai_price_prediction', {})
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"3D viewer data hatası: {str(e)}"
        }), 500
    
@upload_bp.route('/render-3d/<analysis_id>', methods=['POST'])
@jwt_required()
def render_3d_model(analysis_id):
    """3D model render'ı oluştur ve kaydet"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis or analysis['user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Analiz erişilemez"}), 404
        
        # Render parametreleri
        data = request.get_json() or {}
        render_type = data.get('type', 'isometric')  # isometric, front, top, side
        resolution = data.get('resolution', 'high')  # low, medium, high
        include_dimensions = data.get('include_dimensions', True)
        
        step_analysis = analysis.get('step_analysis', {})
        file_path = analysis.get('file_path')
        
        # Render dosya adı
        timestamp = int(time.time())
        render_filename = f"render_{analysis_id}_{render_type}_{timestamp}.png"
        render_path = os.path.join("static", "renders", render_filename)
        os.makedirs(os.path.dirname(render_path), exist_ok=True)
        
        # Render oluştur
        if file_path and os.path.exists(file_path) and file_path.lower().endswith(('.step', '.stp')):
            # STEP dosyasından render
            from services.step_renderer import generate_step_views
            rendered_files = generate_step_views(file_path, views=[render_type], output_dir="static/renders")
            if rendered_files:
                # Dosyayı rename et
                import shutil
                shutil.move(rendered_files[0], render_path)
                success = True
            else:
                success = False
        else:
            # PDF analizi verilerinden render
            from services.pdf_3d_renderer import generate_pdf_3d_render
            rendered_files = generate_pdf_3d_render(step_analysis, "static/renders", [render_type])
            if rendered_files:
                shutil.move(rendered_files[0], render_path)
                success = True
            else:
                success = False
        
        if success:
            # Analiz kaydını güncelle
            renders = analysis.get('custom_renders', [])
            renders.append({
                "type": render_type,
                "path": render_path,
                "created_at": timestamp,
                "resolution": resolution
            })
            
            FileAnalysis.update_analysis(analysis_id, {"custom_renders": renders})
            
            return jsonify({
                "success": True,
                "message": "Render başarıyla oluşturuldu",
                "render_path": render_path,
                "render_url": f"/static/renders/{render_filename}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Render oluşturulamadı"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Render hatası: {str(e)}"
        }), 500

@upload_bp.route('/render/<analysis_id>', methods=['GET'])
@jwt_required()
def get_step_render(analysis_id):
    """STEP dosyası için render görüntüsü getir - UPDATED"""
    try:
        current_user = get_current_user()
        
        # Analiz kaydını bul
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        # İzometrik görünüm var mı kontrol et
        isometric_view = analysis.get('isometric_view')
        if isometric_view and os.path.exists(isometric_view):
            # Mevcut render'ı döndür
            return send_file(isometric_view, mimetype='image/png')
        
        # Yoksa yeni render oluştur
        try:
            model_service = Model3DService()
            result = model_service.generate_3d_views_from_analysis(
                analysis_id, 
                views=['isometric']
            )
            
            if result['success'] and result['views']:
                isometric_result = result['views'][0]
                if isometric_result['success'] and os.path.exists(isometric_result['file_path']):
                    return send_file(isometric_result['file_path'], mimetype='image/png')
            
            return jsonify({
                "success": False,
                "message": "Render oluşturulamadı"
            }), 500
            
        except Exception as render_error:
            return jsonify({
                "success": False,
                "message": f"Render oluşturma hatası: {str(render_error)}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Render hatası: {str(e)}"
        }), 500

@upload_bp.route('/3d-info/<analysis_id>', methods=['GET'])
@jwt_required()
def get_3d_info(analysis_id):
    """
    3D model bilgilerini getir - app.py benzeri
    """
    try:
        current_user = get_current_user()
        
        # Analiz kaydını bul
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        # 3D Model Service kullan
        model_service = Model3DService()
        info = model_service.get_analysis_3d_info(analysis_id)
        
        return jsonify({
            "success": True,
            "3d_info": info
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"3D bilgi hatası: {str(e)}"
        }), 500

@upload_bp.route('/3d-viewer/<analysis_id>', methods=['GET'])
@jwt_required()
def get_3d_viewer_page(analysis_id):
    """3D viewer sayfası için HTML döndür - UPDATED"""
    try:
        current_user = get_current_user()
        
        # Analiz kaydını kontrol et
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        # 3D viewer HTML'ini döndür
        viewer_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>3D Model Viewer - EngTeklif</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ margin: 0; overflow: hidden; background: #f0f0f0; }}
                iframe {{ width: 100vw; height: 100vh; border: none; }}
                .loading {{ 
                    position: absolute; top: 50%; left: 50%; 
                    transform: translate(-50%, -50%);
                    font-family: Arial, sans-serif;
                    color: #333;
                }}
            </style>
        </head>
        <body>
            <div class="loading">3D Model Yükleniyor...</div>
            <iframe src="/static/3d-viewer.html?analysis_id={analysis_id}&token={current_user['id']}" 
                    onload="document.querySelector('.loading').style.display='none'">
            </iframe>
        </body>
        </html>
        '''
        
        return Response(viewer_html, mimetype='text/html')
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"3D viewer hatası: {str(e)}"
        }), 500

# ===== EXISTING ENDPOINTS (unchanged) =====

@upload_bp.route('/status/<analysis_id>', methods=['GET'])
@jwt_required()
def get_analysis_status(analysis_id):
    """Analiz durumunu getir"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu analize erişim yetkiniz yok"
            }), 403
        
        return jsonify({
            "success": True,
            "analysis": analysis
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@upload_bp.route('/my-uploads', methods=['GET'])
@jwt_required()
def get_my_uploads():
    """Kullanıcının yüklediği dosyaları listele"""
    try:
        current_user = get_current_user()
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status', None, type=str)
        file_type = request.args.get('file_type', None, type=str)
        
        skip = (page - 1) * limit
        
        # Filtreleme
        if status:
            analyses = FileAnalysis.get_analyses_by_status(current_user['id'], status)
        elif file_type:
            analyses = FileAnalysis.get_analyses_by_file_type(current_user['id'], file_type)
        else:
            analyses = FileAnalysis.get_user_analyses(current_user['id'], limit, skip)
        
        total_count = FileAnalysis.get_user_analysis_count(current_user['id'])
        
        return jsonify({
            "success": True,
            "analyses": analyses,
            "pagination": {
                "current_page": page,
                "total_pages": (total_count + limit - 1) // limit,
                "total_items": total_count,
                "items_per_page": limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@upload_bp.route('/delete/<analysis_id>', methods=['DELETE'])
@jwt_required()
def delete_uploaded_file(analysis_id):
    """Yüklenmiş dosyayı sil"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyayı silme yetkiniz yok"
            }), 403
        
        # Fiziksel dosyayı sil
        if analysis.get('file_path') and os.path.exists(analysis['file_path']):
            try:
                os.remove(analysis['file_path'])
            except Exception as e:
                print(f"Dosya silinirken hata: {e}")
        
        # Render dosyasını sil
        if analysis.get('isometric_view') and os.path.exists(analysis['isometric_view']):
            try:
                os.remove(analysis['isometric_view'])
            except Exception as e:
                print(f"Render silinirken hata: {e}")
        
        # 3D model dosyalarını sil
        session_id = analysis.get('3d_session_id')
        if session_id:
            try:
                import glob
                pattern = os.path.join("static", f"model_{session_id}_*.png")
                model_files = glob.glob(pattern)
                for model_file in model_files:
                    os.remove(model_file)
                print(f"[INFO] {len(model_files)} 3D model dosyası silindi")
            except Exception as e:
                print(f"3D model dosyaları silinirken hata: {e}")
        
        # Veritabanından sil
        success = FileAnalysis.delete_analysis(analysis_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Dosya başarıyla silindi"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Dosya silinirken hata oluştu"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@upload_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """Desteklenen dosya formatları"""
    return jsonify({
        "success": True,
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "max_files_per_request": MAX_FILES_PER_REQUEST,
        "format_descriptions": {
            "pdf": "PDF dökümanları - Malzeme analizi ve gömülü STEP dosyaları için",
            "doc": "Microsoft Word belgeleri - Malzeme spesifikasyonları için",
            "docx": "Microsoft Word belgeleri (yeni format)",
            "step": "CAD STEP dosyaları - 3D geometrik analiz için",
            "stp": "CAD STEP dosyaları - 3D geometrik analiz için"
        },
        "analysis_capabilities": {
            "material_recognition": "Akıllı malzeme tanıma sistemi",
            "step_geometry": "3D geometrik analiz ve ölçüm",
            "cost_estimation": "Malzeme ve işçilik maliyet tahmini", 
            "ai_prediction": "AI destekli fiyat tahmini",
            "visual_rendering": "STEP dosyası görselleştirme",
            "all_material_calculations": "Bulunan malzemeler için detaylı hesaplama",
            "material_options": "Tüm mevcut malzemeler için karşılaştırma",
            "3d_visualization": "İnteraktif 3D model görüntüleme",
            "3d_model_generation": "Otomatik 3D model oluşturma",
            "wireframe_rendering": "Wireframe 3D görünüm"
        },
        "3d_features": {
            "isometric_view": "İzometrik görünüm oluşturma",
            "orthographic_views": "Ön, üst, yan görünümler",
            "wireframe_data": "3D viewer için wireframe data",
            "cylindrical_detection": "Silindirik geometri tanıma",
            "prismatic_detection": "Prizmatik geometri tanıma",
            "auto_generation": "Analiz sonrası otomatik model oluşturma"
        }
    }), 200

# ===== STATIC FILE SERVING =====

@upload_bp.route('/static/<path:filename>')
def serve_static_files(filename):
    """Static dosyaları serve et"""
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Static dosya hatası: {str(e)}"
        }), 404

# ===== UTILITY ENDPOINTS =====

@upload_bp.route('/cleanup-old-files', methods=['POST'])
@jwt_required()
def cleanup_old_files():
    """
    Eski render ve model dosyalarını temizle
    Sadece admin kullanıcılar için
    """
    try:
        current_user = get_current_user()
        
        # Admin kontrolü
        if current_user.get('role') != 'admin':
            return jsonify({
                "success": False,
                "message": "Bu işlem için admin yetkisi gerekli"
            }), 403
        
        data = request.get_json() or {}
        days_old = data.get('days_old', 7)
        
        # 3D Model Service kullan
        model_service = Model3DService()
        model_service.cleanup_old_renders(days_old)
        
        return jsonify({
            "success": True,
            "message": f"{days_old} günden eski dosyalar temizlendi"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Temizleme hatası: {str(e)}"
        }), 500

@upload_bp.route('/batch-generate-3d', methods=['POST'])
@jwt_required()
def batch_generate_3d():
    """
    Birden fazla analiz için toplu 3D model oluşturma
    """
    try:
        current_user = get_current_user()
        
        data = request.get_json()
        if not data or 'analysis_ids' not in data:
            return jsonify({
                "success": False,
                "message": "Analiz ID'leri gerekli"
            }), 400
        
        analysis_ids = data['analysis_ids']
        views = data.get('views', ['isometric'])
        
        if not isinstance(analysis_ids, list) or len(analysis_ids) == 0:
            return jsonify({
                "success": False,
                "message": "Geçerli analiz ID listesi gerekli"
            }), 400
        
        if len(analysis_ids) > 10:
            return jsonify({
                "success": False,
                "message": "Maksimum 10 analiz işlenebilir"
            }), 400
        
        model_service = Model3DService()
        results = []
        
        for analysis_id in analysis_ids:
            try:
                # Yetki kontrolü
                analysis = FileAnalysis.find_by_id(analysis_id)
                if not analysis or analysis['user_id'] != current_user['id']:
                    results.append({
                        "analysis_id": analysis_id,
                        "success": False,
                        "message": "Yetkisiz erişim veya analiz bulunamadı"
                    })
                    continue
                
                # 3D model oluştur
                result = model_service.generate_3d_views_from_analysis(analysis_id, views)
                results.append({
                    "analysis_id": analysis_id,
                    "success": result['success'],
                    "message": result['message'],
                    "views_count": len(result.get('views', []))
                })
                
            except Exception as e:
                results.append({
                    "analysis_id": analysis_id,
                    "success": False,
                    "message": f"Hata: {str(e)}"
                })
        
        successful_count = len([r for r in results if r['success']])
        
        return jsonify({
            "success": True,
            "message": f"{successful_count}/{len(analysis_ids)} analiz için 3D model oluşturuldu",
            "results": results,
            "summary": {
                "total_requested": len(analysis_ids),
                "successful": successful_count,
                "failed": len(analysis_ids) - successful_count
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Toplu 3D model oluşturma hatası: {str(e)}"
        }), 500
    

@upload_bp.route('/wireframe-data/<analysis_id>', methods=['GET'])
def get_wireframe_data_for_viewer(analysis_id):
    """3D viewer için wireframe data getir"""
    try:
        
        # Analiz kaydını bul
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        
        
        # STEP analizi kontrolü
        step_analysis = analysis.get('step_analysis', {})
        if not step_analysis:
            return jsonify({
                "success": False,
                "message": "STEP analizi mevcut değil"
            }), 404
        
        wireframe_data = None
        
        # 1. STEP dosyası varsa gerçek wireframe oluştur
        file_path = analysis.get('file_path')
        if file_path and os.path.exists(file_path) and file_path.lower().endswith(('.step', '.stp')):
            try:
                wireframe_data = create_step_wireframe_from_file(file_path)
                print(f"[SUCCESS] STEP dosyasından wireframe oluşturuldu: {analysis_id}")
            except Exception as step_error:
                print(f"[WARN] STEP wireframe hatası: {step_error}")
        
        # 2. STEP wireframe başarısızsa, analiz verilerinden oluştur
        if not wireframe_data and step_analysis:
            wireframe_data = create_wireframe_from_analysis_data(step_analysis)
            print(f"[SUCCESS] Analiz verilerinden wireframe oluşturuldu: {analysis_id}")
        
        if wireframe_data:
            return jsonify({
                "success": True,
                "wireframe_data": wireframe_data,
                "step_analysis": step_analysis,
                "material_info": {
                    "matches": analysis.get('material_matches', []),
                    "calculations": analysis.get('all_material_calculations', []),
                    "material_used": get_best_material_from_analysis(analysis)
                },
                "file_info": {
                    "original_filename": analysis.get('original_filename', ''),
                    "file_type": analysis.get('file_type', ''),
                    "analysis_method": step_analysis.get('method', 'unknown')
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Wireframe data oluşturulamadı"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Wireframe data hatası: {str(e)}"
        }), 500
    
@upload_bp.route('/3d-viewer-serve/<analysis_id>', methods=['GET'])
def serve_3d_viewer_page(analysis_id):
    """3D viewer HTML sayfasını döndür"""
    try:
        
        # Analiz kontrolü
        analysis = FileAnalysis.find_by_id(analysis_id)

        
        # 3D viewer HTML template
        viewer_html = f'''
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>3D Model Viewer - {analysis.get('original_filename', 'Model')}</title>
            <style>
                body {{ margin: 0; padding: 0; background: #1a1a1a; font-family: Arial, sans-serif; color: white; overflow: hidden; }}
                #viewer-container {{ width: 100vw; height: 100vh; position: relative; }}
                #loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; z-index: 1000; }}
                .controls {{ position: absolute; top: 20px; left: 20px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px; min-width: 250px; z-index: 1000; }}
                .info-panel {{ position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 8px; min-width: 200px; z-index: 1000; }}
                .btn {{ background: #4CAF50; color: white; border: none; padding: 6px 12px; border-radius: 4px; margin: 2px; cursor: pointer; font-size: 11px; }}
                .btn:hover {{ background: #45a049; }}
                .btn-danger {{ background: #f44336; }}
                input[type="range"], input[type="color"] {{ width: 100%; margin: 5px 0; }}
                .control-group {{ margin-bottom: 10px; }}
                .control-group label {{ display: block; font-size: 11px; margin-bottom: 3px; color: #ccc; }}
                #stats {{ font-size: 10px; color: #888; margin-top: 10px; }}
                .error {{ color: #f44336; text-align: center; padding: 20px; }}
            </style>
        </head>
        <body>
            <div id="viewer-container">
                <div id="loading">
                    <div style="font-size: 24px;">🔄</div>
                    <div>3D Model yükleniyor...</div>
                </div>
                
                <div class="controls">
                    <h4 style="margin-top: 0; color: #4CAF50;">🧊 3D Viewer</h4>
                    <div class="control-group">
                        <label>Wireframe Rengi:</label>
                        <input type="color" id="wireframeColor" value="#00ff88">
                    </div>
                    <div class="control-group">
                        <label>Çizgi Kalınlığı:</label>
                        <input type="range" id="lineWidth" min="1" max="5" value="2">
                    </div>
                    <div class="control-group">
                        <button class="btn" onclick="resetView()">🔄 Sıfırla</button>
                        <button class="btn" onclick="takeScreenshot()">📸 Screenshot</button>
                    </div>
                    <div class="control-group">
                        <button class="btn" onclick="toggleAutoRotate()">🔄 Otomatik Döndür</button>
                        <button class="btn btn-danger" onclick="window.close()">❌ Kapat</button>
                    </div>
                    <div id="stats">Vertices: 0<br>Edges: 0<br>Zoom: 1.0x</div>
                </div>
                
                <div class="info-panel">
                    <h4 style="margin-top: 0; color: #2196F3;">📊 Model Bilgileri</h4>
                    <div id="model-info">Yükleniyor...</div>
                </div>
            </div>

            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <script>
                let scene, camera, renderer, wireframeMesh;
                let controls = {{ autoRotate: false, rotationSpeed: 0.01 }};
                let modelData = null;
                const analysisId = '{analysis_id}';
                
                let mouseDown = false, targetRotationX = 0, targetRotationY = 0;
                let finalRotationX = 0, finalRotationY = 0;
                let mouseXOnMouseDown = 0, mouseYOnMouseDown = 0;
                let targetRotationOnMouseDownX = 0, targetRotationOnMouseDownY = 0;
                
                function init3D() {{
                    scene = new THREE.Scene();
                    scene.background = new THREE.Color(0x1a1a1a);
                    
                    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 2000);
                    camera.position.set(50, 50, 50);
                    
                    renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
                    renderer.setSize(window.innerWidth, window.innerHeight);
                    document.getElementById('viewer-container').appendChild(renderer.domElement);
                    
                    const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
                    scene.add(ambientLight);
                    
                    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6);
                    directionalLight.position.set(100, 100, 50);
                    scene.add(directionalLight);
                    
                    const gridHelper = new THREE.GridHelper(200, 20, 0x333333, 0x333333);
                    scene.add(gridHelper);
                    
                    const axesHelper = new THREE.AxesHelper(30);
                    scene.add(axesHelper);
                    
                    setupControls();
                    window.addEventListener('resize', onWindowResize);
                    animate();
                    loadModel();
                }}
                
                function setupControls() {{
                    const canvas = renderer.domElement;
                    canvas.addEventListener('mousedown', onMouseDown, false);
                    canvas.addEventListener('mouseup', () => mouseDown = false, false);
                    canvas.addEventListener('mousemove', onMouseMove, false);
                    canvas.addEventListener('wheel', onWheel, false);
                    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
                }}
                
                function onMouseDown(event) {{
                    event.preventDefault();
                    mouseDown = true;
                    mouseXOnMouseDown = event.clientX;
                    mouseYOnMouseDown = event.clientY;
                    targetRotationOnMouseDownX = targetRotationX;
                    targetRotationOnMouseDownY = targetRotationY;
                }}
                
                function onMouseMove(event) {{
                    if (!mouseDown) return;
                    const mouseX = event.clientX - mouseXOnMouseDown;
                    const mouseY = event.clientY - mouseYOnMouseDown;
                    targetRotationY = targetRotationOnMouseDownX + (mouseX * 0.02);
                    targetRotationX = targetRotationOnMouseDownY + (mouseY * 0.02);
                }}
                
                function onWheel(event) {{
                    event.preventDefault();
                    const scale = event.deltaY > 0 ? 1.1 : 0.9;
                    camera.position.multiplyScalar(scale);
                    camera.position.clampLength(10, 500);
                }}
                
                function onWindowResize() {{
                    camera.aspect = window.innerWidth / window.innerHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(window.innerWidth, window.innerHeight);
                }}
                
                async function loadModel() {{
                    try {{
                        const response = await fetch(`/api/upload/wireframe-data/${{analysisId}}`);
                        const data = await response.json();
                        
                        if (!data.success) throw new Error(data.message);
                        
                        modelData = data;
                        createWireframeModel(data.wireframe_data);
                        updateInfoPanel(data);
                        document.getElementById('loading').style.display = 'none';
                    }} catch (error) {{
                        document.getElementById('loading').innerHTML = `
                            <div class="error">
                                <div style="font-size: 24px;">❌</div>
                                <div>Model yüklenemedi</div>
                                <div style="font-size: 12px; margin-top: 10px;">${{error.message}}</div>
                            </div>
                        `;
                    }}
                }}
                
                function createWireframeModel(wireframeData) {{
                    if (!wireframeData?.vertices || !wireframeData?.edges) return;
                    
                    if (wireframeMesh) scene.remove(wireframeMesh);
                    
                    const geometry = new THREE.BufferGeometry();
                    const positions = [];
                    wireframeData.vertices.forEach(vertex => positions.push(vertex[0], vertex[1], vertex[2]));
                    
                    const indices = [];
                    wireframeData.edges.forEach(edge => indices.push(edge[0], edge[1]));
                    
                    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
                    geometry.setIndex(indices);
                    
                    const material = new THREE.LineBasicMaterial({{ 
                        color: document.getElementById('wireframeColor').value,
                        linewidth: parseInt(document.getElementById('lineWidth').value) || 2
                    }});
                    
                    wireframeMesh = new THREE.LineSegments(geometry, material);
                    scene.add(wireframeMesh);
                    
                    if (wireframeData.bounding_box) {{
                        const bbox = wireframeData.bounding_box;
                        const center = bbox.center || [0, 0, 0];
                        const maxDim = Math.max(...(bbox.dimensions || [100, 100, 100]));
                        camera.position.set(center[0] + maxDim, center[1] + maxDim, center[2] + maxDim);
                        camera.lookAt(center[0], center[1], center[2]);
                    }}
                }}
                
                function updateInfoPanel(data) {{
                    const stepAnalysis = data.step_analysis || {{}};
                    const materialInfo = data.material_info || {{}};
                    
                    let infoHTML = '';
                    if (stepAnalysis['X (mm)']) {{
                        infoHTML += `<strong>Boyutlar:</strong><br>`;
                        infoHTML += `X: ${{stepAnalysis['X (mm)']}} mm<br>`;
                        infoHTML += `Y: ${{stepAnalysis['Y (mm)']}} mm<br>`;
                        infoHTML += `Z: ${{stepAnalysis['Z (mm)']}} mm<br>`;
                    }}
                    if (stepAnalysis['Prizma Hacmi (mm³)']) {{
                        infoHTML += `Hacim: ${{Math.round(stepAnalysis['Prizma Hacmi (mm³)'])}} mm³<br><br>`;
                    }}
                    if (materialInfo.material_used) {{
                        infoHTML += `<strong>Malzeme:</strong><br>${{materialInfo.material_used}}<br>`;
                    }}
                    document.getElementById('model-info').innerHTML = infoHTML || 'Bilgi mevcut değil';
                }}
                
                function animate() {{
                    requestAnimationFrame(animate);
                    
                    finalRotationX += (targetRotationX - finalRotationX) * 0.1;
                    finalRotationY += (targetRotationY - finalRotationY) * 0.1;
                    
                    if (wireframeMesh) {{
                        wireframeMesh.rotation.x = finalRotationX;
                        wireframeMesh.rotation.y = finalRotationY;
                        if (controls.autoRotate) wireframeMesh.rotation.y += controls.rotationSpeed;
                    }}
                    
                    if (modelData?.wireframe_data) {{
                        const distance = camera.position.length();
                        const zoom = (100 / distance).toFixed(1);
                        document.getElementById('stats').innerHTML = `
                            Vertices: ${{modelData.wireframe_data.vertex_count}}<br>
                            Edges: ${{modelData.wireframe_data.edge_count}}<br>
                            Zoom: ${{zoom}}x
                        `;
                    }}
                    
                    renderer.render(scene, camera);
                }}
                
                function resetView() {{
                    targetRotationX = targetRotationY = finalRotationX = finalRotationY = 0;
                    if (wireframeMesh) wireframeMesh.rotation.set(0, 0, 0);
                    camera.position.set(50, 50, 50);
                    camera.lookAt(0, 0, 0);
                }}
                
                function toggleAutoRotate() {{ controls.autoRotate = !controls.autoRotate; }}
                
                function takeScreenshot() {{
                    const link = document.createElement('a');
                    link.download = `3d_model_${{analysisId}}.png`;
                    link.href = renderer.domElement.toDataURL();
                    link.click();
                }}
                
                document.getElementById('wireframeColor').addEventListener('change', function() {{
                    if (wireframeMesh) wireframeMesh.material.color.setStyle(this.value);
                }});
                
                document.getElementById('lineWidth').addEventListener('input', function() {{
                    if (wireframeMesh) wireframeMesh.material.linewidth = parseInt(this.value);
                }});
                
                document.addEventListener('DOMContentLoaded', init3D);
            </script>
        </body>
        </html>
        '''
        
        return Response(viewer_html, mimetype='text/html')
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"3D viewer hatası: {str(e)}"
        }), 500

def create_step_wireframe_from_file(step_path):
    """STEP dosyasından wireframe data oluştur"""
    try:
        import cadquery as cq
        
        assembly = cq.importers.importStep(step_path)
        if not assembly.objects:
            return None
        
        main_shape = max(assembly.objects, key=lambda s: s.Volume())
        
        # Edges'leri al
        vertices = []
        edges = []
        vertex_map = {}
        
        shape_edges = main_shape.Edges()
        
        for edge in shape_edges:
            try:
                start = edge.startPoint()
                end = edge.endPoint()
                
                # Start point
                start_key = f"{start.x:.3f},{start.y:.3f},{start.z:.3f}"
                if start_key not in vertex_map:
                    vertex_map[start_key] = len(vertices)
                    vertices.append([start.x, start.y, start.z])
                
                # End point  
                end_key = f"{end.x:.3f},{end.y:.3f},{end.z:.3f}"
                if end_key not in vertex_map:
                    vertex_map[end_key] = len(vertices)
                    vertices.append([end.x, end.y, end.z])
                
                # Edge
                edges.append([vertex_map[start_key], vertex_map[end_key]])
                
            except Exception as e:
                continue
        
        bbox = main_shape.BoundingBox()
        
        return {
            'vertices': vertices,
            'edges': edges,
            'vertex_count': len(vertices),
            'edge_count': len(edges),
            'bounding_box': {
                'min': [bbox.xmin, bbox.ymin, bbox.zmin],
                'max': [bbox.xmax, bbox.ymax, bbox.zmax],
                'center': [(bbox.xmin + bbox.xmax)/2, (bbox.ymin + bbox.ymax)/2, (bbox.zmin + bbox.zmax)/2],
                'dimensions': [bbox.xlen, bbox.ylen, bbox.zlen]
            },
            'source_type': 'step_file',
            'complexity': 'high' if len(edges) > 100 else 'medium' if len(edges) > 20 else 'low'
        }
        
    except Exception as e:
        print(f"[ERROR] STEP wireframe hatası: {e}")
        return None

def create_wireframe_from_analysis_data(step_analysis):
    """STEP analizi verilerinden wireframe oluştur"""
    try:
        if not step_analysis or step_analysis.get('error'):
            return None
        
        x = step_analysis.get("X (mm)", 50.0)
        y = step_analysis.get("Y (mm)", 30.0)
        z = step_analysis.get("Z (mm)", 20.0)
        
        # Silindirik kontrol
        cyl_diameter = step_analysis.get("Silindirik Çap (mm)")
        cyl_height = step_analysis.get("Silindirik Yükseklik (mm)")
        
        if cyl_diameter and cyl_height:
            return create_cylinder_wireframe(cyl_diameter, cyl_height)
        else:
            return create_box_wireframe(x, y, z)
            
    except Exception as e:
        print(f"[ERROR] Analysis wireframe hatası: {e}")
        return None

def create_box_wireframe(x, y, z):
    """Dikdörtgen prizma wireframe"""
    vertices = [
        [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],  # alt
        [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]   # üst
    ]
    
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # alt yüz
        [4, 5], [5, 6], [6, 7], [7, 4],  # üst yüz
        [0, 4], [1, 5], [2, 6], [3, 7]   # dikey kenarlar
    ]
    
    return {
        'vertices': vertices,
        'edges': edges,
        'vertex_count': len(vertices),
        'edge_count': len(edges),
        'bounding_box': {
            'min': [0, 0, 0],
            'max': [x, y, z],
            'center': [x/2, y/2, z/2],
            'dimensions': [x, y, z]
        },
        'source_type': 'analysis_box',
        'geometry_type': 'prismatic'
    }

def create_cylinder_wireframe(diameter, height):
    """Silindir wireframe"""
    radius = diameter / 2
    segments = 16
    vertices = []
    edges = []
    
    # Alt ve üst çember vertices
    for i in range(segments):
        angle = (i / segments) * 2 * math.pi
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        
        vertices.append([x, y, 0])        # Alt çember
        vertices.append([x, y, height])   # Üst çember
    
    # Edges
    for i in range(segments):
        next_i = (i + 1) % segments
        
        # Alt çember kenarları
        edges.append([i * 2, next_i * 2])
        # Üst çember kenarları
        edges.append([i * 2 + 1, next_i * 2 + 1])
        # Dikey kenarlar
        edges.append([i * 2, i * 2 + 1])
    
    return {
        'vertices': vertices,
        'edges': edges,
        'vertex_count': len(vertices),
        'edge_count': len(edges),
        'bounding_box': {
            'min': [-radius, -radius, 0],
            'max': [radius, radius, height],
            'center': [0, 0, height/2],
            'dimensions': [diameter, diameter, height]
        },
        'source_type': 'analysis_cylinder',
        'geometry_type': 'cylindrical'
    }

def get_best_material_from_analysis(analysis):
    """Analizden en iyi malzemeyi seç"""
    try:
        # Material matches varsa ilkini al
        material_matches = analysis.get('material_matches', [])
        if material_matches:
            return material_matches[0].split('(')[0].strip()
        
        # All material calculations varsa en ucuzunu al
        calculations = analysis.get('all_material_calculations', [])
        if calculations:
            best = min(calculations, key=lambda x: x.get('material_cost', float('inf')))
            return best.get('material', 'Bilinmiyor')
        
        return 'Bilinmiyor'
        
    except Exception as e:
        return 'Bilinmiyor'
