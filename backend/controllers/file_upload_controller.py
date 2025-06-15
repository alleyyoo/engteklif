# controllers/file_upload_controller.py
import os
import time
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from typing import List, Dict, Any
from models.user import User
from models.file_analysis import FileAnalysis, FileAnalysisCreate
from services.pdf_analysis_service import PDFAnalysisService
from services.material_analysis import MaterialAnalysisService, CostEstimationService

print("[INFO] ✅ Material Analysis servisleri aktif - Full STEP processing mevcut")

upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

# Konfigürasyon
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'step', 'stp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_REQUEST = 10

# Upload klasörünü oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        file.stream.seek(0, 2)  # Dosya sonuna git
        file_size = file.stream.tell()
        file.stream.seek(0)  # Başa dön
        
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
    """Yüklenmiş dosyayı analiz et - Yeni Material Analysis ile"""
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
        
        # Material Analysis Service - Full Active
        try:
            material_service = MaterialAnalysisService()
            
            # Kapsamlı analiz yap
            if analysis['file_type'] in ['pdf', 'document', 'step']:
                result = material_service.analyze_document_comprehensive(
                    analysis['file_path'], 
                    analysis['file_type'],
                    current_user['id']
                )
                
                # Başarılı analiz
                analysis_success = not result.get('error')
                
                if analysis_success:
                    processing_time = time.time() - start_time
                    
                    # Sonuçları güncelle
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
                        "step_file_hash": result.get('step_file_hash')
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
                            "processing_steps": len(result.get('processing_log', []))
                        }
                    }), 200
                    
                else:
                    # Analiz hatası
                    FileAnalysis.update_analysis(analysis_id, {
                        "analysis_status": "failed",
                        "error_message": result.get('error', 'Bilinmeyen analiz hatası'),
                        "processing_time": time.time() - start_time
                    })
                    
                    return jsonify({
                        "success": False,
                        "message": f"Analiz hatası: {result.get('error', 'Bilinmeyen hata')}",
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
            # Full Material Analysis hatası
            error_message = f"Material Analysis hatası: {str(analysis_error)}"
            print(f"[ERROR] {error_message}")
            
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

@upload_bp.route('/material-matches/<analysis_id>', methods=['GET'])
@jwt_required()
def get_material_matches(analysis_id):
    """Analiz sonucu malzeme eşleşmelerini getir"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz bulunamadı"
            }), 404
        
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu analize erişim yetkiniz yok"
            }), 403
        
        if analysis['analysis_status'] != 'completed':
            return jsonify({
                "success": False,
                "message": "Analiz henüz tamamlanmamış",
                "current_status": analysis['analysis_status']
            }), 400
        
        # Malzeme eşleşmeleri ve detayları
        material_matches = analysis.get('material_matches', [])
        step_analysis = analysis.get('step_analysis', {})
        cost_estimation = analysis.get('cost_estimation', {})
        
        # Ek maliyet hesaplamaları
        additional_calculations = []
        if step_analysis.get('volumes'):
            try:
                cost_service = CostEstimationService()
                volume = step_analysis['volumes'].get('bounding_box_mm3', 0)
                
                for match in material_matches:
                    material_name = match.split('(')[0].strip()
                    material_calc = cost_service.calculate_material_cost(volume, material_name)
                    if not material_calc.get('error'):
                        additional_calculations.append({
                            "material": material_name,
                            **material_calc
                        })
            except Exception as e:
                print(f"Additional calculations error: {e}")
        
        return jsonify({
            "success": True,
            "analysis_id": analysis_id,
            "material_matches": material_matches,
            "step_analysis": step_analysis,
            "cost_estimation": cost_estimation,
            "additional_calculations": additional_calculations,
            "processing_info": {
                "processing_time": analysis.get('processing_time'),
                "rotation_count": analysis.get('rotation_count', 0),
                "processing_log": analysis.get('processing_log', [])
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@upload_bp.route('/step-analysis/<analysis_id>', methods=['GET'])
@jwt_required()  
def get_step_analysis(analysis_id):
    """STEP analiz sonuçlarını detaylı getir"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz bulunamadı"
            }), 404
        
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu analize erişim yetkiniz yok"
            }), 403
        
        step_analysis = analysis.get('step_analysis', {})
        if not step_analysis:
            return jsonify({
                "success": False,
                "message": "STEP analizi bulunamadı"
            }), 404
        
        # AI fiyat tahmini ve makine süresi hesaplamaları
        ai_prediction = analysis.get('ai_price_prediction', {})
        
        return jsonify({
            "success": True,
            "analysis_id": analysis_id,
            "step_analysis": step_analysis,
            "ai_price_prediction": ai_prediction,
            "isometric_view": analysis.get('isometric_view'),
            "file_info": {
                "original_filename": analysis.get('original_filename'),
                "file_type": analysis.get('file_type'),
                "step_file_hash": analysis.get('step_file_hash')
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@upload_bp.route('/recalculate-cost/<analysis_id>', methods=['POST'])
@jwt_required()
def recalculate_cost(analysis_id):
    """Malzeme değiştirerek maliyeti yeniden hesapla"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        if not data or 'material_name' not in data:
            return jsonify({
                "success": False,
                "message": "Malzeme adı gerekli"
            }), 400
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({
                "success": False,
                "message": "Analiz bulunamadı"
            }), 404
        
        if analysis['user_id'] != current_user['id']:
            return jsonify({
                "success": False,
                "message": "Bu analize erişim yetkiniz yok"
            }), 403
        
        step_analysis = analysis.get('step_analysis', {})
        if not step_analysis:
            return jsonify({
                "success": False,
                "message": "STEP analizi bulunamadı"
            }), 404
        
        # Yeni malzeme ile maliyet hesaplama
        material_name = data['material_name']
        hourly_rate = data.get('hourly_rate', 65)  # Default $65/hour
        
        cost_service = CostEstimationService()
        
        # Tek malzeme listesi oluştur
        material_matches = [f"{material_name} (%100)"]
        
        new_cost_estimation = cost_service.calculate_comprehensive_cost(
            step_analysis, 
            material_matches, 
            hourly_rate
        )
        
        # Güncellenen maliyet tahminini kaydet
        FileAnalysis.update_analysis(analysis_id, {
            "cost_estimation": new_cost_estimation,
            "selected_material": material_name,
            "hourly_rate": hourly_rate
        })
        
        return jsonify({
            "success": True,
            "message": "Maliyet yeniden hesaplandı",
            "cost_estimation": new_cost_estimation,
            "selected_material": material_name,
            "hourly_rate": hourly_rate
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Maliyet hesaplama hatası: {str(e)}"
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
            "visual_rendering": "STEP dosyası görselleştirme"
        }
    }), 200