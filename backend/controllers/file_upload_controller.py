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

def background_render_task(analysis_id: str, step_path: str, extracted_step_path: str = None):
    """Arka planda render işlemi"""
    try:
        print(f"[BG-RENDER] 🎨 Arka plan render başlıyor: {analysis_id}")
        
        # Step renderer'ı kullan
        from services.step_renderer import StepRendererEnhanced
        from models.file_analysis import FileAnalysis
        import cadquery as cq
        from cadquery import exporters
        
        step_renderer = StepRendererEnhanced()
        
        # Hangi STEP dosyasını kullanacağız?
        render_path = extracted_step_path if extracted_step_path and os.path.exists(extracted_step_path) else step_path
        
        # Render oluştur
        render_result = step_renderer.generate_comprehensive_views(
            render_path,
            analysis_id=analysis_id,
            include_dimensions=True,
            include_materials=True,
            high_quality=True
        )
        
        if render_result['success']:
            # Analiz kaydını güncelle
            update_data = {
                "enhanced_renders": render_result['renders'],
                "render_quality": "high",
                "render_status": "completed"
            }
            
            # Ana isometric view'ı ekle
            if 'isometric' in render_result['renders']:
                update_data["isometric_view"] = render_result['renders']['isometric']['file_path']
                if 'excel_path' in render_result['renders']['isometric']:
                    update_data["isometric_view_clean"] = render_result['renders']['isometric']['excel_path']
            
            # STL oluştur
            try:
                session_output_dir = os.path.join("static", "stepviews", analysis_id)
                os.makedirs(session_output_dir, exist_ok=True)
                
                stl_filename = f"model_{analysis_id}.stl"
                stl_path_full = os.path.join(session_output_dir, stl_filename)
                
                # STEP'ten STL oluştur
                assembly = cq.importers.importStep(render_path)
                shape = assembly.val()
                exporters.export(shape, stl_path_full)
                
                if os.path.exists(stl_path_full):
                    stl_relative = f"/static/stepviews/{analysis_id}/{stl_filename}"
                    update_data["stl_generated"] = True
                    update_data["stl_path"] = stl_relative
                    update_data["stl_file_size"] = os.path.getsize(stl_path_full)
                    
                    print(f"[BG-RENDER] ✅ STL oluşturuldu: {stl_filename}")
                    
            except Exception as stl_error:
                print(f"[BG-RENDER] ⚠️ STL oluşturma hatası: {stl_error}")
            
            FileAnalysis.update_analysis(analysis_id, update_data)
            
            print(f"[BG-RENDER] ✅ Render tamamlandı: {analysis_id} - {len(render_result['renders'])} görünüm")
            return {"success": True, "renders": len(render_result['renders'])}
            
        else:
            FileAnalysis.update_analysis(analysis_id, {
                "render_status": "failed",
                "render_error": render_result.get('message', 'Render hatası')
            })
            print(f"[BG-RENDER] ❌ Render başarısız: {analysis_id}")
            return {"success": False, "error": render_result.get('message')}
            
    except Exception as e:
        import traceback
        print(f"[BG-RENDER] ❌ Arka plan render hatası: {str(e)}")
        print(f"[BG-RENDER] 📋 Traceback: {traceback.format_exc()}")
        
        try:
            FileAnalysis.update_analysis(analysis_id, {
                "render_status": "failed",
                "render_error": str(e)
            })
        except:
            pass
            
        return {"success": False, "error": str(e)}

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
    """✅ ENHANCED - Hızlı analiz + arka planda render"""
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
        
        # ✅ Material Analysis Service kullan - SADECE TEMEL ANALİZ
        try:
            from services.background_tasks import task_manager
            
            material_service = MaterialAnalysisService()
            
            print(f"[ANALYSIS] ⚡ Hızlı analiz başlatılıyor: {analysis['file_type']} - {analysis['original_filename']}")
            
            # ✅ HIZLI ANALİZ - analyze_document_fast kullan!
            if analysis['file_type'] in ['pdf', 'document', 'step', 'stp', 'doc', 'docx']:
                # ✅ DÜZELTİLDİ - analyze_document_fast metodunu çağır
                result = material_service.analyze_document_comprehensive(
                    analysis['file_path'], 
                    analysis['file_type'],
                    current_user['id']
                )
                
                print(f"[ANALYSIS] ✅ Hızlı analiz tamamlandı - Success: {not result.get('error')}")
                
                analysis_success = not result.get('error')
                
                if analysis_success:
                    processing_time = time.time() - start_time
                    print(f"[ANALYSIS] ⏱️ Analiz süresi: {processing_time:.2f}s")
                    
                    # ✅ Temel sonuçları hemen kaydet - RENDER ALANLARI BOŞ
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
                        "step_file_hash": result.get('step_file_hash'),
                        # ✅ RENDER ALANLARI BOŞ/NONE
                        "isometric_view": None,
                        "isometric_view_clean": None,
                        "enhanced_renders": {},  # ✅ BOŞ OBJE
                        "render_status": "pending",
                        "render_quality": "none",
                        "stl_generated": False,
                        "stl_path": None
                    }
                    
                    # PDF özel alanlar
                    if analysis['file_type'] == 'pdf':
                        update_data["pdf_step_extracted"] = bool(result.get('step_file_hash'))
                        update_data["pdf_rotation_count"] = result.get('rotation_count', 0)
                        update_data["extracted_step_path"] = result.get('extracted_step_path')
                        update_data["pdf_analysis_id"] = result.get('pdf_analysis_id')
                    
                    FileAnalysis.update_analysis(analysis_id, update_data)
                    
                    # ✅ RENDER'I ARKA PLANDA YAP
                    should_render = False
                    render_path = None
                    
                    if analysis['file_type'] in ['step', 'stp']:
                        should_render = True
                        render_path = analysis['file_path']
                    elif analysis['file_type'] == 'pdf' and result.get('step_file_hash'):
                        should_render = True
                        render_path = result.get('extracted_step_path')
                    
                    if should_render and render_path:
                        # Render görevini kuyruğa ekle
                        task_id = task_manager.add_task(
                            func=background_render_task,
                            args=(analysis_id, analysis['file_path'], render_path),
                            name=f"Render_{analysis_id}",
                            callback=lambda res: print(f"[BACKGROUND] ✅ Render tamamlandı: {analysis_id}")
                        )
                        
                        # Task ID'yi kaydet
                        FileAnalysis.update_analysis(analysis_id, {
                            "render_task_id": task_id,
                            "render_status": "processing"
                        })
                        
                        print(f"[ANALYSIS] 🎨 Render görevi arka plana eklendi: {task_id}")
                    
                    # ✅ GÜNCELLENMIŞ ANALİZİ DÖNDÜR - RENDER ALANLARI BOŞ
                    updated_analysis = FileAnalysis.find_by_id(analysis_id)
                    
                    # ✅ FRONTEND'E DÖNEN RESPONSE - RENDER ALANLARI BOŞ
                    response_data = {
                        "success": True,
                        "message": "Analiz başarıyla tamamlandı",
                        "analysis": {
                            **updated_analysis,
                            # ✅ RENDER ALANLARINI AÇIKÇA BOŞ GÖNDER
                            "enhanced_renders": {},
                            "isometric_view": None,
                            "isometric_view_clean": None,
                            "stl_generated": False,
                            "stl_path": None
                        },
                        "processing_time": processing_time,
                        "render_status": "processing" if should_render else "none",
                        "analysis_details": {
                            "material_matches_count": len(result.get('material_matches', [])),
                            "step_analysis_available": bool(result.get('step_analysis')),
                            "cost_estimation_available": bool(result.get('cost_estimation')),
                            "processing_steps": len(result.get('processing_log', [])),
                            "all_material_calculations_count": len(result.get('all_material_calculations', [])),
                            "material_options_count": len(result.get('material_options', [])),
                            "3d_render_available": False,  # ✅ AÇIKÇA FALSE
                            "excel_friendly_render": False,  # ✅ AÇIKÇA FALSE
                            "pdf_step_extracted": analysis['file_type'] == 'pdf' and bool(result.get('step_file_hash')),
                            "step_file_hash": result.get('step_file_hash'),
                            "pdf_rotation_attempts": result.get('rotation_count', 0),
                            "stl_generated": False,  # ✅ AÇIKÇA FALSE
                            "render_in_progress": should_render
                        }
                    }
                    
                    print(f"[ANALYSIS] 📤 Response gönderiliyor - Render alanları: BOŞ")
                    
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
    """✅ FIXED - Excel dosyasını analiz sonuçlarıyla birleştir - KÜTLE VE FİYAT HESAPLAMALARİ İLE"""
    try:
        current_user = get_current_user()
        
        # Form verilerini kontrol et
        if 'excel_file' not in request.files:
            return jsonify({
                "success": False,
                "message": "Excel dosyası bulunamadı"
            }), 400
        
        excel_file = request.files['excel_file']
        analysis_ids = request.form.getlist('analysis_ids')
        
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
        
        print(f"[MERGE-FIXED] 📊 Excel birleştirme başlıyor: {excel_file.filename}")
        print(f"[MERGE-FIXED] 🔢 Analiz ID'leri: {analysis_ids}")
        
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
        
        print(f"[MERGE-FIXED] ✅ {len(analyses)} analiz yüklendi")
        
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
            print(f"[MERGE-FIXED] ✅ Excel yüklendi. Satır: {ws.max_row}, Sütun: {ws.max_column}")
            
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
            print(f"[MERGE-FIXED] 📋 Header satırı: {header_row}")
            
            # Malzeme No sütununu bul
            malzeme_no_patterns = [
                "malzeme no", "malzemeno", "malzeme_no", "malzeme numarası", "malzeme numarasi",
                "ürün kodu", "urun kodu", "ürün no", "urun no", "kod", "no", "part", "item"
            ]
            
            malzeme_col_index = None
            for i, header in enumerate(header_row):
                if header:
                    normalized_header = normalize_robust(header)
                    print(f"[MERGE-FIXED] 🔍 Header {i+1}: '{header}' -> '{normalized_header}'")
                    
                    for pattern in malzeme_no_patterns:
                        if normalize_robust(pattern) == normalized_header:
                            malzeme_col_index = i + 1  # 1-based
                            print(f"[MERGE-FIXED] ✅ Malzeme No sütunu: '{header}' (sütun {malzeme_col_index})")
                            break
                    if malzeme_col_index:
                        break
            
            if not malzeme_col_index:
                # Fallback: üçüncü sütun genelde malzeme no'dur
                malzeme_col_index = 3
                print(f"[MERGE-FIXED] ⚠️ Malzeme No sütunu bulunamadı, sütun {malzeme_col_index} kullanılıyor")
            
            # İhale miktarı sütununu bul
            ihale_col_index = None
            ihale_patterns = ["ihale", "miktar", "adet", "quantity", "amount"]
            
            for i, header in enumerate(header_row):
                if header:
                    normalized_header = normalize_robust(header)
                    for pattern in ihale_patterns:
                        if pattern in normalized_header:
                            ihale_col_index = i + 1
                            print(f"[MERGE-FIXED] ✅ İhale sütunu: '{header}' (sütun {ihale_col_index})")
                            break
                    if ihale_col_index:
                        break
            
            if not ihale_col_index:
                ihale_col_index = malzeme_col_index + 1
                print(f"[MERGE-FIXED] ⚠️ İhale sütunu bulunamadı, sütun {ihale_col_index} kullanılıyor")
            
            # ✅ İHALE SÜTUNUNDAN SONRAKİ SÜTUNLARI SİL
            columns_to_keep = ihale_col_index
            columns_to_delete = ws.max_column - columns_to_keep
            
            for _ in range(columns_to_delete):
                if ws.max_column > columns_to_keep:
                    ws.delete_cols(columns_to_keep + 1)
            
            print(f"[MERGE-FIXED] 🗑️ {columns_to_delete} sütun silindi")
            
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
            
            # ✅ ANALİZ VERİLERİNİ LOOKUP TABLOSU HAZİRLA - ENHANCED MATERIAL CALCULATIONS
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
                
                # ✅ KÜTLE VE FİYAT HESAPLAMALARI
                analysis_calculated_data = calculate_mass_and_cost_for_analysis(analysis)
                
                # Benzersiz kodları normalize et ve ekle
                for code in set(product_codes):
                    if code and len(code) >= 3:  # En az 3 karakter
                        normalized_code = normalize_robust(code)
                        if normalized_code:
                            # Analysis'e hesaplanmış verileri ekle
                            enhanced_analysis = analysis.copy()
                            enhanced_analysis.update(analysis_calculated_data)
                            
                            analysis_lookup[normalized_code] = enhanced_analysis
                            print(f"[MERGE-FIXED] 📝 Lookup eklendi: '{code}' -> '{normalized_code}' -> {analysis['id']} (kütle: {analysis_calculated_data.get('calculated_mass_kg', 'N/A')} kg)")
            
            print(f"[MERGE-FIXED] 📋 Toplam lookup entries: {len(analysis_lookup)}")
            
            # ✅ SATIRLARI İŞLE VE EŞLEŞTİR
            matched_count = 0
            total_rows = 0
            
            for row in range(2, ws.max_row + 1):
                total_rows += 1
                
                # Excel'den malzeme numarasını al
                malzeme_cell = ws.cell(row=row, column=malzeme_col_index).value
                
                if not malzeme_cell:
                    print(f"[MERGE-FIXED] ⚠️ Satır {row}: Malzeme numarası boş")
                    continue
                
                excel_malzeme = str(malzeme_cell).strip()
                print(f"[MERGE-FIXED] 🔍 Satır {row}: Excel malzeme = '{excel_malzeme}'")
                
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
                    print(f"[MERGE-FIXED] ✅ Satır {row}: '{excel_malzeme}' eşleşti -> {matched_analysis['id']} ({match_method})")
                    
                    # ✅ HESAPLANMIŞ VERİLERİ AL
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
                    
                    # ✅ HESAPLANMIŞ KÜTLE VE MALİYET - LOOKUP'TAN AL
                    kutle_kg = matched_analysis.get('calculated_mass_kg', 0)
                    maliyet_usd = matched_analysis.get('calculated_material_cost_usd', 0)
                    density_used = matched_analysis.get('density_used', 2.7)
                    price_per_kg_used = matched_analysis.get('price_per_kg_used', 4.5)
                    
                    # İşçilik maliyeti hesaplama (basit tahmin)
                    iscilik_usd = 0
                    if kutle_kg > 0:
                        # Kütle bazlı işçilik tahmini: büyük parça = daha fazla işçilik
                        iscilik_base = min(kutle_kg * 15, 50)  # Max $50
                        iscilik_usd = round(iscilik_base, 2)
                    
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
                        kutle_kg if kutle_kg > 0 else None,           # ← HESAPLANMIŞ KÜTLE
                        maliyet_usd if maliyet_usd > 0 else None,     # ← HESAPLANMIŞ MALİYET
                        "",  # Kaplama - boş bırak
                        "",  # Helicoil - boş bırak
                        "",  # Markalama - boş bırak
                        iscilik_usd if iscilik_usd > 0 else "",      # İşçilik
                        birim_fiyat if birim_fiyat > 0 else "",      # Birim Fiyat
                        toplam_maliyet if toplam_maliyet > 0 else "" # Toplam
                    ]
                    
                    print(f"[MERGE-FIXED] 📊 Satır {row} değerler:")
                    print(f"   - Kütle: {kutle_kg} kg (density: {density_used} g/cm³)")
                    print(f"   - Hammadde Maliyeti: ${maliyet_usd} (${price_per_kg_used}/kg)")
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
                                        
                                        print(f"[MERGE-FIXED] 🖼️ Satır {row}: Resim eklendi ({img.width}x{img.height})")
                                        
                                    except Exception as img_error:
                                        print(f"[MERGE-FIXED] ❌ Satır {row} resim hatası: {img_error}")
                                        target_cell.value = "Resim Hatası"
                                else:
                                    print(f"[MERGE-FIXED] ⚠️ Satır {row}: Resim dosyası bulunamadı: {full_image_path}")
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
                    print(f"[MERGE-FIXED] ❌ Satır {row}: '{excel_malzeme}' eşleşmedi")
            
            print(f"[MERGE-FIXED] 📊 İşlem tamamlandı: {matched_count}/{total_rows} eşleşme")
            
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
            
            print(f"[MERGE-FIXED] ✅ Excel başarıyla birleştirildi: {filename}")
            print(f"[MERGE-FIXED] 📈 Sonuç: {matched_count}/{total_rows} satır eşleşti")
            
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
            print(f"[MERGE-FIXED] ❌ Excel işleme hatası: {excel_error}")
            import traceback
            print(f"[MERGE-FIXED] 📋 Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "success": False,
                "message": f"Excel işleme hatası: {str(excel_error)}",
                "details": traceback.format_exc()
            }), 500
    
    except Exception as e:
        print(f"[MERGE-FIXED] ❌ Genel hata: {str(e)}")
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
    """✅ FIXED - Birden fazla analizi Excel'e aktar - KÜTLE VE MALİYET HESAPLAMALARİ İLE"""
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
        
        print(f"[EXCEL-MULTI-FIXED] 📊 Çoklu Excel export başlıyor: {len(analysis_ids)} analiz")
        
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
            
            print(f"[EXCEL-MULTI-FIXED] ✅ {len(analyses)} analiz işlenecek")
            
            # ✅ TÜM ANALİZLER İÇİN ENHANCED VERİ HAZIRLA
            excel_data = []
            total_calculated_mass = 0
            total_calculated_cost = 0
            successful_calculations = 0
            
            for analysis in analyses:
                print(f"[EXCEL-MULTI-FIXED] 🔄 İşleniyor: {analysis.get('original_filename', 'unknown')}")
                
                # ✅ HER ANALİZ İÇİN KÜTLE VE MALİYET HESAPLA
                calculated_data = calculate_mass_and_cost_for_analysis(analysis)
                
                # ✅ STEP ANALİZİ VERİLERİNİ TOPLA
                step_analysis = analysis.get('step_analysis', {})
                
                # ✅ MALZEME BİLGİSİNİ BELİRLE
                material_name = calculated_data['material_used']
                if material_name == 'Unknown':
                    material_matches = analysis.get('material_matches', [])
                    if material_matches:
                        first_match = material_matches[0]
                        if isinstance(first_match, str) and "(" in first_match:
                            material_name = first_match.split("(")[0].strip()
                        else:
                            material_name = str(first_match)
                
                # ✅ İŞÇİLİK VE TOPLAM MALİYET HESAPLAMA
                calculated_mass_kg = calculated_data['calculated_mass_kg']
                calculated_material_cost = calculated_data['calculated_material_cost_usd']
                
                # İşçilik tahmini (kütle bazlı)
                estimated_labor_cost = 0
                if calculated_mass_kg > 0:
                    # Kütle bazlı işçilik: 0.5 kg altı = $10, üstü = kütle * $12
                    if calculated_mass_kg <= 0.5:
                        estimated_labor_cost = 10.0
                    else:
                        estimated_labor_cost = min(calculated_mass_kg * 12, 100.0)  # Max $100
                
                # Toplam birim maliyet
                unit_total_cost = calculated_material_cost + estimated_labor_cost
                
                # İstatistik için topla
                if calculated_mass_kg > 0:
                    total_calculated_mass += calculated_mass_kg
                    total_calculated_cost += unit_total_cost
                    successful_calculations += 1
                
                # ✅ EXCEL SATIRI OLUŞTUR - ENHANCED
                row_data = {
                    "Ürün Görseli": "",  # Resim için boş bırak - sonra eklenecek
                    "Analiz ID": analysis.get('id', 'N/A'),
                    "Dosya Adı": analysis.get('original_filename', 'N/A'),
                    "Dosya Türü": analysis.get('file_type', 'N/A'),
                    "Analiz Durumu": analysis.get('analysis_status', 'N/A'),
                    
                    # ✅ MALZEME BİLGİLERİ - ENHANCED
                    "Hammadde": material_name,
                    "Yoğunluk (g/cm³)": calculated_data['density_used'],
                    "Malzeme Fiyatı (USD/kg)": calculated_data['price_per_kg_used'],
                    
                    # ✅ BOYUTLAR
                    "X+Pad (mm)": step_analysis.get('X+Pad (mm)', step_analysis.get('X (mm)', 0)),
                    "Y+Pad (mm)": step_analysis.get('Y+Pad (mm)', step_analysis.get('Y (mm)', 0)),
                    "Z+Pad (mm)": step_analysis.get('Z+Pad (mm)', step_analysis.get('Z (mm)', 0)),
                    "Silindirik Çap (mm)": step_analysis.get('Silindirik Çap (mm)', 0),
                    
                    # ✅ HACİM VE KÜTLE - HESAPLANMIŞ
                    "Hacim (mm³)": calculated_data['volume_used_mm3'],
                    "Ürün Hacmi (mm³)": step_analysis.get('Ürün Hacmi (mm³)', 0),
                    "Toplam Yüzey Alanı (mm²)": step_analysis.get('Toplam Yüzey Alanı (mm²)', 0),
                    "Kütle (kg)": calculated_mass_kg,  # ← HESAPLANMIŞ KÜTLE
                    
                    # ✅ MALİYET BİLGİLERİ - HESAPLANMIŞ
                    "Hammadde Maliyeti (USD)": calculated_material_cost,  # ← HESAPLANMIŞ MALİYET
                    "Tahmini İşçilik (USD)": round(estimated_labor_cost, 2),
                    "Birim Toplam Maliyet (USD)": round(unit_total_cost, 2),
                    
                    # ✅ META VERİLER
                    "İşleme Süresi (s)": analysis.get('processing_time', 0),
                    "Oluşturma Tarihi": analysis.get('created_at', 'N/A'),
                    "Render Sayısı": len(analysis.get('enhanced_renders', {})),
                    "PDF'den STEP": "Evet" if analysis.get('pdf_step_extracted', False) else "Hayır"
                }
                
                # Malzeme detayını ekle (varsa)
                if analysis.get('material_matches'):
                    row_data["Malzeme Eşleşmeleri"] = "; ".join(analysis['material_matches'][:3])  # İlk 3'ü
                
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
                        print(f"[EXCEL-MULTI-FIXED] ⚠️ Görsel dosyası bulunamadı: {full_image_path}")
                        full_image_path = None
                    else:
                        print(f"[EXCEL-MULTI-FIXED] ✅ Görsel bulundu: {full_image_path}")
                
                # Row data'ya image path'i ekle (Excel'de kullanılacak)
                row_data["_image_path"] = full_image_path
                
                excel_data.append(row_data)
                
                print(f"[EXCEL-MULTI-FIXED] ✅ {analysis.get('original_filename')}: {calculated_mass_kg:.3f} kg, ${calculated_material_cost:.2f}")
            
            # ✅ DATAFRAME OLUŞTUR
            df = pd.DataFrame(excel_data)
            
            # _image_path sütununu DataFrame'den çıkar (sadece internal kullanım için)
            image_paths = df["_image_path"].tolist()
            df = df.drop(columns=["_image_path"])
            
            print(f"[EXCEL-MULTI-FIXED] 📋 DataFrame oluşturuldu: {len(df)} satır")
            print(f"[EXCEL-MULTI-FIXED] 📊 Toplam kütle: {total_calculated_mass:.3f} kg")
            print(f"[EXCEL-MULTI-FIXED] 💰 Toplam maliyet: ${total_calculated_cost:.2f}")
            
            # ✅ EXCEL ÇIKTISI (xlsxwriter ile)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Ana sayfayı yaz (header'ı manuel olarak yazacağız)
                df.to_excel(writer, sheet_name='Analiz Sonuçları', index=False, header=False, startrow=1)
                
                workbook = writer.book
                worksheet = writer.sheets['Analiz Sonuçları']
                
                # ✅ SÜTUN GENİŞLİKLERİNİ AYARLA
                column_widths = {
                    0: 60,   # Görsel sütunu geniş
                    1: 15,   # Analiz ID
                    2: 25,   # Dosya Adı
                    3: 12,   # Dosya Türü
                    4: 15,   # Analiz Durumu
                    5: 20,   # Hammadde
                    6: 12,   # Yoğunluk
                    7: 15,   # Malzeme Fiyatı
                    8: 12,   # X+Pad
                    9: 12,   # Y+Pad
                    10: 12,  # Z+Pad
                    11: 15,  # Silindirik Çap
                    12: 15,  # Hacim
                    13: 15,  # Ürün Hacmi
                    14: 18,  # Yüzey Alanı
                    15: 12,  # Kütle
                    16: 18,  # Hammadde Maliyeti
                    17: 15,  # İşçilik
                    18: 18,  # Birim Toplam
                    19: 15,  # İşleme Süresi
                    20: 20,  # Tarih
                    21: 12,  # Render Sayısı
                    22: 12,  # PDF STEP
                    23: 25   # Malzeme Eşleşmeleri
                }
                
                for col_index, width in column_widths.items():
                    if col_index < len(df.columns):
                        col_letter = chr(65 + col_index)  # A, B, C, ...
                        if col_index >= 26:  # AA, AB, AC, ...
                            col_letter = chr(64 + col_index // 26) + chr(65 + col_index % 26)
                        worksheet.set_column(f"{col_letter}:{col_letter}", width)
                
                # ✅ HEADER STİLİ
                header_format = workbook.add_format({
                    "bold": True,
                    "text_wrap": True,
                    "valign": "top",
                    "fg_color": "#D7E4BC",
                    "border": 1,
                    "font_size": 10
                })
                
                # ✅ SAYISAL DEĞER FORMATLARİ
                number_format = workbook.add_format({'num_format': '#,##0.000'})
                currency_format = workbook.add_format({'num_format': '$#,##0.00'})
                percent_format = workbook.add_format({'num_format': '0.0%'})
                
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
                            # Resmi ekle (optimized boyutlarda)
                            worksheet.insert_image(f"A{excel_row + 1}", image_path, {
                                "x_scale": 0.35,
                                "y_scale": 0.35,
                                "x_offset": 5,
                                "y_offset": 5
                            })
                            print(f"[EXCEL-MULTI-FIXED] 🖼️ Satır {excel_row + 1}: Resim eklendi")
                        except Exception as img_error:
                            print(f"[EXCEL-MULTI-FIXED] ❌ Satır {excel_row + 1} resim ekleme hatası: {img_error}")
                            # Resim eklenemezse "Resim Hatası" yaz
                            worksheet.write(f"A{excel_row + 1}", "Resim Hatası")
                    else:
                        # Resim yoksa "Resim Yok" yaz
                        worksheet.write(f"A{excel_row + 1}", "Resim Yok")
                
                # ✅ SAYISAL SÜTUNLARA FORMAT UYGULA
                # Kütle sütunu (kg)
                mass_col = None
                cost_cols = []
                
                for col_idx, col_name in enumerate(df.columns):
                    if "Kütle" in col_name:
                        mass_col = col_idx
                    elif any(keyword in col_name for keyword in ["Maliyet", "İşçilik", "Toplam", "Fiyat"]):
                        cost_cols.append(col_idx)
                
                # Kütle formatı
                if mass_col is not None:
                    col_letter = chr(65 + mass_col)
                    worksheet.set_column(f"{col_letter}:{col_letter}", 12, number_format)
                
                # Para formatı
                for col_idx in cost_cols:
                    col_letter = chr(65 + col_idx)
                    worksheet.set_column(f"{col_letter}:{col_letter}", 15, currency_format)
                
                # ✅ EK SAYFALAR
                
                # 1. Malzeme özeti sayfası
                material_summary = {}
                for analysis in analyses:
                    calculated_data = calculate_mass_and_cost_for_analysis(analysis)
                    material = calculated_data['material_used']
                    
                    if material not in material_summary:
                        material_summary[material] = {
                            'count': 0,
                            'total_mass': 0,
                            'total_cost': 0,
                            'density': calculated_data['density_used'],
                            'price_per_kg': calculated_data['price_per_kg_used']
                        }
                    
                    material_summary[material]['count'] += 1
                    material_summary[material]['total_mass'] += calculated_data['calculated_mass_kg']
                    material_summary[material]['total_cost'] += calculated_data['calculated_material_cost_usd']
                
                if material_summary:
                    summary_data = []
                    for material, data in material_summary.items():
                        summary_data.append({
                            'Malzeme': material,
                            'Parça Sayısı': data['count'],
                            'Toplam Kütle (kg)': round(data['total_mass'], 3),
                            'Toplam Maliyet (USD)': round(data['total_cost'], 2),
                            'Ortalama Kütle (kg)': round(data['total_mass'] / data['count'], 3),
                            'Yoğunluk (g/cm³)': data['density'],
                            'Fiyat (USD/kg)': data['price_per_kg']
                        })
                    
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Malzeme Özeti', index=False)
                    print(f"[EXCEL-MULTI-FIXED] 📄 Malzeme özeti sayfası: {len(summary_data)} malzeme")
                
                # 2. Genel istatistikler sayfası
                stats_data = {
                    "Metrik": [
                        "Toplam Analiz Sayısı",
                        "Başarılı Kütle Hesaplaması", 
                        "Başarısız Analizler",
                        "STEP Dosyaları",
                        "PDF Dosyaları",
                        "PDF'den STEP Çıkarılan",
                        "Ortalama İşleme Süresi (s)",
                        "Toplam Kütle (kg)",
                        "Toplam Hammadde Maliyeti (USD)",
                        "Ortalama Birim Maliyet (USD)"
                    ],
                    "Değer": [
                        len(analyses),
                        successful_calculations,
                        len([a for a in analyses if a.get('analysis_status') == 'failed']),
                        len([a for a in analyses if a.get('file_type') in ['step', 'stp']]),
                        len([a for a in analyses if a.get('file_type') == 'pdf']),
                        len([a for a in analyses if a.get('pdf_step_extracted', False)]),
                        round(sum([a.get('processing_time', 0) for a in analyses]) / len(analyses), 2),
                        round(total_calculated_mass, 3),
                        round(sum([calculate_mass_and_cost_for_analysis(a)['calculated_material_cost_usd'] for a in analyses]), 2),
                        round(total_calculated_cost / len(analyses), 2) if analyses else 0
                    ]
                }
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='İstatistikler', index=False)
                print(f"[EXCEL-MULTI-FIXED] 📊 İstatistik sayfası oluşturuldu")
                
                # 3. Detaylı malzeme hesaplamaları sayfası
                detailed_calcs = []
                for analysis in analyses:
                    calc_data = calculate_mass_and_cost_for_analysis(analysis)
                    detailed_calcs.append({
                        'Analiz ID': analysis.get('id'),
                        'Dosya Adı': analysis.get('original_filename'),
                        'Malzeme': calc_data['material_used'],
                        'Hacim (mm³)': calc_data['volume_used_mm3'],
                        'Yoğunluk (g/cm³)': calc_data['density_used'],
                        'Kütle (kg)': calc_data['calculated_mass_kg'],
                        'Fiyat (USD/kg)': calc_data['price_per_kg_used'],
                        'Maliyet (USD)': calc_data['calculated_material_cost_usd'],
                        'Hesaplama Formülü': f"{calc_data['volume_used_mm3']} mm³ × {calc_data['density_used']} g/cm³ ÷ 1,000,000 = {calc_data['calculated_mass_kg']} kg"
                    })
                
                if detailed_calcs:
                    detailed_df = pd.DataFrame(detailed_calcs)
                    detailed_df.to_excel(writer, sheet_name='Hesaplama Detayları', index=False)
                    print(f"[EXCEL-MULTI-FIXED] 🧮 Hesaplama detayları sayfası: {len(detailed_calcs)} hesaplama")
            
            output.seek(0)
            
            # ✅ DOSYA ADI OLUŞTUR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"coklu_analiz_{len(analyses)}_dosya_{timestamp}.xlsx"
            
            print(f"[EXCEL-MULTI-FIXED] ✅ Excel dosyası hazır: {filename}")
            print(f"[EXCEL-MULTI-FIXED] 📈 Başarılı hesaplamalar: {successful_calculations}/{len(analyses)}")
            
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
            print(f"[EXCEL-MULTI-FIXED] ❌ Excel oluşturma hatası: {excel_error}")
            import traceback
            print(f"[EXCEL-MULTI-FIXED] 📋 Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "success": False,
                "message": f"Excel oluşturma hatası: {str(excel_error)}"
            }), 500
            
    except Exception as e:
        print(f"[EXCEL-MULTI-FIXED] ❌ Genel hata: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Çoklu Excel export hatası: {str(e)}"
        }), 500

def calculate_mass_and_cost_for_analysis(analysis):
    """✅ ANALİZ İÇİN KÜTLE VE MALİYET HESAPLAMA - ENHANCED WITH DEDUPLICATION"""
    try:
        # Default değerler
        result = {
            'calculated_mass_kg': 0.0,
            'calculated_material_cost_usd': 0.0,
            'density_used': 2.7,
            'price_per_kg_used': 4.5,
            'volume_used_mm3': 0.0,
            'material_used': 'Unknown'
        }
        
        # ✅ STEP ANALİZİNDEN HACİM AL
        step_analysis = analysis.get('step_analysis', {})
        volume_mm3 = 0
        
        # Hacim kaynaklarını dene
        if step_analysis.get('Prizma Hacmi (mm³)'):
            volume_mm3 = step_analysis['Prizma Hacmi (mm³)']
        elif step_analysis.get('Ürün Hacmi (mm³)'):
            volume_mm3 = step_analysis['Ürün Hacmi (mm³)']
        elif step_analysis.get('volume_mm3'):
            volume_mm3 = step_analysis['volume_mm3']
        
        if volume_mm3 <= 0:
            print(f"[CALC-MASS] ⚠️ Analiz {analysis.get('id', 'unknown')}: Geçerli hacim bulunamadı")
            return result
        
        result['volume_used_mm3'] = volume_mm3
        
        # ✅ MALZEME BİLGİSİNİ BELİRLE - ENHANCED DEDUPLICATION
        material_matches = analysis.get('material_matches', [])
        material_name = 'Unknown'
        best_confidence = 0
        
        # ✅ En yüksek confidence'a sahip malzemeyi bul
        if material_matches:
            best_material = None
            
            for match in material_matches:
                if isinstance(match, str):
                    # Confidence değerini çıkar
                    confidence_match = re.search(r'%(\d+)', match)
                    if confidence_match:
                        confidence_value = int(confidence_match.group(1))
                    elif "estimated" in match.lower():
                        confidence_value = 70  # estimated için varsayılan
                    else:
                        confidence_value = 50  # fallback
                    
                    # En yüksek confidence'ı bul
                    if confidence_value > best_confidence:
                        best_confidence = confidence_value
                        best_material = match
            
            # En iyi malzemeyi seç
            if best_material:
                if "(" in best_material:
                    material_name = best_material.split("(")[0].strip()
                else:
                    material_name = best_material.strip()
                
                print(f"[CALC-MASS] 🏆 En iyi malzeme seçildi: {material_name} (%{best_confidence})")
            else:
                # Fallback: ilk malzemeyi kullan
                first_match = material_matches[0]
                if isinstance(first_match, str) and "(" in first_match:
                    material_name = first_match.split("(")[0].strip()
                else:
                    material_name = str(first_match) if first_match else 'Unknown'
        
        result['material_used'] = material_name
        
        # ✅ MONGODB'DEN MALZEME VERİLERİNİ AL
        try:
            from utils.database import db
            database = db.get_db()
            
            # Malzeme ara
            material = database.materials.find_one({
                "$or": [
                    {"name": {"$regex": f"^{material_name}$", "$options": "i"}},
                    {"name": {"$regex": material_name, "$options": "i"}},
                    {"aliases": {"$in": [material_name]}},
                    {"aliases": {"$elemMatch": {"$regex": material_name, "$options": "i"}}}
                ]
            })
            
            if material:
                density = material.get("density", 2.7)
                price_per_kg = material.get("price_per_kg", 4.5)
                print(f"[CALC-MASS] ✅ MongoDB'de bulundu: {material.get('name')} (density: {density}, price: ${price_per_kg})")
            else:
                print(f"[CALC-MASS] ⚠️ MongoDB'de bulunamadı: {material_name}, varsayılan kullanılıyor")
                # Varsayılan değerler - yaygın malzemeler için
                if "6061" in material_name.upper():
                    density, price_per_kg = 2.7, 4.5
                elif "7075" in material_name.upper():
                    density, price_per_kg = 2.81, 6.2
                elif "304" in material_name.upper():
                    density, price_per_kg = 7.93, 8.5
                elif "316" in material_name.upper():
                    density, price_per_kg = 7.98, 12.0
                elif "ST37" in material_name.upper() or "S235" in material_name.upper():
                    density, price_per_kg = 7.85, 2.2
                else:
                    density, price_per_kg = 2.7, 4.5
            
        except Exception as db_error:
            print(f"[CALC-MASS] ❌ MongoDB hatası: {db_error}")
            density, price_per_kg = 2.7, 4.5
        
        result['density_used'] = density
        result['price_per_kg_used'] = price_per_kg
        
        # ✅ KÜTLE HESAPLAMA
        mass_kg = (volume_mm3 * density) / 1_000_000
        result['calculated_mass_kg'] = round(mass_kg, 3)
        
        # ✅ MALİYET HESAPLAMA
        material_cost_usd = mass_kg * price_per_kg
        result['calculated_material_cost_usd'] = round(material_cost_usd, 2)
        
        print(f"[CALC-MASS] ✅ Hesaplama tamamlandı: {volume_mm3} mm³ x {density} g/cm³ = {mass_kg:.3f} kg x ${price_per_kg} = ${material_cost_usd:.2f}")
        print(f"[CALC-MASS] 🎯 Seçilen malzeme: {material_name} (confidence: %{best_confidence})")
        
        return result
        
    except Exception as e:
        import traceback
        print(f"[CALC-MASS] ❌ Kütle/maliyet hesaplama hatası: {e}")
        print(f"[CALC-MASS] 📋 Traceback: {traceback.format_exc()}")
        return {
            'calculated_mass_kg': 0.0,
            'calculated_material_cost_usd': 0.0,
            'density_used': 2.7,
            'price_per_kg_used': 4.5,
            'volume_used_mm3': 0.0,
            'material_used': 'Unknown'
        }
    
    
@upload_bp.route('/render-status/<analysis_id>', methods=['GET'])
@jwt_required()
def get_render_status(analysis_id):
    """Render durumunu kontrol et"""
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
        
        # Render durumunu kontrol et
        render_status = analysis.get('render_status', 'none')
        render_task_id = analysis.get('render_task_id')
        
        response = {
            "success": True,
            "render_status": render_status,
            "has_renders": bool(analysis.get('enhanced_renders')),
            "render_count": len(analysis.get('enhanced_renders', {})),
            "stl_generated": analysis.get('stl_generated', False),
            "stl_path": analysis.get('stl_path')
        }
        
        # Task manager'dan detaylı durum al
        if render_task_id:
            from services.background_tasks import task_manager
            task_status = task_manager.get_task_status(render_task_id)
            response["task_status"] = task_status
        
        # Render'lar hazırsa detayları ekle
        if render_status == 'completed' and analysis.get('enhanced_renders'):
            response["renders"] = {}
            for view_name, view_data in analysis['enhanced_renders'].items():
                if view_data.get('success'):
                    response["renders"][view_name] = {
                        "file_path": view_data.get('file_path'),
                        "excel_path": view_data.get('excel_path')
                    }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Durum kontrolü hatası: {str(e)}"
        }), 500
