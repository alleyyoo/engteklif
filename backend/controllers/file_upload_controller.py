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
    """Yüklenmiş dosyayı analiz et - ENHANCED WITH DETAILED RENDERING"""
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
        
        # Enhanced Material Analysis Service kullan
        try:
            material_service = MaterialAnalysisService()
            
            # Kapsamlı analiz yap
            if analysis['file_type'] in ['pdf', 'document', 'step']:
                result = material_service.analyze_document_comprehensive(
                    analysis['file_path'], 
                    analysis['file_type'],
                    current_user['id']
                )
                
                # ✅ ENHANCED STEP RENDERING - process_uploaded_files'dan uyarlanan detaylı
                enhanced_renders = {}
                if analysis['file_type'] == 'step' and result.get('step_analysis') and not result.get('error'):
                    try:
                        print(f"[INFO] 🎨 Detaylı STEP rendering başlıyor: {analysis_id}")
                        
                        # Enhanced Step Renderer kullan
                        step_renderer = StepRendererEnhanced()
                        
                        # Çoklu görünüm oluştur - process_uploaded_files tarzında
                        render_result = step_renderer.generate_comprehensive_views(
                            analysis['file_path'],
                            analysis_id=analysis_id,
                            include_dimensions=True,
                            include_materials=True,
                            high_quality=True
                        )
                        
                        if render_result['success']:
                            enhanced_renders = render_result['renders']
                            print(f"[SUCCESS] ✅ {len(enhanced_renders)} detaylı render oluşturuldu")
                            
                            # Ana isometric render'ı result'a ekle (app.py process_uploaded_files gibi)
                            if 'isometric' in enhanced_renders:
                                result['isometric_view'] = enhanced_renders['isometric']['file_path']
                                result['isometric_view_enhanced'] = enhanced_renders['isometric']
                                # Excel-friendly version da ekle
                                if 'excel_path' in enhanced_renders['isometric']:
                                    result['isometric_view_clean'] = enhanced_renders['isometric']['excel_path']
                        else:
                            print(f"[WARN] ⚠️ Enhanced rendering başarısız: {render_result.get('message')}")
                            
                    except Exception as render_error:
                        print(f"[ERROR] ❌ Enhanced rendering hatası: {render_error}")
                        # Rendering hatası ana analizi etkilemez
                
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
                        "isometric_view_clean": result.get('isometric_view_clean'),  # Excel version
                        "processing_log": result.get('processing_log', []),
                        "step_file_hash": result.get('step_file_hash'),
                        "all_material_calculations": result.get('all_material_calculations', []),
                        "material_options": result.get('material_options', []),
                        # ✅ Enhanced rendering results - process_uploaded_files benzeri
                        "enhanced_renders": enhanced_renders,
                        "render_quality": "high" if enhanced_renders else "standard"
                    }
                    
                    FileAnalysis.update_analysis(analysis_id, update_data)
                    
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
                            "enhanced_renders_count": len(enhanced_renders),
                            "render_types": list(enhanced_renders.keys()) if enhanced_renders else [],
                            "excel_friendly_render": bool(result.get('isometric_view_clean'))  # Excel uyumlu render var mı
                        },
                        "enhanced_features": {
                            "detailed_wireframe": bool(enhanced_renders.get('wireframe')),
                            "dimensioned_views": bool(enhanced_renders.get('technical')),
                            "material_annotated": bool(enhanced_renders.get('material')),
                            "multi_view_projection": bool(len(enhanced_renders) > 1)
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
    """Analiz sonuçlarını Excel'e aktar"""
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
        
        # Excel export servisi (placeholder - implement edilecek)
        try:
            import pandas as pd
            import io
            from datetime import datetime
            
            # Analiz verilerini topla
            data = {
                "Dosya Adı": [analysis.get('original_filename', 'N/A')],
                "Dosya Türü": [analysis.get('file_type', 'N/A')],
                "Analiz Durumu": [analysis.get('analysis_status', 'N/A')],
                "İşleme Süresi (s)": [analysis.get('processing_time', 0)],
                "Malzeme Eşleşme Sayısı": [len(analysis.get('material_matches', []))],
                "Render Sayısı": [len(analysis.get('enhanced_renders', {}))],
                "Oluşturma Tarihi": [analysis.get('created_at', 'N/A')]
            }
            
            # STEP analizi varsa ekle
            step_analysis = analysis.get('step_analysis', {})
            if step_analysis and not step_analysis.get('error'):
                data.update({
                    "Genişlik (mm)": [step_analysis.get('X (mm)', 0)],
                    "Yükseklik (mm)": [step_analysis.get('Y (mm)', 0)],
                    "Derinlik (mm)": [step_analysis.get('Z (mm)', 0)],
                    "Hacim (mm³)": [step_analysis.get('Prizma Hacmi (mm³)', 0)],
                    "Yüzey Alanı (mm²)": [step_analysis.get('Toplam Yüzey Alanı (mm²)', 0)]
                })
            
            # DataFrame oluştur
            df = pd.DataFrame(data)
            
            # Excel dosyası oluştur
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Analiz Sonuçları', index=False)
                
                # Malzeme seçenekleri sayfası
                material_options = analysis.get('material_options', [])
                if material_options:
                    material_df = pd.DataFrame(material_options)
                    material_df.to_excel(writer, sheet_name='Malzeme Seçenekleri', index=False)
            
            output.seek(0)
            
            # Dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analiz_{analysis_id}_{timestamp}.xlsx"
            
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
