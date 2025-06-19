# controllers/file_upload_controller.py - PDF 3D VIEWER SUPPORT ADDED

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
                    
                    # PDF için 3D render oluştur
                    isometric_view_path = None
                    if analysis['file_type'] == 'pdf' and result.get('step_analysis'):
                        try:
                            from services.pdf_3d_renderer import generate_pdf_3d_render
                            generated_files = generate_pdf_3d_render(
                                result['step_analysis'], 
                                output_path="static",
                                views=['isometric']
                            )
                            if generated_files:
                                isometric_view_path = generated_files[0]
                                print(f"[INFO] PDF 3D render oluşturuldu: {isometric_view_path}")
                        except Exception as render_error:
                            print(f"[WARN] PDF 3D render hatası: {render_error}")
                    
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
                        "isometric_view": isometric_view_path or result.get('isometric_view'),
                        "processing_log": result.get('processing_log', []),
                        "step_file_hash": result.get('step_file_hash'),
                        "all_material_calculations": result.get('all_material_calculations', []),
                        "material_options": result.get('material_options', [])
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
                            "3d_render_available": bool(isometric_view_path or result.get('isometric_view')),
                            "3d_viewer_ready": bool(result.get('step_analysis'))  # ✅ PDF için 3D viewer desteği
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
            "pdf_3d_support": "PDF'lerden çıkarılan 3D veriler için wireframe görüntüleme"  # ✅ YENİ
        }
    }), 200

# ===== 3D VIEWER ENDPOINTS - PDF DESTEKLİ VERSİYON =====

@upload_bp.route('/wireframe/<analysis_id>', methods=['GET'])
@jwt_required()
def get_wireframe_data(analysis_id):
    """Wireframe data getir - PDF ve STEP desteği ile"""
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
        
        # STEP analizi var mı kontrol et
        step_analysis = analysis.get('step_analysis', {})
        if not step_analysis or step_analysis.get('error'):
            return jsonify({
                "success": False,
                "message": "STEP analizi mevcut değil"
            }), 404
        
        file_type = analysis.get('file_type', 'unknown')
        wireframe_data = None
        
        # Dosya türüne göre wireframe data oluştur
        if file_type == 'step' or file_type == 'stp':
            # STEP dosyası için gerçek wireframe
            file_path = analysis.get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    from services.step_renderer import create_step_wireframe_data
                    wireframe_data = create_step_wireframe_data(file_path)
                except ImportError:
                    wireframe_data = create_simple_wireframe_data(step_analysis)
            
        elif file_type == 'pdf':
            # PDF için step_analysis verilerinden wireframe oluştur
            try:
                from services.pdf_3d_renderer import create_pdf_wireframe_data
                wireframe_data = create_pdf_wireframe_data(step_analysis)
                print(f"[INFO] PDF wireframe data oluşturuldu")
            except ImportError:
                wireframe_data = create_simple_wireframe_data(step_analysis)
                
        else:
            # Diğer dosya türleri için basit wireframe
            wireframe_data = create_simple_wireframe_data(step_analysis)
        
        if wireframe_data:
            return jsonify({
                "success": True,
                "wireframe_data": wireframe_data,
                "step_analysis": step_analysis,
                "file_type": file_type,
                "material_info": {
                    "matches": analysis.get('material_matches', []),
                    "calculations": analysis.get('all_material_calculations', [])
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

def create_simple_wireframe_data(step_analysis):
    """STEP analizi verilerinden basit wireframe data oluştur - FALLBACK"""
    try:
        x = step_analysis.get("X (mm)", 50)
        y = step_analysis.get("Y (mm)", 30) 
        z = step_analysis.get("Z (mm)", 20)
        
        # Silindirik geometri kontrolü
        cyl_diameter = step_analysis.get("Silindirik Çap (mm)")
        cyl_height = step_analysis.get("Silindirik Yükseklik (mm)")
        
        if cyl_diameter and cyl_height:
            # Silindir wireframe
            radius = cyl_diameter / 2
            segments = 16
            vertices = []
            edges = []
            
            # Alt ve üst çember vertices
            for i in range(segments):
                angle = (i / segments) * 2 * 3.14159
                x_pos = radius * np.cos(angle) if 'np' in globals() else radius * (1 if i % 4 == 0 else 0.7 if i % 2 == 0 else 0)
                y_pos = radius * np.sin(angle) if 'np' in globals() else radius * (0 if i % 4 == 0 else 0.7 if i % 2 == 0 else 1)
                vertices.append([x_pos, y_pos, 0])  # Alt çember
                vertices.append([x_pos, y_pos, cyl_height])  # Üst çember
            
            # Kenarlar
            for i in range(segments):
                next_i = (i + 1) % segments
                # Alt çember
                edges.append([i * 2, next_i * 2])
                # Üst çember
                edges.append([i * 2 + 1, next_i * 2 + 1])
                # Dikey bağlantılar
                edges.append([i * 2, i * 2 + 1])
            
            bounding_box = {
                'min': [-radius, -radius, 0],
                'max': [radius, radius, cyl_height],
                'center': [0, 0, cyl_height/2],
                'dimensions': [cyl_diameter, cyl_diameter, cyl_height]
            }
            
            return {
                'vertices': vertices,
                'edges': edges,
                'vertex_count': len(vertices),
                'edge_count': len(edges),
                'bounding_box': bounding_box,
                'geometry_type': 'cylindrical'
            }
        
        else:
            # Basit kutu wireframe
            vertices = [
                [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],  # alt yüz
                [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]   # üst yüz
            ]
            
            edges = [
                # Alt yüz kenarları
                [0, 1], [1, 2], [2, 3], [3, 0],
                # Üst yüz kenarları  
                [4, 5], [5, 6], [6, 7], [7, 4],
                # Dikey kenarlar
                [0, 4], [1, 5], [2, 6], [3, 7]
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
                'geometry_type': 'prismatic'
            }
    except:
        return None

@upload_bp.route('/render/<analysis_id>', methods=['GET'])
@jwt_required()
def get_step_render(analysis_id):
    """Render görüntüsü getir - PDF ve STEP desteği ile"""
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
        
        file_type = analysis.get('file_type', 'unknown')
        step_analysis = analysis.get('step_analysis', {})
        
        # Dosya türüne göre render oluştur
        if file_type == 'step' or file_type == 'stp':
            # STEP dosyası için gerçek render
            file_path = analysis.get('file_path')
            if not file_path or not os.path.exists(file_path):
                return jsonify({
                    "success": False,
                    "message": "STEP dosyası bulunamadı"
                }), 404
            
            try:
                from services.step_renderer import generate_step_views
                rendered_files = generate_step_views(file_path, views=['isometric'])
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "STEP render servisi mevcut değil"
                }), 503
                
        elif file_type == 'pdf':
            # PDF için step_analysis verilerinden render oluştur
            if not step_analysis or step_analysis.get('error'):
                return jsonify({
                    "success": False,
                    "message": "PDF STEP analizi mevcut değil"
                }), 404
            
            try:
                from services.pdf_3d_renderer import generate_pdf_3d_render
                rendered_files = generate_pdf_3d_render(
                    step_analysis, 
                    output_path="static",
                    views=['isometric']
                )
                print(f"[INFO] PDF render oluşturuldu: {len(rendered_files)} dosya")
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "PDF render servisi mevcut değil"
                }), 503
                
        else:
            return jsonify({
                "success": False,
                "message": f"Desteklenmeyen dosya türü: {file_type}"
            }), 400
        
        if rendered_files and len(rendered_files) > 0:
            # Render yolunu kaydet
            FileAnalysis.update_analysis(analysis_id, {
                "isometric_view": rendered_files[0]
            })
            
            return send_file(rendered_files[0], mimetype='image/png')
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

@upload_bp.route('/3d-viewer/<analysis_id>', methods=['GET'])
@jwt_required()
def get_3d_viewer_page(analysis_id):
    """3D viewer sayfası için HTML döndür - PDF ve STEP desteği ile"""
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
        
        # STEP analizi kontrolü
        step_analysis = analysis.get('step_analysis', {})
        if not step_analysis or step_analysis.get('error'):
            return jsonify({
                "success": False,
                "message": "3D görselleştirme için STEP analizi gerekli"
            }), 404
        
        file_type = analysis.get('file_type', 'unknown')
        original_filename = analysis.get('original_filename', 'Unknown')
        
        # 3D viewer HTML'ini döndür
        viewer_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>3D Model Viewer - {original_filename} - EngTeklif</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    margin: 0; 
                    overflow: hidden; 
                    font-family: Arial, sans-serif;
                }}
                iframe {{ 
                    width: 100vw; 
                    height: 100vh; 
                    border: none; 
                }}
                .file-info {{
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background: rgba(0,0,0,0.7);
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    z-index: 1000;
                }}
                .file-type {{
                    background: {'#e74c3c' if file_type == 'pdf' else '#3498db'};
                    padding: 2px 6px;
                    border-radius: 3px;
                    margin-right: 8px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="file-info">
                <span class="file-type">{file_type.upper()}</span>
                {original_filename}
                <br>
                <small>3D Analiz: {step_analysis.get('method', 'unknown')}</small>
            </div>
            <iframe src="/static/3d-viewer.html?analysis_id={analysis_id}&file_type={file_type}"></iframe>
        </body>
        </html>
        '''
        
        return Response(viewer_html, mimetype='text/html')
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"3D viewer hatası: {str(e)}"
        }), 500

@upload_bp.route('/viewer-info/<analysis_id>', methods=['GET'])
@jwt_required()
def get_viewer_info(analysis_id):
    """3D viewer için detaylı bilgi getir"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz kaydı bulunamadı"
            }), 404
        
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu dosyaya erişim yetkiniz yok"
            }), 403
        
        step_analysis = analysis.get('step_analysis', {})
        file_type = analysis.get('file_type', 'unknown')
        
        # Dosya türüne göre bilgi hazırla
        viewer_info = {
            "analysis_id": analysis_id,
            "file_type": file_type,
            "original_filename": analysis.get('original_filename', 'Unknown'),
            "step_analysis": step_analysis,
            "material_matches": analysis.get('material_matches', []),
            "all_material_calculations": analysis.get('all_material_calculations', []),
            "material_options": analysis.get('material_options', []),
            "cost_estimation": analysis.get('cost_estimation', {}),
            "3d_capabilities": {
                "wireframe_available": bool(step_analysis and not step_analysis.get('error')),
                "render_available": bool(analysis.get('isometric_view')),
                "interactive_viewer": True,
                "file_type": file_type,
                "analysis_method": step_analysis.get('method', 'unknown')
            }
        }
        
        return jsonify({
            "success": True,
            "viewer_info": viewer_info
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Viewer bilgi hatası: {str(e)}"
        }), 500

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

# ===== THUMBNAIL ENDPOINT =====

@upload_bp.route('/thumbnail/<analysis_id>', methods=['GET'])
@jwt_required()
def get_analysis_thumbnail(analysis_id):
    """Analiz için küçük thumbnail görüntüsü"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis or analysis['user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Erişim reddedildi"}), 403
        
        file_type = analysis.get('file_type', 'unknown')
        step_analysis = analysis.get('step_analysis', {})
        
        if not step_analysis or step_analysis.get('error'):
            # Varsayılan thumbnail döndür
            default_thumb_path = "static/default_thumbnail.png"
            if os.path.exists(default_thumb_path):
                return send_file(default_thumb_path, mimetype='image/png')
            else:
                return jsonify({"success": False, "message": "Thumbnail mevcut değil"}), 404
        
        # Thumbnail oluştur
        session_id = str(uuid.uuid4())[:8]
        thumb_path = f"static/thumb_{session_id}_{analysis_id}.png"
        
        try:
            if file_type == 'pdf':
                from services.pdf_3d_renderer import create_pdf_thumbnail
                success = create_pdf_thumbnail(step_analysis, thumb_path, size=(200, 150))
            else:
                # STEP thumbnail
                file_path = analysis.get('file_path')
                if file_path and os.path.exists(file_path):
                    from services.step_renderer import generate_step_thumbnail
                    success = generate_step_thumbnail(file_path, thumb_path, size=(200, 150))
                else:
                    success = False
            
            if success and os.path.exists(thumb_path):
                return send_file(thumb_path, mimetype='image/png')
            else:
                return jsonify({"success": False, "message": "Thumbnail oluşturulamadı"}), 500
                
        except ImportError:
            return jsonify({"success": False, "message": "Thumbnail servisi mevcut değil"}), 503
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Thumbnail hatası: {str(e)}"
        }), 500
    
@upload_bp.route('/generate-isometric/<analysis_id>', methods=['POST'])
@jwt_required()
def generate_isometric_view(analysis_id):
    """Analiz için izometrik görünüm oluştur"""
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
        
        # Visualization service'i import et
        from services.visualization_service import generate_isometric_view
        
        # Output path oluştur
        import uuid
        session_id = str(uuid.uuid4())[:8]
        output_filename = f"isometric_{analysis_id}_{session_id}.png"
        output_path = os.path.join("static", output_filename)
        
        # İzometrik görünüm oluştur
        success = generate_isometric_view(analysis, output_path)
        
        if success and os.path.exists(output_path):
            # Dosya yolunu analiz kaydına kaydet
            FileAnalysis.update_analysis(analysis_id, {
                "isometric_view": output_path
            })
            
            return jsonify({
                "success": True,
                "message": "İzometrik görünüm oluşturuldu",
                "image_path": output_path,
                "image_url": f"/static/{output_filename}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "İzometrik görünüm oluşturulamadı"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"İzometrik görünüm hatası: {str(e)}"
        }), 500