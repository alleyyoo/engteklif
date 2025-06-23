# controllers/file_upload_controller.py - COMPLETE WITH STEP RENDERER INTEGRATION

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
from services.step_renderer import StepRendererEnhanced
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

# ===== UPLOAD ENDPOINTS =====

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

# ===== ANALYSIS ENDPOINTS =====

@upload_bp.route('/analyze/<analysis_id>', methods=['POST'])
@jwt_required()
def analyze_uploaded_file(analysis_id):
    """✅ ENHANCED - Yüklenmiş dosyayı analiz et + STEP viewer entegrasyonu"""
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
        
        # ✅ Material Analysis Service kullan
        try:
            material_service = MaterialAnalysisService()
            
            print(f"[ANALYSIS] 🔍 Enhanced analiz başlatılıyor: {analysis['file_type']} - {analysis['original_filename']}")
            
            # Kapsamlı analiz
            if analysis['file_type'] in ['pdf', 'document', 'step']:
                result = material_service.analyze_document_comprehensive(
                    analysis['file_path'], 
                    analysis['file_type'],
                    current_user['id']
                )
                
                print(f"[ANALYSIS] 📊 Material analysis tamamlandı - Success: {not result.get('error')}")
                
                analysis_success = not result.get('error')
                
                if analysis_success:
                    processing_time = time.time() - start_time
                    
                    # ✅ STEP DOSYASI İÇİN STL OLUŞTUR
                    if analysis['file_type'] in ['step', 'stp']:
                        stl_result = create_stl_for_step_analysis(analysis['file_path'], analysis_id)
                        if stl_result['success']:
                            result['stl_generated'] = True
                            result['stl_path'] = stl_result['stl_path']
                            result['stl_url'] = stl_result['stl_url']
                            print(f"[ANALYSIS] ✅ STEP için STL oluşturuldu: {stl_result['stl_path']}")
                    
                    # PDF'den çıkarılan STEP için STL
                    elif analysis['file_type'] == 'pdf' and result.get('step_file_hash'):
                        # PDF'den çıkarılan kalıcı STEP dosyasını kullan
                        if result.get('extracted_step_path') and os.path.exists(result['extracted_step_path']):
                            stl_result = create_stl_for_step_analysis(result['extracted_step_path'], analysis_id)
                            if stl_result['success']:
                                result['stl_generated'] = True
                                result['stl_path'] = stl_result['stl_path']
                                result['stl_url'] = stl_result['stl_url']
                                print(f"[ANALYSIS] ✅ PDF-STEP için STL oluşturuldu: {stl_result['stl_path']}")
                        else:
                            print(f"[ANALYSIS] ⚠️ PDF-STEP dosyası bulunamadı: {result.get('extracted_step_path')}")
                    
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
                        "processing_log": result.get('processing_log', []),
                        "all_material_calculations": result.get('all_material_calculations', []),
                        "material_options": result.get('material_options', []),
                        "isometric_view": result.get('isometric_view'),
                        "isometric_view_clean": result.get('isometric_view_clean'),
                        "enhanced_renders": result.get('enhanced_renders', {}),
                        "step_file_hash": result.get('step_file_hash'),
                        "render_quality": "high" if result.get('enhanced_renders') else "none",
                        "stl_path": result.get('stl_path'),
                        "stl_generated": result.get('stl_generated', False)
                    }
                    
                    # PDF özel alanlar
                    if analysis['file_type'] == 'pdf':
                        update_data["pdf_step_extracted"] = bool(result.get('step_file_hash'))
                        update_data["pdf_rotation_count"] = result.get('rotation_count', 0)
                        update_data["extracted_step_path"] = result.get('extracted_step_path')
                        update_data["pdf_analysis_id"] = result.get('pdf_analysis_id')
                    
                    FileAnalysis.update_analysis(analysis_id, update_data)
                    
                    # Güncellenmiş analizi döndür
                    updated_analysis = FileAnalysis.find_by_id(analysis_id)
                    
                    # ✅ STEP viewer bilgilerini ekle
                    step_viewer_info = {}
                    if result.get('stl_generated'):
                        step_viewer_info = {
                            "viewer_url": f"/step-viewer/{analysis_id}",
                            "stl_ready": True,
                            "stl_path": result.get('stl_path'),
                            "stl_url": result.get('stl_url')
                        }
                    elif analysis['file_type'] == 'step' or (analysis['file_type'] == 'pdf' and result.get('step_file_hash')):
                        step_viewer_info = {
                            "viewer_url": f"/step-viewer/{analysis_id}",
                            "stl_ready": False,
                            "note": "STL henüz oluşturulmamış, otomatik oluşturulacak"
                        }
                    
                    response_data = {
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
                            "excel_friendly_render": bool(result.get('isometric_view_clean')),
                            "pdf_step_extracted": analysis['file_type'] == 'pdf' and bool(result.get('step_file_hash')),
                            "step_file_hash": result.get('step_file_hash'),
                            "pdf_rotation_attempts": result.get('rotation_count', 0),
                            "stl_generated": result.get('stl_generated', False)
                        }
                    }
                    
                    # ✅ STEP viewer bilgilerini response'a ekle
                    if step_viewer_info:
                        response_data["step_viewer"] = step_viewer_info
                    
                    return jsonify(response_data), 200
                    
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
            
            print(f"[ANALYSIS] ❌ Analiz hatası: {error_message}")
            import traceback
            print(f"[ANALYSIS] 📋 Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "success": False,
                "message": error_message,
                "traceback": traceback.format_exc()
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
            
        print(f"[ANALYSIS] ❌ Beklenmeyen hata: {str(e)}")
        import traceback
        print(f"[ANALYSIS] 📋 Traceback: {traceback.format_exc()}")
            
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen analiz hatası: {str(e)}"
        }), 500

# ===== ENHANCED STATUS AND MANAGEMENT ENDPOINTS =====


# ===== RENDER ENDPOINTS =====

@upload_bp.route('/render/<analysis_id>', methods=['POST'])
@jwt_required()
def generate_step_render(analysis_id):
    """STEP dosyası için render oluştur"""
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
        
        # STEP dosyası kontrolü
        if analysis['file_type'] not in ['step', 'stp']:
            return jsonify({
                "success": False,
                "message": "Sadece STEP dosyaları için render oluşturulabilir"
            }), 400
        
        # Dosya varlık kontrolü
        if not os.path.exists(analysis['file_path']):
            return jsonify({
                "success": False,
                "message": "STEP dosyası sistemde bulunamadı"
            }), 404
        
        # Render parametrelerini al
        request_data = request.get_json() or {}
        include_dimensions = request_data.get('include_dimensions', True)
        include_materials = request_data.get('include_materials', True)
        high_quality = request_data.get('high_quality', True)
        
        print(f"[STEP-RENDER] 🎨 Render isteği: {analysis_id}")
        
        # Step Renderer'ı kullan
        step_renderer = StepRendererEnhanced()
        
        render_result = step_renderer.generate_comprehensive_views(
            analysis['file_path'],
            analysis_id=analysis_id,
            include_dimensions=include_dimensions,
            include_materials=include_materials,
            high_quality=high_quality
        )
        
        if render_result['success']:
            # Analiz kaydını güncelle
            update_data = {
                "enhanced_renders": render_result['renders'],
                "render_quality": "high" if high_quality else "standard"
            }
            
            # Ana isometric view'ı ekle
            if 'isometric' in render_result['renders']:
                update_data["isometric_view"] = render_result['renders']['isometric']['file_path']
                if 'excel_path' in render_result['renders']['isometric']:
                    update_data["isometric_view_clean"] = render_result['renders']['isometric']['excel_path']
            
            FileAnalysis.update_analysis(analysis_id, update_data)
            
            return jsonify({
                "success": True,
                "message": "Render başarıyla oluşturuldu",
                "renders": render_result['renders'],
                "session_id": render_result['session_id'],
                "dimensions": render_result['dimensions'],
                "total_views": render_result['total_views']
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": f"Render oluşturma başarısız: {render_result.get('message', 'Bilinmeyen hata')}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Render hatası: {str(e)}"
        }), 500

@upload_bp.route('/wireframe/<analysis_id>', methods=['GET'])
@jwt_required()
def get_wireframe_view(analysis_id):
    """STEP dosyası için wireframe görünümü"""
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
        
        # Enhanced renders kontrolü
        enhanced_renders = analysis.get('enhanced_renders', {})
        if 'wireframe' in enhanced_renders and enhanced_renders['wireframe'].get('success'):
            wireframe_data = enhanced_renders['wireframe']
            return jsonify({
                "success": True,
                "wireframe": wireframe_data,
                "analysis_id": analysis_id
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Wireframe görünümü mevcut değil. Önce render oluşturun."
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Wireframe hatası: {str(e)}"
        }), 500

@upload_bp.route('/3d-viewer/<analysis_id>', methods=['GET'])
@jwt_required()
def get_3d_viewer_data(analysis_id):
    """3D viewer için analiz verilerini getir"""
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
        
        # 3D viewer verilerini hazırla
        viewer_data = {
            "analysis_id": analysis_id,
            "filename": analysis.get('original_filename', 'Unknown'),
            "file_type": analysis.get('file_type'),
            "step_analysis": analysis.get('step_analysis', {}),
            "material_matches": analysis.get('material_matches', []),
            "enhanced_renders": analysis.get('enhanced_renders', {}),
            "dimensions": {},
            "available_views": []
        }
        
        # Boyutları step_analysis'ten al
        step_data = analysis.get('step_analysis', {})
        if step_data and not step_data.get('error'):
            viewer_data["dimensions"] = {
                "width": step_data.get('X (mm)', 0),
                "height": step_data.get('Y (mm)', 0),
                "depth": step_data.get('Z (mm)', 0),
                "volume": step_data.get('Prizma Hacmi (mm³)', 0)
            }
        
        # Mevcut görünümleri listele
        enhanced_renders = analysis.get('enhanced_renders', {})
        for view_name, view_data in enhanced_renders.items():
            if view_data.get('success') and view_data.get('file_path'):
                viewer_data["available_views"].append({
                    "name": view_name,
                    "type": view_data.get('view_type', view_name),
                    "file_path": view_data['file_path'],
                    "svg_path": view_data.get('svg_path'),
                    "excel_path": view_data.get('excel_path')
                })
        
        return jsonify({
            "success": True,
            "viewer_data": viewer_data,
            "has_3d_data": len(viewer_data["available_views"]) > 0
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"3D viewer veri hatası: {str(e)}"
        }), 500

# ===== STATUS AND MANAGEMENT ENDPOINTS =====

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
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        # Kullanıcı yetkisi kontrolü
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        return jsonify({
            "success": True,
            "analysis": {
                "id": analysis['id'],
                "status": analysis.get('analysis_status', 'unknown'),
                "filename": analysis.get('original_filename'),
                "file_type": analysis.get('file_type'),
                "processing_time": analysis.get('processing_time'),
                "error_message": analysis.get('error_message'),
                "created_at": analysis.get('created_at'),
                "updated_at": analysis.get('updated_at'),
                "has_step_analysis": bool(analysis.get('step_analysis')),
                "has_renders": bool(analysis.get('enhanced_renders')),
                "material_matches_count": len(analysis.get('material_matches', [])),
                "render_count": len(analysis.get('enhanced_renders', {}))
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Durum sorgulama hatası: {str(e)}"
        }), 500

@upload_bp.route('/my-uploads', methods=['GET'])
@jwt_required()
def get_my_uploads():
    """Kullanıcının yüklemelerini getir"""
    try:
        current_user = get_current_user()
        
        # Query parametreleri
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        file_type = request.args.get('file_type', '', type=str)
        status = request.args.get('status', '', type=str)
        
        skip = (page - 1) * limit
        
        # Kullanıcının analizlerini getir
        analyses = FileAnalysis.get_user_analyses(current_user['id'], limit, skip)
        total_count = FileAnalysis.get_user_analysis_count(current_user['id'])
        
        # Filtrele
        if file_type:
            analyses = [a for a in analyses if a.get('file_type') == file_type]
        if status:
            analyses = [a for a in analyses if a.get('analysis_status') == status]
        
        # Özet bilgiler ekle
        for analysis in analyses:
            analysis['summary'] = {
                "has_step_analysis": bool(analysis.get('step_analysis')),
                "has_renders": bool(analysis.get('enhanced_renders')),
                "material_count": len(analysis.get('material_matches', [])),
                "render_count": len(analysis.get('enhanced_renders', {})),
                "processing_time_formatted": f"{analysis.get('processing_time', 0):.2f}s" if analysis.get('processing_time') else "N/A"
            }
        
        return jsonify({
            "success": True,
            "uploads": analyses,
            "pagination": {
                "current_page": page,
                "total_pages": (total_count + limit - 1) // limit,
                "total_items": total_count,
                "items_per_page": limit
            },
            "filters_applied": {
                "file_type": file_type or None,
                "status": status or None
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Yüklemeler getirilemedi: {str(e)}"
        }), 500

@upload_bp.route('/delete/<analysis_id>', methods=['DELETE'])
@jwt_required()
def delete_analysis(analysis_id):
    """Analizi sil"""
    try:
        current_user = get_current_user()
        
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
                "message": "Bu dosyayı silme yetkiniz yok"
            }), 403
        
        # Dosyaları sil
        try:
            if analysis.get('file_path') and os.path.exists(analysis['file_path']):
                os.remove(analysis['file_path'])
            
            # Render dosyalarını sil
            enhanced_renders = analysis.get('enhanced_renders', {})
            for view_name, view_data in enhanced_renders.items():
                if view_data.get('file_path'):
                    file_path = os.path.join(os.getcwd(), view_data['file_path'])
                    if os.path.exists(file_path):
                        os.remove(file_path)
        except Exception as file_error:
            print(f"[WARN] Dosya silme hatası: {file_error}")
        
        # Veritabanından sil
        success = FileAnalysis.delete_analysis(analysis_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Analiz başarıyla silindi"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Analiz silinirken hata oluştu"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Silme hatası: {str(e)}"
        }), 500

# ===== UTILITY ENDPOINTS =====

@upload_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """Desteklenen dosya formatları"""
    return jsonify({
        "success": True,
        "supported_formats": {
            "upload": list(ALLOWED_EXTENSIONS),
            "analysis": {
                "pdf": "PDF doküman analizi ve malzeme tanıma",
                "doc": "Word doküman analizi",
                "docx": "Word doküman analizi", 
                "step": "3D STEP dosya analizi ve rendering",
                "stp": "3D STEP dosya analizi ve rendering"
            }
        },
        "limits": {
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "max_files_per_request": MAX_FILES_PER_REQUEST
        },
        "features": {
            "material_recognition": True,
            "3d_rendering": True,
            "cost_estimation": True,
            "wireframe_generation": True,
            "technical_drawings": True,
            "excel_export": True
        }
    }), 200

@upload_bp.route('/download/<analysis_id>/<view_type>', methods=['GET'])
@jwt_required()
def download_render(analysis_id, view_type):
    """Render dosyasını indir"""
    try:
        current_user = get_current_user()
        
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
        
        # Render dosyasını bul
        enhanced_renders = analysis.get('enhanced_renders', {})
        if view_type not in enhanced_renders:
            return jsonify({
                "success": False,
                "message": f"'{view_type}' görünümü bulunamadı"
            }), 404
        
        render_data = enhanced_renders[view_type]
        if not render_data.get('success') or not render_data.get('file_path'):
            return jsonify({
                "success": False,
                "message": f"'{view_type}' dosyası mevcut değil"
            }), 404
        
        file_path = os.path.join(os.getcwd(), render_data['file_path'])
        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "message": "Dosya sistemde bulunamadı"
            }), 404
        
        # Dosyayı indir
        filename = f"{analysis.get('original_filename', 'render')}_{view_type}.png"
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='image/png'
        )
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"İndirme hatası: {str(e)}"
        }), 500

@upload_bp.route('/export-excel/<analysis_id>', methods=['GET'])
@jwt_required()
def export_analysis_excel(analysis_id):
    """✅ ENHANCED - Analiz sonuçlarını Excel'e aktar (resimlerle birlikte)"""
    try:
        current_user = get_current_user()
        
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
        
        try:
            import pandas as pd
            import io
            from datetime import datetime
            import os
            
            # ✅ STEP ANALİZİ VERİLERİNİ TOPLA
            step_analysis = analysis.get('step_analysis', {})
            
            # ✅ MALZEME BİLGİSİNİ BELİRLE
            material_matches = analysis.get('material_matches', [])
            material_name = "Bilinmiyor"
            
            if material_matches:
                # İlk malzeme eşleşmesinden isim çıkar
                first_match = material_matches[0]
                if isinstance(first_match, str) and "(" in first_match:
                    material_name = first_match.split("(")[0].strip()
                elif isinstance(first_match, str):
                    material_name = first_match
            
            # Alternatif: material_used alanından al
            if analysis.get('material_used'):
                material_name = analysis['material_used']
            
            # ✅ EXCEL SATIRI OLUŞTUR (app.py benzeri)
            data = {
                "Ürün Görseli": "",  # Resim için boş bırak
                "Ürün Kodu": analysis.get('product_code', 'N/A'),
                "Dosya Adı": analysis.get('original_filename', 'N/A'),
                "Dosya Türü": analysis.get('file_type', 'N/A'),
                "Hammadde": material_name,
                "X+Pad (mm)": step_analysis.get('X+Pad (mm)', 0),
                "Y+Pad (mm)": step_analysis.get('Y+Pad (mm)', 0),
                "Z+Pad (mm)": step_analysis.get('Z+Pad (mm)', 0),
                "Silindirik Çap (mm)": step_analysis.get('Silindirik Çap (mm)', 0),
                "Ürün Hacmi (mm³)": step_analysis.get('Ürün Hacmi (mm³)', 0),
                "Toplam Yüzey Alanı (mm²)": step_analysis.get('Toplam Yüzey Alanı (mm²)', 0),
                "Hammadde Maliyeti (USD)": analysis.get('material_cost', 0),
                "Kütle (kg)": analysis.get('calculated_mass', 0),
                "Analiz Durumu": analysis.get('analysis_status', 'N/A'),
                "İşleme Süresi (s)": analysis.get('processing_time', 0),
                "Oluşturma Tarihi": analysis.get('created_at', 'N/A')
            }
            
            # Malzeme detayını ekle (varsa)
            if analysis.get('malzeme_detay'):
                data["Malzeme Eşleşmeleri"] = analysis['malzeme_detay']
            
            # ✅ RESİM YOLUNU BUL
            image_path = None
            enhanced_renders = analysis.get('enhanced_renders', {})
            
            # İzometrik görünüm varsa kullan
            if 'isometric' in enhanced_renders and enhanced_renders['isometric'].get('file_path'):
                image_path = enhanced_renders['isometric']['file_path']
            elif analysis.get('isometric_view_clean'):
                image_path = analysis['isometric_view_clean']
            elif analysis.get('isometric_view'):
                image_path = analysis['isometric_view']
            
            # Görsel yolunu tam path'e çevir
            if image_path:
                if image_path.startswith('/'):
                    image_path = image_path[1:]  # Baştaki / işaretini kaldır
                if not image_path.startswith('static'):
                    image_path = os.path.join('static', image_path)
                
                full_image_path = os.path.join(os.getcwd(), image_path)
                
                # Dosya var mı kontrol et
                if not os.path.exists(full_image_path):
                    print(f"[EXPORT] ⚠️ Görsel dosyası bulunamadı: {full_image_path}")
                    image_path = None
                else:
                    print(f"[EXPORT] ✅ Görsel bulundu: {full_image_path}")
            
            # ✅ DATAFRAME OLUŞTUR
            df = pd.DataFrame([data])
            
            # ✅ EXCEL ÇIKTISI (xlsxwriter ile)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Ana sayfayı yaz (header'ı manuel olarak yazacağız)
                df.to_excel(writer, sheet_name='Analiz Sonuçları', index=False, header=False, startrow=1)
                
                workbook = writer.book
                worksheet = writer.sheets['Analiz Sonuçları']
                
                # ✅ SÜTUN GENİŞLİKLERİNİ AYARLA
                worksheet.set_column("A:A", 30)  # Görsel sütunu geniş
                worksheet.set_column("B:B", 20)  # Ürün Kodu
                worksheet.set_column("C:C", 25)  # Dosya Adı
                worksheet.set_column("D:D", 15)  # Dosya Türü
                worksheet.set_column("E:E", 20)  # Hammadde
                worksheet.set_column("F:Z", 18)  # Diğer sütunlar
                
                # ✅ HEADER STİLİ
                header_format = workbook.add_format({
                    "bold": True,
                    "text_wrap": True,
                    "valign": "top",
                    "fg_color": "#D7E4BC",
                    "border": 1
                })
                
                # Header'ları yaz
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # ✅ RESMİ EKLE
                if image_path and os.path.exists(full_image_path):
                    # Satır yüksekliğini artır
                    worksheet.set_row(1, 120)
                    
                    try:
                        # Resmi ekle (app.py ile aynı ayarlar)
                        worksheet.insert_image("A2", full_image_path, {
                            "x_scale": 0.4,
                            "y_scale": 0.4,
                            "x_offset": 45,
                            "y_offset": 35
                        })
                        print(f"[EXPORT] ✅ Resim Excel'e eklendi: {image_path}")
                    except Exception as img_error:
                        print(f"[EXPORT] ❌ Resim ekleme hatası: {img_error}")
                
                # ✅ EK SAYFALAR
                # Malzeme seçenekleri sayfası
                material_options = analysis.get('material_options', [])
                if material_options:
                    material_df = pd.DataFrame(material_options)
                    material_df.to_excel(writer, sheet_name='Malzeme Seçenekleri', index=False)
                
                # Enhanced renders sayfası
                if enhanced_renders:
                    renders_data = []
                    for view_name, view_data in enhanced_renders.items():
                        if view_data.get('success'):
                            renders_data.append({
                                "Görünüm": view_name,
                                "Dosya Yolu": view_data.get('file_path', ''),
                                "Başarılı": view_data.get('success', False),
                                "Format": view_data.get('format', 'png')
                            })
                    
                    if renders_data:
                        renders_df = pd.DataFrame(renders_data)
                        renders_df.to_excel(writer, sheet_name='3D Görünümler', index=False)
            
            output.seek(0)
            
            # ✅ DOSYA ADI OLUŞTUR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analiz_{analysis_id}_{timestamp}.xlsx"
            
            print(f"[EXPORT] ✅ Excel dosyası hazır: {filename}")
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except ImportError:
            return jsonify({
                "success": False,
                "message": "Excel export için pandas ve xlsxwriter gerekli"
            }), 500
        except Exception as excel_error:
            print(f"[EXPORT] ❌ Excel oluşturma hatası: {excel_error}")
            import traceback
            print(f"[EXPORT] 📋 Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "success": False,
                "message": f"Excel oluşturma hatası: {str(excel_error)}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Excel export hatası: {str(e)}"
        }), 500

@upload_bp.route('/search', methods=['GET'])
@jwt_required()
def search_analyses():
    """Analizlerde arama yap"""
    try:
        current_user = get_current_user()
        
        # Query parametreleri
        search_term = request.args.get('q', '', type=str)
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        if not search_term or len(search_term.strip()) < 2:
            return jsonify({
                "success": False,
                "message": "Arama terimi en az 2 karakter olmalı"
            }), 400
        
        # Arama yap
        results = FileAnalysis.search_analyses(current_user['id'], search_term.strip())
        
        # Pagination
        total = len(results)
        start = (page - 1) * limit
        end = start + limit
        paginated_results = results[start:end]
        
        # Özet bilgiler ekle
        for result in paginated_results:
            result['search_relevance'] = {
                "filename_match": search_term.lower() in result.get('original_filename', '').lower(),
                "material_match": any(search_term.lower() in m.lower() for m in result.get('material_matches', [])),
                "file_type_match": search_term.lower() == result.get('file_type', '').lower()
            }
        
        return jsonify({
            "success": True,
            "search_results": paginated_results,
            "search_term": search_term,
            "pagination": {
                "current_page": page,
                "total_pages": (total + limit - 1) // limit,
                "total_items": total,
                "items_per_page": limit
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Arama hatası: {str(e)}"
        }), 500

# ===== ADVANCED FEATURES =====

@upload_bp.route('/batch-analyze', methods=['POST'])
@jwt_required()
def batch_analyze():
    """Toplu dosya analizi"""
    try:
        current_user = get_current_user()
        
        data = request.get_json()
        if not data or 'analysis_ids' not in data:
            return jsonify({
                "success": False,
                "message": "Analiz ID'leri gerekli"
            }), 400
        
        analysis_ids = data['analysis_ids']
        if not isinstance(analysis_ids, list) or len(analysis_ids) == 0:
            return jsonify({
                "success": False,
                "message": "Geçerli analiz ID listesi gerekli"
            }), 400
        
        if len(analysis_ids) > 10:
            return jsonify({
                "success": False,
                "message": "Maksimum 10 dosya aynı anda analiz edilebilir"
            }), 400
        
        results = []
        for analysis_id in analysis_ids:
            try:
                # Her analiz için analyze endpoint'ini çağır
                analysis = FileAnalysis.find_by_id(analysis_id)
                if analysis and analysis['user_id'] == current_user['id']:
                    # Analiz durumunu kontrol et
                    if analysis['analysis_status'] in ['uploaded', 'failed']:
                        # Analizi başlat (async olarak implement edilebilir)
                        results.append({
                            "analysis_id": analysis_id,
                            "status": "queued",
                            "filename": analysis.get('original_filename')
                        })
                    else:
                        results.append({
                            "analysis_id": analysis_id,
                            "status": "already_processed",
                            "filename": analysis.get('original_filename')
                        })
                else:
                    results.append({
                        "analysis_id": analysis_id,
                        "status": "not_found_or_unauthorized",
                        "filename": None
                    })
            except Exception as e:
                results.append({
                    "analysis_id": analysis_id,
                    "status": "error",
                    "error": str(e),
                    "filename": None
                })
        
        return jsonify({
            "success": True,
            "message": f"{len(analysis_ids)} dosya için toplu analiz başlatıldı",
            "results": results,
            "queued_count": len([r for r in results if r['status'] == 'queued'])
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Toplu analiz hatası: {str(e)}"
        }), 500

@upload_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_user_statistics():
    """Kullanıcının dosya istatistikleri"""
    try:
        current_user = get_current_user()
        
        # Kullanıcının tüm analizlerini al
        all_analyses = FileAnalysis.get_user_analyses(current_user['id'], limit=1000)
        
        # İstatistikleri hesapla
        stats = {
            "total_files": len(all_analyses),
            "by_status": {},
            "by_file_type": {},
            "total_processing_time": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "files_with_renders": 0,
            "total_materials_found": 0
        }
        
        for analysis in all_analyses:
            # Durum istatistikleri
            status = analysis.get('analysis_status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Dosya türü istatistikleri
            file_type = analysis.get('file_type', 'unknown')
            stats['by_file_type'][file_type] = stats['by_file_type'].get(file_type, 0) + 1
            
            # İşleme süresi
            processing_time = analysis.get('processing_time', 0)
            if processing_time:
                stats['total_processing_time'] += processing_time
            
            # Başarı oranları
            if status == 'completed':
                stats['successful_analyses'] += 1
            elif status == 'failed':
                stats['failed_analyses'] += 1
            
            # Render sayısı
            if analysis.get('enhanced_renders'):
                stats['files_with_renders'] += 1
            
            # Malzeme sayısı
            materials = analysis.get('material_matches', [])
            stats['total_materials_found'] += len(materials)
        
        # Ortalamalar
        stats['average_processing_time'] = stats['total_processing_time'] / max(1, stats['successful_analyses'])
        stats['success_rate'] = (stats['successful_analyses'] / max(1, stats['total_files'])) * 100
        
        return jsonify({
            "success": True,
            "statistics": stats,
            "user_id": current_user['id']
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"İstatistik hatası: {str(e)}"
        }), 500
    
@upload_bp.route('/generate-stl/<analysis_id>', methods=['POST'])
@jwt_required()
def generate_stl_for_analysis(analysis_id):
    """Analiz için STL dosyası oluştur"""
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
        
        # STEP dosyası kontrolü
        if analysis['file_type'] not in ['step', 'stp']:
            # PDF'den çıkarılan STEP kontrolü
            if not (analysis['file_type'] == 'pdf' and analysis.get('step_file_hash')):
                return jsonify({
                    "success": False,
                    "message": "Bu analiz için STEP dosyası bulunamadı"
                }), 400
        
        # STEP dosya yolunu bul
        step_path = None
        
        if analysis['file_type'] in ['step', 'stp']:
            # Direkt STEP dosyası
            step_path = analysis['file_path']
        else:
            # PDF'den çıkarılan STEP dosyasını kullan
            if analysis.get('extracted_step_path'):
                step_path = analysis['extracted_step_path']
                print(f"[STL-GEN] 📄 PDF'den çıkarılan STEP kullanılıyor: {step_path}")
            else:
                # Fallback: PDF analysis ID varsa o dizinde ara
                if analysis.get('pdf_analysis_id'):
                    pdf_dir = os.path.join("static", "stepviews", analysis['pdf_analysis_id'])
                    if os.path.exists(pdf_dir):
                        for file in os.listdir(pdf_dir):
                            if file.endswith(('.step', '.stp')):
                                step_path = os.path.join(pdf_dir, file)
                                print(f"[STL-GEN] 📂 PDF dizininde STEP bulundu: {step_path}")
                                break
        
        if not step_path or not os.path.exists(step_path):
            return jsonify({
                "success": False,
                "message": "STEP dosyası bulunamadı"
            }), 404
        
        print(f"[STL-GEN] 🔧 STL oluşturuluyor: {analysis_id}")
        
        # StepRendererEnhanced kullan
        step_renderer = StepRendererEnhanced()
        
        # Session output directory
        session_output_dir = os.path.join("static", "stepviews", analysis_id)
        os.makedirs(session_output_dir, exist_ok=True)
        
        # STL dosya yolu
        stl_filename = f"model_{analysis_id}.stl"
        stl_path_full = os.path.join(session_output_dir, stl_filename)
        
        try:
            # CadQuery ile STEP'i import et ve STL olarak export et
            import cadquery as cq
            from cadquery import exporters
            
            # STEP dosyasını yükle
            assembly = cq.importers.importStep(step_path)
            shape = assembly.val()
            
            # STL olarak export et
            exporters.export(shape, stl_path_full)
            
            # Dosya boyutunu kontrol et
            if os.path.exists(stl_path_full):
                file_size = os.path.getsize(stl_path_full)
                print(f"[STL-GEN] ✅ STL oluşturuldu: {stl_filename} ({file_size} bytes)")
                
                # Analiz kaydını güncelle
                stl_relative = f"/static/stepviews/{analysis_id}/{stl_filename}"
                
                update_data = {
                    "stl_generated": True,
                    "stl_path": stl_relative,
                    "stl_file_size": file_size
                }
                
                # Enhanced renders'a ekle
                if not analysis.get('enhanced_renders'):
                    analysis['enhanced_renders'] = {}
                
                analysis['enhanced_renders']['stl_model'] = {
                    "success": True,
                    "file_path": stl_relative,
                    "file_size": file_size,
                    "format": "stl"
                }
                
                FileAnalysis.update_analysis(analysis_id, {
                    "enhanced_renders": analysis['enhanced_renders'],
                    "stl_generated": True,
                    "stl_path": stl_relative
                })
                
                return jsonify({
                    "success": True,
                    "message": "STL dosyası başarıyla oluşturuldu",
                    "stl_path": stl_relative,
                    "stl_url": stl_relative,
                    "file_size": file_size,
                    "viewer_url": f"/step-viewer/{analysis_id}"
                }), 200
            else:
                raise Exception("STL dosyası oluşturulamadı")
                
        except Exception as stl_error:
            print(f"[STL-GEN] ❌ STL oluşturma hatası: {stl_error}")
            return jsonify({
                "success": False,
                "message": f"STL oluşturma hatası: {str(stl_error)}"
            }), 500
        
    except Exception as e:
        print(f"[STL-GEN] ❌ Beklenmeyen hata: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@upload_bp.route('/model-3d/<analysis_id>', methods=['GET'])
@jwt_required()
def get_3d_model_info(analysis_id):
    """3D model bilgilerini getir"""
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
        
        # 3D model bilgilerini topla
        model_info = {
            "analysis_id": analysis_id,
            "has_step": analysis['file_type'] in ['step', 'stp'] or (analysis['file_type'] == 'pdf' and analysis.get('step_file_hash')),
            "is_pdf_with_step": analysis['file_type'] == 'pdf' and analysis.get('step_file_hash'),
            "step_analysis": analysis.get('step_analysis', {}),
            "models_available": {}
        }
        
        # STL kontrolü
        stl_path = f"static/stepviews/{analysis_id}/model_{analysis_id}.stl"
        if os.path.exists(stl_path):
            model_info["models_available"]["stl"] = {
                "path": f"/{stl_path}",
                "size": os.path.getsize(stl_path),
                "ready": True
            }
        else:
            # PDF için özel kontrol
            if analysis['file_type'] == 'pdf' and analysis.get('pdf_analysis_id'):
                # PDF analysis dizininde STL kontrolü
                pdf_stl_path = f"static/stepviews/{analysis['pdf_analysis_id']}/model_{analysis['pdf_analysis_id']}.stl"
                if os.path.exists(pdf_stl_path):
                    model_info["models_available"]["stl"] = {
                        "path": f"/{pdf_stl_path}",
                        "size": os.path.getsize(pdf_stl_path),
                        "ready": True,
                        "from_pdf": True
                    }
                else:
                    model_info["models_available"]["stl"] = {
                        "ready": False,
                        "generate_endpoint": f"/api/upload/generate-stl/{analysis_id}",
                        "note": "PDF'den çıkarılan STEP için STL oluşturulabilir"
                    }
            else:
                model_info["models_available"]["stl"] = {
                    "ready": False,
                    "generate_endpoint": f"/api/upload/generate-stl/{analysis_id}"
                }
        
        # STEP dosya bilgisi
        if analysis.get('extracted_step_path'):
            model_info["extracted_step"] = {
                "path": analysis['extracted_step_path'],
                "exists": os.path.exists(analysis['extracted_step_path'])
            }
        
        # Viewer URL'leri
        model_info["viewer_urls"] = {
            "direct": f"/step-viewer/{analysis_id}",
            "with_token": f"/step-viewer/{analysis_id}/{{access_token}}"
        }
        
        # Render bilgileri
        if analysis.get('enhanced_renders'):
            model_info["renders_available"] = len(analysis['enhanced_renders'])
            model_info["render_types"] = list(analysis['enhanced_renders'].keys())
        
        return jsonify({
            "success": True,
            "model_info": model_info
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Model bilgisi hatası: {str(e)}"
        }), 500
    
def create_stl_for_step_analysis(step_path, analysis_id):
    """STEP dosyasından STL oluştur"""
    try:
        import cadquery as cq
        from cadquery import exporters
        
        # Session output directory
        session_output_dir = os.path.join("static", "stepviews", analysis_id)
        os.makedirs(session_output_dir, exist_ok=True)
        
        # STL dosya yolu
        stl_filename = f"model_{analysis_id}.stl"
        stl_path_full = os.path.join(session_output_dir, stl_filename)
        
        # STEP dosyasını yükle
        assembly = cq.importers.importStep(step_path)
        shape = assembly.val()
        
        # STL olarak export et
        exporters.export(shape, stl_path_full)
        
        # Dosya boyutunu kontrol et
        if os.path.exists(stl_path_full):
            file_size = os.path.getsize(stl_path_full)
            stl_relative = f"/static/stepviews/{analysis_id}/{stl_filename}"
            
            print(f"[STL-CREATE] ✅ STL oluşturuldu: {stl_filename} ({file_size} bytes)")
            
            return {
                "success": True,
                "stl_path": stl_relative,
                "stl_url": stl_relative,
                "file_size": file_size
            }
        else:
            return {
                "success": False,
                "error": "STL dosyası oluşturulamadı"
            }
            
    except Exception as e:
        print(f"[STL-CREATE] ❌ STL oluşturma hatası: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@upload_bp.route('/merge-with-excel', methods=['POST'])
@jwt_required()
def merge_with_excel():
    """✅ GÜNCELLENMIŞ - Excel dosyasını analiz sonuçlarıyla birleştir"""
    try:
        current_user = get_current_user()
        
        # Form verilerini kontrol et
        if 'excel_file' not in request.files:
            return jsonify({
                "success": False,
                "message": "Excel dosyası bulunamadı"
            }), 400
        
        excel_file = request.files['excel_file']
        analysis_ids = request.form.getlist('analysis_ids')  # Çoklu analiz ID'si
        
        if excel_file.filename == '':
            return jsonify({
                "success": False,
                "message": "Excel dosyası seçilmedi"
            }), 400
        
        if not analysis_ids:
            return jsonify({
                "success": False,
                "message": "Analiz ID'leri belirtilmedi"
            }), 400
        
        print(f"[MERGE-API] 📊 Excel birleştirme başlıyor: {excel_file.filename}")
        print(f"[MERGE-API] 🔢 Analiz ID'leri: {analysis_ids}")
        
        # Excel dosyası kontrolü
        if not excel_file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                "success": False,
                "message": "Sadece Excel dosyaları (.xlsx, .xls) desteklenir"
            }), 400
        
        # Analizleri yükle ve yetki kontrolü
        analyses = []
        for analysis_id in analysis_ids:
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis:
                return jsonify({
                    "success": False,
                    "message": f"Analiz bulunamadı: {analysis_id}"
                }), 404
            
            if analysis['user_id'] != current_user['id']:
                return jsonify({
                    "success": False,
                    "message": f"Analiz erişim yetkisi yok: {analysis_id}"
                }), 403
            
            analyses.append(analysis)
        
        print(f"[MERGE-API] ✅ {len(analyses)} analiz yüklendi")
        
        # Excel işleme
        try:
            import openpyxl
            from openpyxl.drawing.image import Image as XLImage
            from openpyxl.styles import Alignment, PatternFill, Border, Side, Font
            import re
            import math
            import io
            from datetime import datetime
            
            # ✅ EXCEL DOSYASINI YÜKLEYİN
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active
            print(f"[MERGE-API] ✅ Excel yüklendi. Satır: {ws.max_row}, Sütun: {ws.max_column}")
            
            # ✅ GELİŞTİRİLMİŞ NORMALIZE FONKSİYONU
            def normalize_robust(text):
                """Güvenli ve kapsamlı normalize fonksiyonu"""
                if not text:
                    return ""
                
                if not isinstance(text, str):
                    text = str(text)
                
                # Türkçe karakterleri çevir
                replacements = {
                    'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
                    'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
                }
                for tr_char, en_char in replacements.items():
                    text = text.replace(tr_char, en_char)
                
                # Sadece sayı ve harf bırak, küçük harfe çevir
                normalized = re.sub(r'[^\w]', '', text.lower())
                return normalized
            
            def extract_numbers(text):
                """Metinden sayıları çıkar"""
                if not text:
                    return []
                numbers = re.findall(r'\d+', str(text))
                return numbers
            
            # ✅ HEADER ANALİZİ VE SÜTUN TESPİTİ
            header_row = [ws.cell(row=1, column=col).value for col in range(1, ws.max_column + 1)]
            print(f"[MERGE-API] 📋 Header satırı: {header_row}")
            
            # Malzeme No sütununu bul (daha kapsamlı arama)
            malzeme_no_patterns = [
                "malzeme no", "malzemeno", "malzeme_no", "malzeme numarası", "malzeme numarasi",
                "ürün kodu", "urun kodu", "ürün no", "urun no", "kod", "no", "part", "item"
            ]
            
            malzeme_col_index = None
            for i, header in enumerate(header_row):
                if header:
                    normalized_header = normalize_robust(header)
                    print(f"[MERGE-API] 🔍 Header {i+1}: '{header}' -> '{normalized_header}'")
                    
                    for pattern in malzeme_no_patterns:
                        if normalize_robust(pattern) == normalized_header:
                            malzeme_col_index = i + 1  # 1-based
                            print(f"[MERGE-API] ✅ Malzeme No sütunu: '{header}' (sütun {malzeme_col_index})")
                            break
                    if malzeme_col_index:
                        break
            
            if not malzeme_col_index:
                # Fallback: üçüncü sütun genelde malzeme no'dur
                malzeme_col_index = 3
                print(f"[MERGE-API] ⚠️ Malzeme No sütunu bulunamadı, sütun {malzeme_col_index} kullanılıyor")
            
            # İhale miktarı sütununu bul
            ihale_col_index = None
            ihale_patterns = ["ihale", "miktar", "adet", "quantity", "amount"]
            
            for i, header in enumerate(header_row):
                if header:
                    normalized_header = normalize_robust(header)
                    for pattern in ihale_patterns:
                        if pattern in normalized_header:
                            ihale_col_index = i + 1
                            print(f"[MERGE-API] ✅ İhale sütunu: '{header}' (sütun {ihale_col_index})")
                            break
                    if ihale_col_index:
                        break
            
            if not ihale_col_index:
                # İhale sütununu malzeme no'dan sonraki ilk sütun olarak varsay
                ihale_col_index = malzeme_col_index + 1
                print(f"[MERGE-API] ⚠️ İhale sütunu bulunamadı, sütun {ihale_col_index} kullanılıyor")
            
            # ✅ İHALE SÜTUNUNDAN SONRAKİ SÜTUNLARI SİL
            columns_to_keep = ihale_col_index
            columns_to_delete = ws.max_column - columns_to_keep
            
            for _ in range(columns_to_delete):
                if ws.max_column > columns_to_keep:
                    ws.delete_cols(columns_to_keep + 1)
            
            print(f"[MERGE-API] 🗑️ {columns_to_delete} sütun silindi")
            
            # ✅ YENİ SÜTUN BAŞLIKLARI EKLE
            new_headers = [
                "Ürün Görseli", "Hammadde", "X+Pad (mm)", "Y+Pad (mm)", "Z+Pad (mm)",
                "Silindirik Çap (mm)", "Kütle (kg)", "Hammadde Maliyeti (USD)",
                "Kaplama", "Helicoil", "Markalama", "İşçilik", "Birim Fiyat", "Toplam"
            ]
            
            start_col = columns_to_keep + 1
            for i, header in enumerate(new_headers):
                ws.cell(row=1, column=start_col + i, value=header)
            
            # ✅ SÜTUN GENİŞLİKLERİ
            for i in range(len(new_headers)):
                col_letter = openpyxl.utils.get_column_letter(start_col + i)
                if i == 0:  # Görsel sütunu
                    ws.column_dimensions[col_letter].width = 25
                else:
                    ws.column_dimensions[col_letter].width = 14
            
            # ✅ ANALİZ VERİLERİNİ LOOKUP TABLOSU HAZİRLA
            analysis_lookup = {}
            
            for analysis in analyses:
                # ✅ PRODUCT CODE ÇIKARMA STRATEJİLERİ
                product_codes = []
                
                # 1. Direkt product_code alanından
                if analysis.get('product_code'):
                    product_codes.append(str(analysis['product_code']))
                
                # 2. Filename'den rakam çıkarma
                filename = analysis.get('original_filename', '')
                if filename:
                    # Başından rakam çıkar
                    front_numbers = re.findall(r'^\d+', filename)
                    if front_numbers:
                        product_codes.append(front_numbers[0])
                    
                    # Tüm rakamları çıkar
                    all_numbers = re.findall(r'\d+', filename)
                    product_codes.extend(all_numbers)
                
                # 3. Analysis ID'yi de ekle
                product_codes.append(str(analysis.get('id', '')))
                
                # Benzersiz kodları normalize et ve ekle
                for code in set(product_codes):
                    if code and len(code) >= 3:  # En az 3 karakter
                        normalized_code = normalize_robust(code)
                        if normalized_code:
                            analysis_lookup[normalized_code] = analysis
                            print(f"[MERGE-API] 📝 Lookup eklendi: '{code}' -> '{normalized_code}' -> {analysis['id']}")
            
            print(f"[MERGE-API] 📋 Toplam lookup entries: {len(analysis_lookup)}")
            
            # ✅ SATIRLARI İŞLE VE EŞLEŞTİR
            matched_count = 0
            total_rows = 0
            
            for row in range(2, ws.max_row + 1):
                total_rows += 1
                
                # Excel'den malzeme numarasını al
                malzeme_cell = ws.cell(row=row, column=malzeme_col_index).value
                
                if not malzeme_cell:
                    print(f"[MERGE-API] ⚠️ Satır {row}: Malzeme numarası boş")
                    continue
                
                excel_malzeme = str(malzeme_cell).strip()
                print(f"[MERGE-API] 🔍 Satır {row}: Excel malzeme = '{excel_malzeme}'")
                
                # ✅ EŞLEŞMEYİ BUL
                matched_analysis = None
                match_method = ""
                
                # 1. Tam eşleşme
                excel_normalized = normalize_robust(excel_malzeme)
                if excel_normalized in analysis_lookup:
                    matched_analysis = analysis_lookup[excel_normalized]
                    match_method = "exact"
                
                # 2. Kısmi eşleşme (başından)
                if not matched_analysis:
                    for lookup_code, analysis in analysis_lookup.items():
                        if excel_normalized.startswith(lookup_code) or lookup_code.startswith(excel_normalized):
                            if len(lookup_code) >= 4:  # Minimum güvenlik
                                matched_analysis = analysis
                                match_method = "partial_start"
                                break
                
                # 3. Sayısal eşleşme
                if not matched_analysis:
                    excel_numbers = extract_numbers(excel_malzeme)
                    for lookup_code, analysis in analysis_lookup.items():
                        lookup_numbers = extract_numbers(lookup_code)
                        if excel_numbers and lookup_numbers:
                            # En büyük sayıları karşılaştır
                            if max(excel_numbers) == max(lookup_numbers):
                                matched_analysis = analysis
                                match_method = "numeric"
                                break
                
                # ✅ EŞLEŞME BULUNURSA VERİLERİ YAZ
                if matched_analysis:
                    matched_count += 1
                    print(f"[MERGE-API] ✅ Satır {row}: '{excel_malzeme}' eşleşti -> {matched_analysis['id']} ({match_method})")
                    
                    # ✅ ANALİZ VERİLERİNİ DEBUG ET
                    print(f"[MERGE-API] 🔍 Analiz debug {matched_analysis['id']}:")
                    print(f"   - calculated_mass: {matched_analysis.get('calculated_mass')}")
                    print(f"   - material_cost: {matched_analysis.get('material_cost')}")
                    print(f"   - cost_estimation: {matched_analysis.get('cost_estimation')}")
                    print(f"   - ai_price_prediction: {matched_analysis.get('ai_price_prediction')}")
                    print(f"   - step_analysis keys: {list(matched_analysis.get('step_analysis', {}).keys())}")
                    
                    # ✅ ANALİZ VERİLERİNİ HAZIRLA
                    step_analysis = matched_analysis.get('step_analysis', {})
                    
                    # Malzeme bilgisi
                    material_matches = matched_analysis.get('material_matches', [])
                    material_name = matched_analysis.get('material_used', 'Bilinmiyor')
                    
                    if not material_name or material_name == 'Bilinmiyor':
                        if material_matches:
                            first_match = material_matches[0]
                            if isinstance(first_match, str) and "(" in first_match:
                                material_name = first_match.split("(")[0].strip()
                            else:
                                material_name = str(first_match)
                    
                    # ✅ DEĞERLER - GELİŞTİRİLMİŞ VERİ ÇIKARTMA
                    
                    # Kütle hesaplama - çoklu kaynak
                    kutle_kg = 0
                    if matched_analysis.get("calculated_mass"):
                        kutle_kg = matched_analysis["calculated_mass"]
                    elif step_analysis.get("Kütle (kg)"):
                        kutle_kg = step_analysis["Kütle (kg)"]
                    elif step_analysis.get("Mass (kg)"):
                        kutle_kg = step_analysis["Mass (kg)"]
                    elif step_analysis.get("Ağırlık (kg)"):
                        kutle_kg = step_analysis["Ağırlık (kg)"]
                    
                    # Maliye hesaplama - çoklu kaynak
                    maliyet_usd = 0
                    if matched_analysis.get("material_cost"):
                        maliyet_usd = matched_analysis["material_cost"]
                    elif matched_analysis.get("cost_estimation", {}).get("total_cost_usd"):
                        maliyet_usd = matched_analysis["cost_estimation"]["total_cost_usd"]
                    elif matched_analysis.get("ai_price_prediction", {}).get("predicted_price_usd"):
                        maliyet_usd = matched_analysis["ai_price_prediction"]["predicted_price_usd"]
                    
                    # Cost estimation verilerinden ek maliyetler
                    cost_est = matched_analysis.get("cost_estimation", {})
                    ai_price = matched_analysis.get("ai_price_prediction", {})
                    
                    # İşçilik maliyeti hesaplama
                    iscilik_usd = 0
                    if cost_est.get("labor_cost_usd"):
                        iscilik_usd = cost_est["labor_cost_usd"]
                    elif ai_price.get("labor_cost_usd"):
                        iscilik_usd = ai_price["labor_cost_usd"]
                    
                    # Birim fiyat hesaplama (hammadde + işçilik)
                    birim_fiyat = maliyet_usd + iscilik_usd
                    
                    # İhale miktarını al (Toplam hesaplama için)
                    ihale_miktari = 1  # Default
                    ihale_cell = ws.cell(row=row, column=ihale_col_index).value
                    if ihale_cell:
                        try:
                            # Virgülü noktaya çevir ve sayıya dönüştür
                            ihale_str = str(ihale_cell).replace(',', '.')
                            ihale_miktari = float(ihale_str)
                        except:
                            ihale_miktari = 1
                    
                    # Toplam hesaplama
                    toplam_maliyet = birim_fiyat * ihale_miktari
                    
                    values_data = [
                        None,  # Görsel (sonra eklenecek)
                        material_name,
                        step_analysis.get("X+Pad (mm)", 0) or step_analysis.get("X (mm)", 0),
                        step_analysis.get("Y+Pad (mm)", 0) or step_analysis.get("Y (mm)", 0),
                        step_analysis.get("Z+Pad (mm)", 0) or step_analysis.get("Z (mm)", 0),
                        step_analysis.get("Silindirik Çap (mm)", 0) or step_analysis.get("Çap (mm)", 0),
                        kutle_kg if kutle_kg > 0 else None,
                        maliyet_usd if maliyet_usd > 0 else None,
                        "",  # Kaplama - boş bırak
                        "",  # Helicoil - boş bırak
                        "",  # Markalama - boş bırak
                        iscilik_usd if iscilik_usd > 0 else "",  # İşçilik
                        birim_fiyat if birim_fiyat > 0 else "",  # Birim Fiyat
                        toplam_maliyet if toplam_maliyet > 0 else ""   # Toplam
                    ]
                    
                    print(f"[MERGE-API] 📊 Satır {row} değerler:")
                    print(f"   - Kütle: {kutle_kg} kg")
                    print(f"   - Hammadde Maliyeti: ${maliyet_usd}")
                    print(f"   - İşçilik: ${iscilik_usd}")
                    print(f"   - Birim Fiyat: ${birim_fiyat}")
                    print(f"   - İhale Miktarı: {ihale_miktari}")
                    print(f"   - Toplam: ${toplam_maliyet}")
                    
                    # ✅ SATIR YÜKSEKLİĞİNİ AYARLA
                    ws.row_dimensions[row].height = 120
                    
                    # ✅ VERİLERİ HÜCRELERE YAZ
                    for i, value in enumerate(values_data):
                        target_col = start_col + i
                        target_cell = ws.cell(row=row, column=target_col)
                        
                        if i == 0:  # Görsel sütunu
                            # ✅ GÖRSELİ BUL VE EKLE
                            image_path = None
                            enhanced_renders = matched_analysis.get('enhanced_renders', {})
                            
                            # Görsel kaynak önceliği
                            if 'isometric' in enhanced_renders and enhanced_renders['isometric'].get('file_path'):
                                image_path = enhanced_renders['isometric']['file_path']
                            elif matched_analysis.get('isometric_view_clean'):
                                image_path = matched_analysis['isometric_view_clean']
                            elif matched_analysis.get('isometric_view'):
                                image_path = matched_analysis['isometric_view']
                            
                            if image_path:
                                # Path'i düzelt
                                if image_path.startswith('/'):
                                    image_path = image_path[1:]
                                if not image_path.startswith('static'):
                                    image_path = os.path.join('static', image_path)
                                
                                full_image_path = os.path.join(os.getcwd(), image_path)
                                
                                if os.path.exists(full_image_path):
                                    try:
                                        img = XLImage(full_image_path)
                                        
                                        # Güvenli boyutlandırma
                                        max_width = 160
                                        max_height = 100
                                        
                                        if img.width > 0 and img.height > 0:
                                            # Aspect ratio koru
                                            width_ratio = max_width / img.width
                                            height_ratio = max_height / img.height
                                            scale_ratio = min(width_ratio, height_ratio)
                                            
                                            img.width = int(img.width * scale_ratio)
                                            img.height = int(img.height * scale_ratio)
                                        
                                        # Hücre koordinatını hesapla
                                        cell_coord = f"{openpyxl.utils.get_column_letter(target_col)}{row}"
                                        ws.add_image(img, cell_coord)
                                        
                                        print(f"[MERGE-API] 🖼️ Satır {row}: Resim eklendi ({img.width}x{img.height})")
                                        
                                    except Exception as img_error:
                                        print(f"[MERGE-API] ❌ Satır {row} resim hatası: {img_error}")
                                        target_cell.value = "Resim Hatası"
                                else:
                                    print(f"[MERGE-API] ⚠️ Satır {row}: Resim dosyası bulunamadı: {full_image_path}")
                                    target_cell.value = "Resim Bulunamadı"
                            else:
                                target_cell.value = "Resim Yok"
                        else:
                            # Sayısal değerleri formatla ve yaz
                            if isinstance(value, (float, int)) and value is not None:
                                if value != 0:  # Sıfır değerleri yazma
                                    if isinstance(value, float):
                                        # Para birimi sütunları için 2 decimal
                                        if i in [7, 11, 12, 13]:  # Maliyet, İşçilik, Birim Fiyat, Toplam
                                            target_cell.value = round(value, 2)
                                            target_cell.number_format = '#,##0.00'
                                        # Kütle için 3 decimal
                                        elif i == 6:  # Kütle
                                            target_cell.value = round(value, 3)
                                            target_cell.number_format = '#,##0.000'
                                        # Boyutlar için 1 decimal
                                        elif i in [2, 3, 4, 5]:  # Boyutlar
                                            target_cell.value = round(value, 1)
                                            target_cell.number_format = '#,##0.0'
                                        else:
                                            target_cell.value = round(value, 2)
                                    else:
                                        target_cell.value = value
                                        if i in [7, 11, 12, 13]:  # Para sütunları
                                            target_cell.number_format = '#,##0.00'
                            elif value and str(value).strip():  # Boş olmayan string değerler
                                target_cell.value = str(value).strip()
                        
                        # Hücre hizalaması
                        target_cell.alignment = Alignment(
                            horizontal='center',
                            vertical='center',
                            wrap_text=True
                        )
                
                else:
                    print(f"[MERGE-API] ❌ Satır {row}: '{excel_malzeme}' eşleşmedi")
            
            print(f"[MERGE-API] 📊 İşlem tamamlandı: {matched_count}/{total_rows} eşleşme")
            
            # ✅ HEADER STİLLENDİRME
            header_fill = PatternFill(start_color="D7E4BC", end_color="D7E4BC", fill_type="solid")
            header_font = Font(bold=True)
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for col in range(1, ws.max_column + 1):
                header_cell = ws.cell(row=1, column=col)
                header_cell.fill = header_fill
                header_cell.font = header_font
                header_cell.border = border
                header_cell.alignment = Alignment(
                    horizontal='center',
                    vertical='center',
                    wrap_text=True
                )
            
            # ✅ DOSYAYI KAYDET VE DÖNDÜR
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            # Dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = excel_file.filename.rsplit('.', 1)[0]
            filename = f"{original_name}_merged_{timestamp}.xlsx"
            
            print(f"[MERGE-API] ✅ Excel başarıyla birleştirildi: {filename}")
            print(f"[MERGE-API] 📈 Sonuç: {matched_count}/{total_rows} satır eşleşti")
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except ImportError as e:
            missing_lib = str(e).split("'")[1] if "'" in str(e) else str(e)
            return jsonify({
                "success": False,
                "message": f"Gerekli kütüphane bulunamadı: {missing_lib}. pip install {missing_lib} çalıştırın."
            }), 500
        except Exception as excel_error:
            print(f"[MERGE-API] ❌ Excel işleme hatası: {excel_error}")
            import traceback
            print(f"[MERGE-API] 📋 Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "success": False,
                "message": f"Excel işleme hatası: {str(excel_error)}",
                "details": traceback.format_exc()
            }), 500
    
    except Exception as e:
        print(f"[MERGE-API] ❌ Genel hata: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": f"Birleştirme hatası: {str(e)}"
        }), 500

    
# file_upload_controller.py içine eklenecek yeni endpoint

@upload_bp.route('/export-excel-multiple', methods=['POST'])
@jwt_required()
def export_multiple_analyses_excel():
    """✅ YENİ - Birden fazla analizi Excel'e aktar (resimlerle birlikte)"""
    try:
        current_user = get_current_user()
        
        # Request body'den analysis_ids array'ini al
        data = request.get_json()
        if not data or 'analysis_ids' not in data:
            return jsonify({
                "success": False,
                "message": "analysis_ids array gerekli"
            }), 400
        
        analysis_ids = data['analysis_ids']
        if not isinstance(analysis_ids, list) or len(analysis_ids) == 0:
            return jsonify({
                "success": False,
                "message": "Geçerli analysis_ids array gerekli"
            }), 400
        
        if len(analysis_ids) > 50:  # Güvenlik limiti
            return jsonify({
                "success": False,
                "message": "Maksimum 50 analiz aynı anda export edilebilir"
            }), 400
        
        print(f"[EXCEL-MULTI] 📊 Çoklu Excel export başlıyor: {len(analysis_ids)} analiz")
        
        # Analizleri yükle ve yetki kontrolü
        analyses = []
        not_found = []
        unauthorized = []
        
        for analysis_id in analysis_ids:
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis:
                not_found.append(analysis_id)
                continue
            
            if analysis['user_id'] != current_user['id']:
                unauthorized.append(analysis_id)
                continue
            
            analyses.append(analysis)
        
        # Hata kontrolü
        if not_found:
            return jsonify({
                "success": False,
                "message": f"Bulunamayan analizler: {', '.join(not_found)}"
            }), 404
        
        if unauthorized:
            return jsonify({
                "success": False,
                "message": f"Yetkisiz erişim: {', '.join(unauthorized)}"
            }), 403
        
        if not analyses:
            return jsonify({
                "success": False,
                "message": "Export edilecek geçerli analiz bulunamadı"
            }), 400
        
        try:
            import pandas as pd
            import io
            from datetime import datetime
            import os
            
            print(f"[EXCEL-MULTI] ✅ {len(analyses)} analiz işlenecek")
            
            # ✅ TÜM ANALİZLER İÇİN VERİ HAZIRLA
            excel_data = []
            
            for analysis in analyses:
                # ✅ STEP ANALİZİ VERİLERİNİ TOPLA
                step_analysis = analysis.get('step_analysis', {})
                
                # ✅ MALZEME BİLGİSİNİ BELİRLE
                material_matches = analysis.get('material_matches', [])
                material_name = "Bilinmiyor"
                
                if material_matches:
                    # İlk malzeme eşleşmesinden isim çıkar
                    first_match = material_matches[0]
                    if isinstance(first_match, str) and "(" in first_match:
                        material_name = first_match.split("(")[0].strip()
                    elif isinstance(first_match, str):
                        material_name = first_match
                
                # Alternatif: material_used alanından al
                if analysis.get('material_used'):
                    material_name = analysis['material_used']
                
                # ✅ EXCEL SATIRI OLUŞTUR
                row_data = {
                    "Ürün Görseli": "",  # Resim için boş bırak - sonra eklenecek
                    "Analiz ID": analysis.get('id', 'N/A'),
                    "Dosya Adı": analysis.get('original_filename', 'N/A'),
                    "Dosya Türü": analysis.get('file_type', 'N/A'),
                    "Hammadde": material_name,
                    "X+Pad (mm)": step_analysis.get('X+Pad (mm)', 0),
                    "Y+Pad (mm)": step_analysis.get('Y+Pad (mm)', 0),
                    "Z+Pad (mm)": step_analysis.get('Z+Pad (mm)', 0),
                    "Silindirik Çap (mm)": step_analysis.get('Silindirik Çap (mm)', 0),
                    "Ürün Hacmi (mm³)": step_analysis.get('Ürün Hacmi (mm³)', 0),
                    "Toplam Yüzey Alanı (mm²)": step_analysis.get('Toplam Yüzey Alanı (mm²)', 0),
                    "Hammadde Maliyeti (USD)": analysis.get('material_cost', 0),
                    "Kütle (kg)": analysis.get('calculated_mass', 0),
                    "Analiz Durumu": analysis.get('analysis_status', 'N/A'),
                    "İşleme Süresi (s)": analysis.get('processing_time', 0),
                    "Oluşturma Tarihi": analysis.get('created_at', 'N/A')
                }
                
                # Malzeme detayını ekle (varsa)
                if analysis.get('malzeme_detay'):
                    row_data["Malzeme Eşleşmeleri"] = analysis['malzeme_detay']
                
                # ✅ RESİM YOLUNU BUL VE EKLE
                image_path = None
                enhanced_renders = analysis.get('enhanced_renders', {})
                
                # İzometrik görünüm varsa kullan
                if 'isometric' in enhanced_renders and enhanced_renders['isometric'].get('file_path'):
                    image_path = enhanced_renders['isometric']['file_path']
                elif analysis.get('isometric_view_clean'):
                    image_path = analysis['isometric_view_clean']
                elif analysis.get('isometric_view'):
                    image_path = analysis['isometric_view']
                
                # Görsel yolunu tam path'e çevir
                full_image_path = None
                if image_path:
                    if image_path.startswith('/'):
                        image_path = image_path[1:]  # Baştaki / işaretini kaldır
                    if not image_path.startswith('static'):
                        image_path = os.path.join('static', image_path)
                    
                    full_image_path = os.path.join(os.getcwd(), image_path)
                    
                    # Dosya var mı kontrol et
                    if not os.path.exists(full_image_path):
                        print(f"[EXCEL-MULTI] ⚠️ Görsel dosyası bulunamadı: {full_image_path}")
                        full_image_path = None
                    else:
                        print(f"[EXCEL-MULTI] ✅ Görsel bulundu: {full_image_path}")
                
                # Row data'ya image path'i ekle (Excel'de kullanılacak)
                row_data["_image_path"] = full_image_path
                
                excel_data.append(row_data)
            
            # ✅ DATAFRAME OLUŞTUR
            df = pd.DataFrame(excel_data)
            
            # _image_path sütununu DataFrame'den çıkar (sadne internal kullanım için)
            image_paths = df["_image_path"].tolist()
            df = df.drop(columns=["_image_path"])
            
            print(f"[EXCEL-MULTI] 📋 DataFrame oluşturuldu: {len(df)} satır")
            
            # ✅ EXCEL ÇIKTISI (xlsxwriter ile)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Ana sayfayı yaz (header'ı manuel olarak yazacağız)
                df.to_excel(writer, sheet_name='Analiz Sonuçları', index=False, header=False, startrow=1)
                
                workbook = writer.book
                worksheet = writer.sheets['Analiz Sonuçları']
                
                # ✅ SÜTUN GENİŞLİKLERİNİ AYARLA
                worksheet.set_column("A:A", 30)  # Görsel sütunu geniş
                worksheet.set_column("B:B", 15)  # Analiz ID
                worksheet.set_column("C:C", 25)  # Dosya Adı
                worksheet.set_column("D:D", 15)  # Dosya Türü
                worksheet.set_column("E:E", 20)  # Hammadde
                worksheet.set_column("F:Z", 18)  # Diğer sütunlar
                
                # ✅ HEADER STİLİ
                header_format = workbook.add_format({
                    "bold": True,
                    "text_wrap": True,
                    "valign": "top",
                    "fg_color": "#D7E4BC",
                    "border": 1
                })
                
                # Header'ları yaz
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # ✅ RESİMLERİ SATIRLARA EKLE
                for row_idx, image_path in enumerate(image_paths):
                    excel_row = row_idx + 1  # +1 çünkü header var
                    
                    # Satır yüksekliğini artır (resim için)
                    worksheet.set_row(excel_row, 120)
                    
                    if image_path and os.path.exists(image_path):
                        try:
                            # Resmi ekle (app.py ile aynı ayarlar)
                            worksheet.insert_image(f"A{excel_row + 1}", image_path, {
                                "x_scale": 0.4,
                                "y_scale": 0.4,
                                "x_offset": 45,
                                "y_offset": 35
                            })
                            print(f"[EXCEL-MULTI] 🖼️ Satır {excel_row + 1}: Resim eklendi")
                        except Exception as img_error:
                            print(f"[EXCEL-MULTI] ❌ Satır {excel_row + 1} resim ekleme hatası: {img_error}")
                            # Resim eklenemezse "Resim Hatası" yaz
                            worksheet.write(f"A{excel_row + 1}", "Resim Hatası")
                    else:
                        # Resim yoksa "Resim Yok" yaz
                        worksheet.write(f"A{excel_row + 1}", "Resim Yok")
                
                # ✅ EK SAYFALAR - Malzeme seçenekleri özeti
                # Tüm analizlerin malzeme seçeneklerini birleştir
                all_material_options = []
                for analysis in analyses:
                    material_options = analysis.get('material_options', [])
                    for mat_option in material_options:
                        mat_option['source_analysis'] = analysis.get('id', 'Unknown')
                        mat_option['source_filename'] = analysis.get('original_filename', 'Unknown')
                        all_material_options.append(mat_option)
                
                if all_material_options:
                    materials_df = pd.DataFrame(all_material_options)
                    materials_df.to_excel(writer, sheet_name='Tüm Malzeme Seçenekleri', index=False)
                    print(f"[EXCEL-MULTI] 📄 Malzeme seçenekleri sayfası: {len(all_material_options)} seçenek")
                
                # ✅ ÖZET SAYFA
                summary_data = {
                    "Metrik": [
                        "Toplam Analiz Sayısı",
                        "Başarılı Analizler", 
                        "Başarısız Analizler",
                        "STEP Dosyaları",
                        "PDF Dosyaları",
                        "Ortalama İşleme Süresi (s)",
                        "Toplam Hacim (mm³)",
                        "Ortalama Malzeme Maliyeti (USD)"
                    ],
                    "Değer": [
                        len(analyses),
                        len([a for a in analyses if a.get('analysis_status') == 'completed']),
                        len([a for a in analyses if a.get('analysis_status') == 'failed']),
                        len([a for a in analyses if a.get('file_type') in ['step', 'stp']]),
                        len([a for a in analyses if a.get('file_type') == 'pdf']),
                        round(sum([a.get('processing_time', 0) for a in analyses]) / len(analyses), 2),
                        sum([a.get('step_analysis', {}).get('Ürün Hacmi (mm³)', 0) for a in analyses]),
                        round(sum([a.get('material_cost', 0) for a in analyses]) / len(analyses), 2)
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Özet', index=False)
                print(f"[EXCEL-MULTI] 📊 Özet sayfası oluşturuldu")
            
            output.seek(0)
            
            # ✅ DOSYA ADI OLUŞTUR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"coklu_analiz_{len(analyses)}_dosya_{timestamp}.xlsx"
            
            print(f"[EXCEL-MULTI] ✅ Excel dosyası hazır: {filename}")
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except ImportError:
            return jsonify({
                "success": False,
                "message": "Excel export için pandas ve xlsxwriter gerekli"
            }), 500
        except Exception as excel_error:
            print(f"[EXCEL-MULTI] ❌ Excel oluşturma hatası: {excel_error}")
            import traceback
            print(f"[EXCEL-MULTI] 📋 Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "success": False,
                "message": f"Excel oluşturma hatası: {str(excel_error)}"
            }), 500
            
    except Exception as e:
        print(f"[EXCEL-MULTI] ❌ Genel hata: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Çoklu Excel export hatası: {str(e)}"
        }), 500
