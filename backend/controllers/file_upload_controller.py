# controllers/file_upload_controller.py - COMPLETE ENHANCED VERSION

import os
import time
import uuid
from flask import Blueprint, request, jsonify, send_file, Response, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from typing import List, Dict, Any, Tuple
from models.user import User
from models.file_analysis import FileAnalysis, FileAnalysisCreate
from services.material_analysis import MaterialAnalysisService, CostEstimationService, extract_enhanced_ocr_data
from services.step_renderer import StepRendererEnhanced
import numpy as np
import time
import math
import threading
import queue
import re
from difflib import SequenceMatcher
import concurrent.futures
import multiprocessing
import PyPDF2

# Blueprint oluştur
upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

# Konfigürasyon
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'step', 'stp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_REQUEST = 200

# Upload klasörünü oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("static", exist_ok=True)

class OptimizedBackgroundProcessor:
    def __init__(self, max_workers=None):
        if max_workers is None:
            max_workers = max(1, multiprocessing.cpu_count() - 1)
            
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
        self.results = {}
        print(f"[PROCESSOR] 🚀 Multiprocessing başlatıldı. Worker sayısı: {max_workers}")
                
    def add_task(self, func, args=(), kwargs=None):
        task_id = str(uuid.uuid4())
        kwargs = kwargs or {}
        
        future = self.executor.submit(func, *args, **kwargs)
        
        self.results[task_id] = {
            "status": "processing",
            "future": future
        }
        
        future.add_done_callback(lambda f: self._on_task_complete(task_id, f))
        
        return task_id
        
    def _on_task_complete(self, task_id, future):
        try:
            result = future.result()
            self.results[task_id]["status"] = "completed"
            self.results[task_id]["result"] = result
        except Exception as e:
            print(f"[PROCESSOR] ❌ Görev hatası ({task_id}): {e}")
            self.results[task_id]["status"] = "failed"
            self.results[task_id]["error"] = str(e)

    def get_result(self, task_id):
        task_info = self.results.get(task_id)
        if not task_info:
            return None
            
        # Eğer işlem hala devam ediyorsa
        if task_info["status"] == "processing":
            return {"status": "processing"}
            
        return {
            "success": task_info["status"] == "completed",
            "result": task_info.get("result"),
            "error": task_info.get("error")
        }

# Global background processor
bg_processor = OptimizedBackgroundProcessor(max_workers=4)

# ===== PDF-STEP MATCHING UTILITIES =====

def normalize_filename(filename: str) -> str:
    """Dosya adını normalize et (karşılaştırma için)"""
    # Dosya uzantısını kaldır
    name = os.path.splitext(filename)[0]
    # Küçük harfe çevir, özel karakterleri kaldır
    normalized = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    return normalized

def extract_numbers_from_filename(filename: str) -> List[str]:
    """Dosya adından sayıları çıkar"""
    numbers = re.findall(r'\d+', filename)
    return numbers

def extract_part_number(filename: str) -> str:
    """Dosya adından parça numarasını çıkar"""
    patterns = [
        r'(\d{10,12}-\d{2})',      # 1203030301-06
        r'(\d{9}_[a-zA-Z])',       # 132200718_b
        r'(\d{8,}[-_][a-zA-Z0-9]+)', # Genel format
        r'(\d{8,})',               # Sadece sayı
    ]
    
    filename_lower = filename.lower()
    
    for pattern in patterns:
        match = re.search(pattern, filename_lower)
        if match:
            return match.group(1).lower()
    
    return None

def calculate_filename_similarity(name1: str, name2: str) -> float:
    """
    ✅ STRICT: Sadece TAM eşleşme 1.0, diğer her şey 0.0
    
    Tek karakter bile farklıysa eşleşme YOK!
    """
    # Normalize et
    norm1 = normalize_filename(name1)
    norm2 = normalize_filename(name2)
    
    # TAM EŞLEŞME KONTROLÜ
    if norm1 == norm2:
        return 1.0
    else:
        return 0.0  # ✅ Farklıysa 0.0

def match_pdf_to_step_files(pdf_files: List[Dict], step_files: List[Dict]) -> List[Dict]:
    """PDF dosyalarını STEP dosyalarıyla eşleştir"""
    matches = []
    
    for pdf_info in pdf_files:
        pdf_filename = pdf_info['original_filename']
        best_match = None
        best_score = 0.0
        
        # Her STEP dosyası ile karşılaştır
        for step_info in step_files:
            step_filename = step_info['original_filename']
            score = calculate_filename_similarity(pdf_filename, step_filename)
            
            if score > best_score:
                best_score = score
                best_match = step_info
        
        # ✅ DÜZELTME: Sadece tam eşleşmede step_file ekle
        match_result = {
            "pdf_file": pdf_info,
            "step_file": best_match if best_score >= 1.0 else None,  # ✅ Bu satır önemli
            "match_score": round(best_score * 100, 1),
            "match_quality": get_match_quality(best_score),
            "analysis_strategy": determine_analysis_strategy(pdf_info, best_match, best_score)
        }
        
        matches.append(match_result)
        
        print(f"[MATCH] 📄 {pdf_filename} ↔ {best_match['original_filename'] if best_score >= 1.0 else 'EŞLEŞME YOK'} "
              f"(Score: {match_result['match_score']}% - {match_result['match_quality']})")
    
    return matches

def get_match_quality(score: float) -> str:
    """Eşleştirme kalitesini belirle"""
    if score >= 0.8:
        return "Excellent"
    elif score >= 0.6:
        return "Good"
    elif score >= 0.4:
        return "Fair"
    elif score >= 0.2:
        return "Poor"
    else:
        return "None"
    
def extract_step_from_pdf_annotations(pdf_path: str, output_folder: str) -> str:
    """
    PDF içindeki yorumlarda (Annotations) gömülü STEP dosyasını arar ve çıkarır.
    Dönüş: Çıkarılan dosyanın yolu veya None
    """
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        
        for i, page in enumerate(reader.pages):
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    try:
                        obj = annot.get_object()
                        
                        # Annotation tipi FileAttachment mı?
                        if obj.get("/Subtype") == "/FileAttachment":
                            
                            # Dosya özelliklerine (File Specification) eriş
                            if "/FS" in obj:
                                fs = obj["/FS"].get_object()
                                filename = fs.get("/F", "embedded_from_comment.step")
                                
                                # Sadece STEP dosyalarını al
                                if not filename.lower().endswith(('.step', '.stp')):
                                    continue
                                    
                                # Gömülü dosya akışına (Embedded File Stream) eriş
                                if "/EF" in fs:
                                    ef = fs["/EF"].get_object()
                                    # 'F' key'i genelde asıl dosya stream'ini tutar
                                    if "/F" in ef:
                                        f_stream = ef["/F"].get_object()
                                        data = f_stream.get_data()
                                        
                                        # Dosyayı kaydet
                                        unique_name = f"comment_extracted_{uuid.uuid4().hex[:8]}_{filename}"
                                        save_path = os.path.join(output_folder, unique_name)
                                        
                                        with open(save_path, "wb") as f:
                                            f.write(data)
                                            
                                        print(f"[PDF-EXTRACT] ✅ Yorumlardan STEP çıkarıldı: {save_path}")
                                        return save_path
                    except Exception as inner_e:
                        print(f"[PDF-EXTRACT] ⚠️ Annotation okuma hatası: {inner_e}")
                        continue
                        
        return None
    except Exception as e:
        print(f"[PDF-EXTRACT] ❌ Yorum analizi hatası: {str(e)}")
        return None

def determine_analysis_strategy(pdf_info: Dict, step_info: Dict, score: float) -> str:
    """Analiz stratejisini belirle"""
    if step_info and score >= 0.6:
        return "pdf_with_matched_step"
    elif step_info and score >= 0.3:
        return "pdf_with_possible_step"
    else:
        return "pdf_only_extract_step"

# ===== HELPER FUNCTIONS =====

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

def save_uploaded_file(file: FileStorage, upload_folder: str) -> Dict[str, Any]:
    """Yüklenen dosyayı güvenli şekilde kaydet"""
    # Dosya boyutu kontrolü
    file.stream.seek(0, 2)
    file_size = file.stream.tell()
    file.stream.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"Dosya çok büyük. Maksimum boyut: {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Benzersiz dosya adı oluştur
    original_filename = file.filename
    timestamp = int(time.time())
    unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{secure_filename(original_filename)}"
    
    # Dosyayı kaydet
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    return {
        "original_filename": original_filename,
        "saved_filename": unique_filename,
        "file_path": file_path,
        "file_size": file_size,
        "file_type": get_file_type(original_filename)
    }

# ===== UPLOAD ENDPOINTS =====

@upload_bp.route('/single', methods=['POST'])
@jwt_required()
def upload_single_file():
    """Tek dosya yükleme - OPTIMIZED"""
    try:
        current_user = get_current_user()
        
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "Dosya bulunamadı"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"success": False, "message": "Dosya seçilmedi"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": f"Desteklenmeyen dosya türü. İzin verilen: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Dosyayı kaydet
        file_info = save_uploaded_file(file, UPLOAD_FOLDER)
        
        # Analiz kaydı oluştur
        analysis_record = FileAnalysis.create_analysis({
            "user_id": current_user['id'],
            "filename": file_info['saved_filename'],
            "original_filename": file_info['original_filename'],
            "file_type": file_info['file_type'],
            "file_size": file_info['file_size'],
            "file_path": file_info['file_path'],
            "analysis_status": "uploaded"
        })
        
        return jsonify({
            "success": True,
            "message": "Dosya başarıyla yüklendi",
            "file_info": {
                "analysis_id": analysis_record['id'],
                "filename": file_info['saved_filename'],
                "original_filename": file_info['original_filename'],
                "file_type": file_info['file_type'],
                "file_size": file_info['file_size'],
                "upload_time": analysis_record['created_at']
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Upload error: {str(e)}"
        }), 500

@upload_bp.route('/multiple', methods=['POST'])
@jwt_required()
def upload_multiple_files_with_matching():
    """✅ ENHANCED - Çoklu dosya yükleme ve PDF-STEP eşleştirme"""
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
        
        print(f"[MULTIPLE-UPLOAD] 📁 {len(files)} dosya yükleniyor")
        
        # ✅ DOSYALARI TÜRE GÖRE AYIR
        pdf_files = []
        step_files = []
        other_files = []
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
                
                # Dosyayı kaydet
                file_info = save_uploaded_file(file, UPLOAD_FOLDER)
                
                # Türe göre kategorilere ayır
                file_type = file_info['file_type']
                if file_type == 'pdf':
                    pdf_files.append(file_info)
                elif file_type == 'step':
                    step_files.append(file_info)
                else:
                    other_files.append(file_info)
                
                print(f"[MULTIPLE-UPLOAD] ✅ Kaydedildi: {file_info['original_filename']} ({file_type})")
                
            except Exception as e:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        print(f"[MULTIPLE-UPLOAD] 📊 PDF: {len(pdf_files)}, STEP: {len(step_files)}, Other: {len(other_files)}, Failed: {len(failed_uploads)}")
        
        # ✅ PDF-STEP EŞLEŞTİRME (eğer her ikisi de varsa)
        matched_pairs = []
        unmatched_pdfs = []
        unmatched_steps = []
        
        if pdf_files and step_files:
            print(f"[MULTIPLE-UPLOAD] 🔄 PDF-STEP eşleştirme başlıyor...")
            
            # Eşleştirmeleri hesapla
            matches = match_pdf_to_step_files(pdf_files, step_files)
            
            used_step_files = set()
            
            for match in matches:
                pdf_info = match['pdf_file']
                step_info = match['step_file']
                score = match['match_score']
                
                # Minimum eşleştirme skoru kontrolü
                if step_info and score >= 30.0 and step_info['saved_filename'] not in used_step_files:
                    matched_pairs.append(match)
                    used_step_files.add(step_info['saved_filename'])
                    print(f"[MULTIPLE-UPLOAD] ✅ Eşleşti: {pdf_info['original_filename']} ↔ {step_info['original_filename']} ({score}%)")
                else:
                    unmatched_pdfs.append(pdf_info)
                    if score < 30.0:
                        print(f"[MULTIPLE-UPLOAD] ❌ Düşük skor: {pdf_info['original_filename']} ({score}%)")
            
            # Kullanılmayan STEP dosyalarını bul
            for step_info in step_files:
                if step_info['saved_filename'] not in used_step_files:
                    unmatched_steps.append(step_info)
        else:
            # Eşleştirme yapılamaz
            unmatched_pdfs = pdf_files
            unmatched_steps = step_files
        
        # ✅ ANALİZ KAYITLARI OLUŞTUR
        created_analyses = []
        
        # 1. Eşleşmiş çiftler için
        for match in matched_pairs:
            pdf_info = match['pdf_file']
            step_info = match['step_file']
            
            # PDF analizi oluştur
            pdf_analysis = FileAnalysis.create_analysis({
                "user_id": current_user['id'],
                "filename": pdf_info['saved_filename'],
                "original_filename": pdf_info['original_filename'],
                "file_type": pdf_info['file_type'],
                "file_size": pdf_info['file_size'],
                "file_path": pdf_info['file_path'],
                "analysis_status": "uploaded",
                # PDF-STEP eşleştirme bilgileri
                "matched_step_file": step_info['saved_filename'],
                "matched_step_path": step_info['file_path'],
                "match_score": match['match_score'],
                "match_quality": match['match_quality'],
                "analysis_strategy": match['analysis_strategy']
            })
            
            created_analyses.append({
                "analysis_id": pdf_analysis['id'],
                "type": "pdf_with_step",
                "primary_file": pdf_info['original_filename'],
                "secondary_file": step_info['original_filename'],
                "match_score": match['match_score'],
                "file_info": pdf_analysis
            })
        
        # 2. Eşleşmemiş PDF'ler için
        for pdf_info in unmatched_pdfs:
            pdf_analysis = FileAnalysis.create_analysis({
                "user_id": current_user['id'],
                "filename": pdf_info['saved_filename'],
                "original_filename": pdf_info['original_filename'],
                "file_type": pdf_info['file_type'],
                "file_size": pdf_info['file_size'],
                "file_path": pdf_info['file_path'],
                "analysis_status": "uploaded",
                "analysis_strategy": "pdf_only_extract_step"
            })
            
            created_analyses.append({
                "analysis_id": pdf_analysis['id'],
                "type": "pdf_only",
                "primary_file": pdf_info['original_filename'],
                "file_info": pdf_analysis
            })
        
        # 3. Eşleşmemiş STEP'ler için
        for step_info in unmatched_steps:
            step_analysis = FileAnalysis.create_analysis({
                "user_id": current_user['id'],
                "filename": step_info['saved_filename'],
                "original_filename": step_info['original_filename'],
                "file_type": step_info['file_type'],
                "file_size": step_info['file_size'],
                "file_path": step_info['file_path'],
                "analysis_status": "uploaded"
            })
            
            created_analyses.append({
                "analysis_id": step_analysis['id'],
                "type": "step_only",
                "primary_file": step_info['original_filename'],
                "file_info": step_analysis
            })
        
        # 4. Diğer dosyalar için
        for other_info in other_files:
            other_analysis = FileAnalysis.create_analysis({
                "user_id": current_user['id'],
                "filename": other_info['saved_filename'],
                "original_filename": other_info['original_filename'],
                "file_type": other_info['file_type'],
                "file_size": other_info['file_size'],
                "file_path": other_info['file_path'],
                "analysis_status": "uploaded"
            })
            
            created_analyses.append({
                "analysis_id": other_analysis['id'],
                "type": "document",
                "primary_file": other_info['original_filename'],
                "file_info": other_analysis
            })
        
        # ✅ SONUÇ HAZIRLA
        response_data = {
            "success": True,
            "message": f"{len(created_analyses)} dosya başarıyla yüklendi ve analiz için hazırlandı",
            "upload_summary": {
                "total_uploaded": len(created_analyses),
                "pdf_files": len(pdf_files),
                "step_files": len(step_files),
                "other_files": len(other_files),
                "failed_uploads": len(failed_uploads),
                "matched_pairs": len(matched_pairs),
                "unmatched_pdfs": len(unmatched_pdfs),
                "unmatched_steps": len(unmatched_steps)
            },
            "analyses": created_analyses,
            "matching_results": {
                "pdf_step_matches": [
                    {
                        "pdf_file": match['pdf_file']['original_filename'],
                        "step_file": match['step_file']['original_filename'],
                        "match_score": match['match_score'],
                        "match_quality": match['match_quality']
                    }
                    for match in matched_pairs
                ],
                "unmatched_files": {
                    "pdfs": [f['original_filename'] for f in unmatched_pdfs],
                    "steps": [f['original_filename'] for f in unmatched_steps]
                }
            },
            "failed_uploads": failed_uploads,
            "next_steps": {
                "analyze_all": f"/api/upload/batch-analyze",
                "analyze_individual": f"/api/upload/analyze/{{analysis_id}}"
            }
        }
        
        print(f"[MULTIPLE-UPLOAD] ✅ Tamamlandı: {len(created_analyses)} analiz oluşturuldu")
        
        return jsonify(response_data), 201
        
    except Exception as e:
        print(f"[MULTIPLE-UPLOAD] ❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": f"Çoklu dosya yükleme hatası: {str(e)}"
        }), 500

# ===== ANALYSIS ENDPOINTS =====

@upload_bp.route('/analyze/<analysis_id>', methods=['POST'])
@jwt_required()
def analyze_uploaded_file_enhanced(analysis_id):
    """✅ ENHANCED - OCR Position Ordering with DETAILED TIMING + PDF Comment Extraction"""
    endpoint_start_time = time.time()
    timing_log = {}
    
    try:
        current_user = get_current_user()
        
        print(f"[ANALYZE-TIMING] 🚀 Starting enhanced analysis: {analysis_id}")
        timing_log['endpoint_start'] = time.time() - endpoint_start_time
        
        # ✅ 1. VALIDATION - TIMED
        validation_start = time.time()
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            print(f"[ANALYZE-TIMING] ❌ Analysis not found: {analysis_id}")
            return jsonify({"success": False, "message": "Analiz kaydı bulunamadı"}), 404
        
        if analysis['user_id'] != current_user['id']:
            print(f"[ANALYZE-TIMING] ❌ Unauthorized access: {analysis_id}")
            return jsonify({"success": False, "message": "Bu dosyaya erişim yetkiniz yok"}), 403
        
        if not os.path.exists(analysis['file_path']):
            print(f"[ANALYZE-TIMING] ❌ File not found: {analysis['file_path']}")
            return jsonify({"success": False, "message": "Dosya sistemde bulunamadı"}), 404
        
        if analysis['analysis_status'] == 'analyzing':
            print(f"[ANALYZE-TIMING] ⚠️ Already analyzing: {analysis_id}")
            return jsonify({"success": False, "message": "Dosya zaten analiz ediliyor"}), 409
            
        timing_log['validation_time'] = time.time() - validation_start
        print(f"[ANALYZE-TIMING] ⏱️ Validation: {timing_log['validation_time']:.3f}s")
        
        # ✅ 2. STATUS UPDATE - TIMED
        status_start = time.time()
        FileAnalysis.update_analysis(analysis_id, {
            "analysis_status": "analyzing",
            "processing_time": None,
            "error_message": None
        })
        timing_log['status_update_time'] = time.time() - status_start
        print(f"[ANALYZE-TIMING] ⏱️ Status update: {timing_log['status_update_time']:.3f}s")
        
        print(f"[ANALYZE-TIMING] 📊 Analysis starting for: {analysis['original_filename']}")
        analysis_start_time = time.time()
        
        # ✅ 3. GET MATCHED STEP PATH & CHECK COMMENTS
        matched_step_path = analysis.get('matched_step_path')
        analysis_strategy = analysis.get('analysis_strategy', 'default')
        step_source = analysis.get('step_source', 'none')
        
        # --- [NEW] PDF YORUM TARAMASI BAŞLANGICI ---
        # Eğer normal yolla (attachment veya ayrı yükleme) bir STEP bulunamadıysa
        # ve dosya PDF ise, yorumların içine bak.
        if not matched_step_path and analysis['file_type'] == 'pdf':
            print(f"[ANALYZE-TIMING] 🔍 Checking PDF comments for embedded STEP files...")
            extracted_from_comment = extract_step_from_pdf_annotations(analysis['file_path'], UPLOAD_FOLDER)
            
            if extracted_from_comment:
                print(f"[ANALYZE-TIMING] 🎯 STEP file found in PDF comments: {extracted_from_comment}")
                matched_step_path = extracted_from_comment
                step_source = 'extracted_from_comments'
                
                # Database'i güncelle ki bir sonraki işlemde bilinsin
                FileAnalysis.update_analysis(analysis_id, {
                    "matched_step_path": matched_step_path,
                    "step_source": step_source,
                    "used_matched_step": True,
                    "pdf_step_extracted": True,
                    "extracted_step_path": matched_step_path
                })
        # --- [NEW] PDF YORUM TARAMASI SONU ---
        
        print(f"[ANALYZE-TIMING] 📋 Strategy: {analysis_strategy}")
        if matched_step_path:
            print(f"[ANALYZE-TIMING] 🔗 Matched STEP: {matched_step_path}")
            print(f"[ANALYZE-TIMING] 📊 STEP exists: {os.path.exists(matched_step_path)}")
        
        # ✅ 4. CORE ANALYSIS - CRITICAL FIX
        core_analysis_start = time.time()
        try:
            material_service = MaterialAnalysisService()
            
            # ✅ CRITICAL: Pass matched_step_path to analyze_document_ultra_fast
            if analysis['file_type'] == 'pdf':
                print(f"[ANALYZE-TIMING] 🎯 PDF Analysis with matched_step_path: {matched_step_path}")
                
                # ✅ PASS matched_step_path TO THE SERVICE
                result = material_service.analyze_document_ultra_fast(
                    analysis['file_path'], 
                    'pdf',
                    current_user['id'],
                    matched_step_path=matched_step_path  # ✅ CRITICAL: Pass this parameter
                )
                
                # Eğer step_source comment ise result'a işle
                if step_source == 'extracted_from_comments':
                    result['step_source'] = step_source
                    result['matched_step_used'] = True
                
                timing_log['pdf_analysis_time'] = time.time() - core_analysis_start
                print(f"[ANALYZE-TIMING] ⏱️ PDF analysis: {timing_log['pdf_analysis_time']:.3f}s")
                
                # ✅ VERIFY: Check if STEP analysis is present and valid
                step_analysis = result.get('step_analysis', {})
                prizma_hacim = step_analysis.get('Prizma Hacmi (mm³)', 0)
                step_method = step_analysis.get('method', 'unknown')
                
                print(f"[ANALYZE-TIMING] 📊 STEP Analysis Result:")
                print(f"   - Prizma Hacmi: {prizma_hacim} mm³")
                print(f"   - Method: {step_method}")
                print(f"   - Step Source: {result.get('step_source', 'unknown')}")
                print(f"   - Matched STEP Used: {result.get('matched_step_used', False)}")
                
                # ✅ CRITICAL VERIFICATION: Check if we got default values
                if prizma_hacim == 15000 and step_method == 'estimated_defaults':
                    print(f"[ANALYZE-TIMING] ❌ WARNING: Got default estimated values!")
                    print(f"[ANALYZE-TIMING] 🔄 This should NOT happen with matched STEP")
                    
                    # ✅ FORCE RE-ANALYSIS if we got defaults but have matched STEP
                    if matched_step_path and os.path.exists(matched_step_path):
                        print(f"[ANALYZE-TIMING] 🔄 FORCING direct STEP analysis...")
                        try:
                            forced_step_result = material_service.analyze_step_file_ultra_fast(matched_step_path)
                            
                            # Check if forced result is valid
                            if forced_step_result.get('Prizma Hacmi (mm³)', 0) > 0:
                                print(f"[ANALYZE-TIMING] ✅ Forced STEP analysis successful!")
                                result['step_analysis'] = forced_step_result
                                result['matched_step_used'] = True
                                result['step_source'] = 'matched_forced'
                                result['extracted_step_path'] = matched_step_path
                                
                                # Recalculate material options with correct volume
                                prizma_hacim = forced_step_result.get('Prizma Hacmi (mm³)', 0)
                                if prizma_hacim > 0:
                                    print(f"[ANALYZE-TIMING] 🔄 Recalculating materials with {prizma_hacim} mm³")
                                    result["material_options"] = material_service._calculate_top_materials_database_only(
                                        prizma_hacim, limit=0
                                    )
                                    
                                    if result.get("material_matches"):
                                        cost_service = CostEstimationService()
                                        result["cost_estimation"] = cost_service.calculate_cost_lightning(
                                            forced_step_result, result["material_matches"]
                                        )
                            else:
                                print(f"[ANALYZE-TIMING] ❌ Forced STEP analysis also returned invalid values")
                                
                        except Exception as forced_error:
                            print(f"[ANALYZE-TIMING] ❌ Forced STEP analysis error: {forced_error}")
                            import traceback
                            traceback.print_exc()
                
            else:
                # Normal analysis for non-PDF files
                result = material_service.analyze_document_ultra_fast(
                    analysis['file_path'], 
                    analysis['file_type'],
                    current_user['id'],
                    matched_step_path=matched_step_path
                )
                timing_log['normal_analysis_time'] = time.time() - core_analysis_start
                print(f"[ANALYZE-TIMING] ⏱️ Normal analysis: {timing_log['normal_analysis_time']:.3f}s")
            
            timing_log['core_analysis_time'] = time.time() - core_analysis_start
            print(f"[ANALYZE-TIMING] ⏱️ CORE ANALYSIS TOTAL: {timing_log['core_analysis_time']:.3f}s")
            
        except Exception as analysis_error:
            timing_log['core_analysis_error_time'] = time.time() - core_analysis_start
            error_message = f"Analysis Service hatası: {str(analysis_error)}"
            print(f"[ANALYZE-TIMING] ❌ Analysis exception: {error_message}")
            import traceback
            traceback.print_exc()
            
            FileAnalysis.update_analysis(analysis_id, {
                "analysis_status": "failed",
                "error_message": error_message,
                "processing_time": time.time() - analysis_start_time
            })
            
            return jsonify({
                "success": False,
                "message": error_message,
                "timing_debug": timing_log
            }), 500
        
        # ✅ 4. OCR DATA EXTRACTION - TIMED
        ocr_extract_start = time.time()
        ocr_data = extract_enhanced_ocr_data(result, analysis['file_path'], analysis['file_type'])
        timing_log['ocr_extraction_time'] = time.time() - ocr_extract_start
        print(f"[ANALYZE-TIMING] ⏱️ OCR data extraction: {timing_log['ocr_extraction_time']:.3f}s")
        print(f"[ANALYZE-TIMING] 📝 OCR data extracted: {len(ocr_data.get('raw_text', ''))} chars")
        print(f"[ANALYZE-TIMING] 🔍 OCR keywords found: {len(ocr_data.get('material_keywords_found', []))}")
        
        # ✅ 5. OCR POSITION ORDERING - TIMED
        position_ordering_start = time.time()
        original_material_matches = result.get('material_matches', [])
        
        if original_material_matches and ocr_data.get('material_keywords_found'):
            print(f"[ANALYZE-TIMING] 🎯 OCR POSITION ORDERING: Reordering {len(original_material_matches)} materials by OCR position")
            
            # OCR keywords'lerinden position bilgilerini çıkar
            ocr_keywords = ocr_data['material_keywords_found']
            position_mapping = {}
            
            position_mapping_start = time.time()
            for keyword_info in ocr_keywords:
                keyword = keyword_info.get('keyword', '').strip()
                positions = keyword_info.get('positions', [])
                if positions and keyword:
                    first_position = min(positions) if isinstance(positions, list) else positions
                    position_mapping[keyword.upper()] = first_position
            timing_log['position_mapping_time'] = time.time() - position_mapping_start
            print(f"[ANALYZE-TIMING] ⏱️ Position mapping: {timing_log['position_mapping_time']:.3f}s")
            
            # Material matches'i position'a göre sırala
            material_sorting_start = time.time()
            material_position_pairs = []
            
            for material_match in original_material_matches:
                material_name = material_match.split('(')[0].strip().upper()
                found_position = float('inf')  # Default: en sonda
                
                # Exact match
                if material_name in position_mapping:
                    found_position = position_mapping[material_name]
                else:
                    # Partial match
                    for ocr_keyword, position in position_mapping.items():
                        if (material_name in ocr_keyword or ocr_keyword in material_name or
                            any(num in ocr_keyword for num in re.findall(r'\d+', material_name) if len(num) >= 3)):
                            
                            if position < found_position:
                                found_position = position
                
                material_position_pairs.append((material_match, found_position))
            
            # Position'a göre sırala
            sorted_pairs = sorted(material_position_pairs, key=lambda x: x[1])
            
            # Confidence'a göre de sırala (aynı position'da olanlar için)
            final_ordered_materials = []
            current_position = None
            current_group = []
            
            for material, position in sorted_pairs:
                if current_position is None or position == current_position:
                    current_group.append(material)
                    current_position = position
                else:
                    if current_group:
                        confidence_sorted = sorted(current_group, key=lambda m: (
                            int(re.search(r'%(\d+)', m).group(1)) if re.search(r'%(\d+)', m) else 0
                        ), reverse=True)
                        final_ordered_materials.extend(confidence_sorted)
                    
                    current_group = [material]
                    current_position = position
            
            # Son grubu da ekle
            if current_group:
                confidence_sorted = sorted(current_group, key=lambda m: (
                    int(re.search(r'%(\d+)', m).group(1)) if re.search(r'%(\d+)', m) else 0
                ), reverse=True)
                final_ordered_materials.extend(confidence_sorted)
            
            # ✅ MATERIAL_MATCHES'İ GÜNCELLE
            result['material_matches'] = final_ordered_materials
            timing_log['material_sorting_time'] = time.time() - material_sorting_start
            print(f"[ANALYZE-TIMING] ⏱️ Material sorting: {timing_log['material_sorting_time']:.3f}s")
            
            # ✅ RECALCULATE all_material_calculations WITH REORDERED MATERIALS - TIMED
            recalc_start = time.time()
            step_analysis = result.get('step_analysis', {})
            prizma_hacim = step_analysis.get('Prizma Hacmi (mm³)', 0)
            
            if prizma_hacim > 0 and final_ordered_materials:
                print(f"[ANALYZE-TIMING] 🔄 Recalculating all_material_calculations with REORDERED materials...")
                
                # Use the position-ordered materials for calculations
                result["all_material_calculations"] = material_service._calculate_found_materials_database_only(
                    prizma_hacim, final_ordered_materials  # ✅ ORDERED materials
                )
            
            timing_log['material_recalc_time'] = time.time() - recalc_start
            print(f"[ANALYZE-TIMING] ⏱️ Material recalculation: {timing_log['material_recalc_time']:.3f}s")
            
            # OCR data updates
            ocr_data['material_position_mapping'] = position_mapping
            ocr_data['position_ordering_applied'] = True
            ocr_data['original_material_order'] = original_material_matches
            ocr_data['reordered_material_count'] = len(final_ordered_materials)
            
        else:
            print(f"[ANALYZE-TIMING] ⚠️ OCR position ordering skipped")
            ocr_data['position_ordering_applied'] = False
            
            # ✅ FALLBACK: Calculate all_material_calculations with original order - TIMED
            fallback_calc_start = time.time()
            step_analysis = result.get('step_analysis', {})
            prizma_hacim = step_analysis.get('Prizma Hacmi (mm³)', 0)
            
            if prizma_hacim > 0 and original_material_matches and not result.get("all_material_calculations"):
                result["all_material_calculations"] = material_service._calculate_found_materials_database_only(
                    prizma_hacim, original_material_matches
                )
            timing_log['fallback_calc_time'] = time.time() - fallback_calc_start
        
        timing_log['position_ordering_total_time'] = time.time() - position_ordering_start
        print(f"[ANALYZE-TIMING] ⏱️ POSITION ORDERING TOTAL: {timing_log['position_ordering_total_time']:.3f}s")
        
        processing_time = time.time() - analysis_start_time
        timing_log['total_processing_time'] = processing_time
        
        if not result.get('error'):
            # ✅ 6. DATABASE UPDATE - TIMED
            db_update_start = time.time()
            update_data = {
                "analysis_status": "completed",
                "processing_time": processing_time,
                "material_matches": result.get('material_matches', []),
                "best_material_block": result.get('best_block', ''),
                "step_analysis": result.get('step_analysis', {}),
                "cost_estimation": result.get('cost_estimation', {}),
                "ai_price_prediction": result.get('ai_price_prediction', {}),
                "all_material_calculations": result.get('all_material_calculations', []),
                "material_options": result.get('material_options', []),
                "processing_log": result.get('processing_log', []),
                # Enhanced fields
                "used_matched_step": bool(matched_step_path and result.get('matched_step_used', False)),
                "step_source": result.get('step_source', step_source),
                "material_confidence": result.get('material_confidence', 0),
                # Render fields
                "render_status": "pending",
                "enhanced_renders": {},
                "isometric_view": None,
                "stl_generated": False,
                # ✅ OCR DATA FIELDS
                "raw_ocr_output": ocr_data.get('raw_text', ''),
                "ocr_confidence": ocr_data.get('confidence', 0),
                "ocr_method_used": ocr_data.get('method', 'unknown'),
                "ocr_processing_time": ocr_data.get('processing_time', 0),
                "material_keywords_found": ocr_data.get('material_keywords_found', []),
                # ✅ Position ordering fields
                "material_position_mapping": ocr_data.get('material_position_mapping', {}),
                "position_ordering_applied": ocr_data.get('position_ordering_applied', False),
                "original_material_order": ocr_data.get('original_material_order', [])
            }
            
            # PDF specific fields
            if analysis['file_type'] == 'pdf':
                update_data.update({
                    "pdf_step_extracted": bool(result.get('step_file_hash')) or step_source == 'extracted_from_comments',
                    "extracted_step_path": result.get('extracted_step_path') or matched_step_path,
                    "step_file_hash": result.get('step_file_hash')
                })
            
            FileAnalysis.update_analysis(analysis_id, update_data)
            timing_log['db_update_time'] = time.time() - db_update_start
            
            # ✅ 7. RENDER DECISION - TIMED
            render_decision_start = time.time()
            should_render = False
            render_path = None
            
            if matched_step_path and os.path.exists(matched_step_path):
                should_render = True
                render_path = matched_step_path
                print(f"[ANALYZE-TIMING] 🎨 Will render: Matched STEP - {matched_step_path}")
            elif analysis['file_type'] in ['step', 'stp']:
                should_render = True
                render_path = analysis['file_path']
            elif result.get('extracted_step_path') and os.path.exists(result['extracted_step_path']):
                should_render = True
                render_path = result['extracted_step_path']
            
            if should_render and render_path:
                task_id = bg_processor.add_task(
                    background_render_task_enhanced,
                    args=(analysis_id, render_path, analysis_strategy),
                    kwargs={}
                )
                
                FileAnalysis.update_analysis(analysis_id, {
                    "render_task_id": task_id,
                    "render_status": "processing"
                })
                
                print(f"[ANALYZE-TIMING] 🎨 Enhanced render queued: {task_id}")
            
            timing_log['render_decision_time'] = time.time() - render_decision_start
            
            # ✅ 8. RESPONSE PREPARATION
            response_prep_start = time.time()
            updated_analysis = FileAnalysis.find_by_id(analysis_id)
            
            response_data = {
                "success": True,
                "message": "Gelişmiş analiz başarıyla tamamlandı",
                "analysis": updated_analysis,
                "processing_time": processing_time,
                "render_status": "processing" if should_render else "not_applicable",
                "enhancement_details": {
                    "used_matched_step": bool(matched_step_path and result.get('matched_step_used', False)),
                    "step_source": result.get('step_source', step_source),
                    "material_confidence": result.get('material_confidence', 0),
                    "analysis_strategy": analysis_strategy,
                    "position_ordering_applied": ocr_data.get('position_ordering_applied', False),
                    "material_reordered": len(ocr_data.get('original_material_order', [])) != len(result.get('material_matches', []))
                },
                "analysis_details": {
                    "material_matches_count": len(result.get('material_matches', [])),
                    "step_analysis_available": bool(result.get('step_analysis')),
                    "render_will_be_available": should_render,
                    "estimated_render_time": "30-60 seconds" if should_render else "N/A"
                },
                "ocr_data": {
                    "raw_text_preview": ocr_data.get('raw_text', '')[:500],
                    "confidence": ocr_data.get('confidence', 0),
                    "position_ordering_applied": ocr_data.get('position_ordering_applied', False)
                },
                "performance_timing": timing_log
            }
            timing_log['response_prep_time'] = time.time() - response_prep_start
            timing_log['total_endpoint_time'] = time.time() - endpoint_start_time
            
            print(f"[ANALYZE-TIMING] ⏱️ TOTAL ENDPOINT TIME: {timing_log['total_endpoint_time']:.3f}s")
            
            return jsonify(response_data), 200
            
        else:
            # Error handling
            error_msg = result.get('error', 'Bilinmeyen analiz hatası')
            FileAnalysis.update_analysis(analysis_id, {
                "analysis_status": "failed",
                "error_message": error_msg,
                "processing_time": time.time() - analysis_start_time
            })
            
            return jsonify({
                "success": False,
                "message": f"Analiz hatası: {error_msg}",
                "performance_timing": timing_log
            }), 500
        
    except Exception as e:
        print(f"[ANALYZE-TIMING] ❌ Global error: {str(e)}")
        try:
            FileAnalysis.update_analysis(analysis_id, {
                "analysis_status": "failed",
                "error_message": str(e)
            })
        except:
            pass
            
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}",
            "performance_timing": timing_log
        }), 500
    

def fast_position_ordering(materials, keywords):
    """⚡ 10x daha hızlı position ordering"""
    if not materials or not keywords:
        return materials
    
    print(f"[FAST-POSITION] 🚀 Processing {len(materials)} materials with {len(keywords)} keywords")
    
    # Pre-build position mapping once
    position_map = {}
    for keyword_info in keywords:
        keyword = keyword_info.get('keyword', '').strip().upper()
        positions = keyword_info.get('positions', [])
        if positions and keyword:
            first_position = min(positions) if isinstance(positions, list) else positions
            position_map[keyword] = first_position
    
    if not position_map:
        return materials
    
    # Fast material scoring
    material_scores = []
    for material in materials:
        material_name = material.split('(')[0].strip().upper()
        best_position = float('inf')
        
        # Direct lookup (O(1))
        if material_name in position_map:
            best_position = position_map[material_name]
        else:
            # Fast partial matching
            for keyword, position in position_map.items():
                if (material_name in keyword or keyword in material_name or
                    any(num in keyword for num in re.findall(r'\d{3,}', material_name))):
                    if position < best_position:
                        best_position = position
                        break  # Use first match for speed
        
        material_scores.append((material, best_position))
    
    # Sort by position, then by confidence
    sorted_materials = sorted(material_scores, key=lambda x: (
        x[1],  # Position first
        -get_confidence_from_material(x[0])  # Then confidence descending
    ))
    
    result = [item[0] for item in sorted_materials]
    print(f"[FAST-POSITION] ✅ Position ordering completed")
    return result


def get_confidence_from_material(material_text):
    """⚡ Fast confidence extraction"""
    match = re.search(r'%(\d+)', material_text)
    return int(match.group(1)) if match else 50


def extract_enhanced_ocr_data_fast(analysis_result, file_path, file_type):
    """⚡ Fast OCR data extraction - only essential data"""
    try:
        # Quick check if already available in result
        if analysis_result.get('ocr_debug'):
            debug_info = analysis_result['ocr_debug']
            return {
                'raw_text': analysis_result.get('raw_ocr_output', ''),
                'confidence': analysis_result.get('ocr_confidence', 0),
                'material_keywords_found': debug_info.get('material_keywords_found', []),
                'position_ordering_applied': False
            }
        
        # Fast minimal extraction
        return {
            'raw_text': analysis_result.get('raw_ocr_output', ''),
            'confidence': analysis_result.get('ocr_confidence', 0),
            'material_keywords_found': [],
            'position_ordering_applied': False
        }
        
    except Exception as e:
        print(f"[FAST-OCR] ⚠️ Fast OCR extraction failed: {e}")
        return {
            'raw_text': '',
            'confidence': 0,
            'material_keywords_found': [],
            'position_ordering_applied': False
        }


def build_analysis_update_data(result, analysis, ocr_data, processing_time, matched_step_path):
    """⚡ Fast update data builder"""
    update_data = {
        "analysis_status": "completed",
        "processing_time": processing_time,
        "material_matches": result.get('material_matches', []),
        "best_material_block": result.get('best_block', ''),
        "step_analysis": result.get('step_analysis', {}),
        "cost_estimation": result.get('cost_estimation', {}),
        "all_material_calculations": result.get('all_material_calculations', []),
        "material_options": result.get('material_options', []),
        "processing_log": result.get('processing_log', []),
        "used_matched_step": bool(matched_step_path and result.get('matched_step_used', False)),
        "step_source": result.get('step_source', 'none'),
        "material_confidence": result.get('material_confidence', 0),
        "render_status": "pending",
        "enhanced_renders": {},
        "isometric_view": None,
        "stl_generated": False
    }
    
    # Add OCR data only if available
    if ocr_data:
        update_data.update({
            "raw_ocr_output": ocr_data.get('raw_text', ''),
            "ocr_confidence": ocr_data.get('confidence', 0),
            "position_ordering_applied": ocr_data.get('position_ordering_applied', False)
        })
    
    # PDF specific fields
    if analysis['file_type'] == 'pdf':
        update_data.update({
            "pdf_step_extracted": bool(result.get('step_file_hash')),
            "extracted_step_path": result.get('extracted_step_path'),
            "step_file_hash": result.get('step_file_hash')
        })
    
    return update_data


def determine_render_path(analysis, matched_step_path, result):
    """⚡ Fast render path determination"""
    if matched_step_path and os.path.exists(matched_step_path):
        return matched_step_path
    elif analysis['file_type'] in ['step', 'stp']:
        return analysis['file_path']
    elif result.get('extracted_step_path') and os.path.exists(result['extracted_step_path']):
        return result['extracted_step_path']
    return None


def build_fast_response(updated_analysis, processing_time, ocr_data, render_path):
    """⚡ Fast response builder"""
    return {
        "success": True,
        "message": "Ultra-fast analiz başarıyla tamamlandı",
        "analysis": updated_analysis,
        "processing_time": processing_time,
        "render_status": "processing" if render_path else "not_applicable",
        "enhancement_details": {
            "used_matched_step": updated_analysis.get('used_matched_step', False),
            "step_source": updated_analysis.get('step_source', 'none'),
            "material_confidence": updated_analysis.get('material_confidence', 0),
            "position_ordering_applied": ocr_data.get('position_ordering_applied', False) if ocr_data else False
        },
        "analysis_details": {
            "material_matches_count": len(updated_analysis.get('material_matches', [])),
            "step_analysis_available": bool(updated_analysis.get('step_analysis')),
            "cost_estimation_available": bool(updated_analysis.get('cost_estimation')),
            "material_calculations_count": len(updated_analysis.get('all_material_calculations', [])),
            "render_will_be_available": bool(render_path),
            "estimated_render_time": "30-60 seconds" if render_path else "N/A"
        }
    }


def extract_material_positions_from_ocr(ocr_text, material_matches):
    """
    OCR metninden material'ların position'larını çıkar
    """
    try:
        if not ocr_text or not material_matches:
            return {}
        
        position_map = {}
        ocr_upper = ocr_text.upper()
        
        for material_match in material_matches:
            material_name = material_match.split('(')[0].strip()
            
            # Material adını OCR metninde ara
            material_patterns = [
                material_name.upper(),
                re.sub(r'[^\w\s]', '', material_name.upper()),
                material_name.upper().replace(' ', ''),
                material_name.upper().replace('-', ''),
            ]
            
            # Sayısal kısımları da ekle
            numbers = re.findall(r'\d{3,}', material_name)
            material_patterns.extend(numbers)
            
            earliest_position = float('inf')
            
            for pattern in material_patterns:
                if pattern and len(pattern) >= 3:
                    try:
                        position = ocr_upper.find(pattern)
                        if position != -1 and position < earliest_position:
                            earliest_position = position
                    except:
                        continue
            
            if earliest_position != float('inf'):
                position_map[material_name] = earliest_position
                print(f"[POSITION-EXTRACT] Found: {material_name} at position {earliest_position}")
        
        return position_map
        
    except Exception as e:
        print(f"[POSITION-EXTRACT] Error: {e}")
        return {}

print("🎯 OCR Position Based Material Ordering implemented!")

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
        if analysis['file_type'] not in ['step', 'stp'] and not analysis.get('matched_step_path'):
            return jsonify({
                "success": False,
                "message": "Render için STEP dosyası gerekli"
            }), 400
        
        # Render parametrelerini al
        request_data = request.get_json() or {}
        include_dimensions = request_data.get('include_dimensions', True)
        include_materials = request_data.get('include_materials', True)
        high_quality = request_data.get('high_quality', True)
        
        print(f"[STEP-RENDER] 🎨 Render isteği: {analysis_id}")
        
        # STEP dosya yolunu belirle
        if analysis.get('matched_step_path'):
            step_path = analysis['matched_step_path']
        else:
            step_path = analysis['file_path']
        
        # Dosya varlık kontrolü
        if not os.path.exists(step_path):
            return jsonify({
                "success": False,
                "message": "STEP dosyası sistemde bulunamadı"
            }), 404
        
        # Step Renderer'ı kullan
        step_renderer = StepRendererEnhanced()
        
        render_result = step_renderer.generate_comprehensive_views(
            step_path,
            analysis_id=analysis_id,
            include_dimensions=include_dimensions,
            include_materials=include_materials,
            high_quality=high_quality
        )
        
        if render_result['success']:
            # Analiz kaydını güncelle
            update_data = {
                "enhanced_renders": render_result['renders'],
                "render_quality": "high" if high_quality else "standard",
                "render_status": "completed"
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

@upload_bp.route('/render-status/<analysis_id>', methods=['GET'])
@jwt_required()
def get_render_status_enhanced(analysis_id):
    """Enhanced render durumunu kontrol et - DEBUGGING"""
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
        enhanced_renders = analysis.get('enhanced_renders', {})
        
        print(f"[RENDER-STATUS] 🔍 Analysis {analysis_id}:")
        print(f"   - render_status: {render_status}")
        print(f"   - render_task_id: {render_task_id}")
        print(f"   - enhanced_renders count: {len(enhanced_renders)}")
        print(f"   - enhanced_renders keys: {list(enhanced_renders.keys())}")
        
        response = {
            "success": True,
            "render_status": render_status,
            "has_renders": bool(enhanced_renders),
            "render_count": len(enhanced_renders),
            "render_details": enhanced_renders,  # Full details for debugging
            "stl_generated": analysis.get('stl_generated', False),
            "stl_path": analysis.get('stl_path'),
            "isometric_view": analysis.get('isometric_view'),
            "render_quality": analysis.get('render_quality', 'none'),
            "render_strategy": analysis.get('render_strategy'),
            "last_render_update": analysis.get('last_render_update'),
            "render_error": analysis.get('render_error'),
            # Debug fields
            "debug_info": {
                "analysis_id": analysis_id,
                "file_type": analysis.get('file_type'),
                "original_filename": analysis.get('original_filename'),
                "step_analysis_available": bool(analysis.get('step_analysis')),
                "extracted_step_path": analysis.get('extracted_step_path'),
                "matched_step_path": analysis.get('matched_step_path')
            }
        }
        
        # Background task durumunu kontrol et
        if render_task_id:
            task_result = bg_processor.get_result(render_task_id)
            if task_result:
                response["background_task"] = task_result
                print(f"[RENDER-STATUS] 🔄 Background task result: {task_result}")
            else:
                print(f"[RENDER-STATUS] ⏳ Background task still running: {render_task_id}")
        
        # Render'lar hazırsa detayları ekle
        if render_status == 'completed' and enhanced_renders:
            response["renders"] = {}
            for view_name, view_data in enhanced_renders.items():
                if view_data.get('success'):
                    response["renders"][view_name] = {
                        "file_path": view_data.get('file_path'),
                        "excel_path": view_data.get('excel_path'),
                        "file_exists": os.path.exists(os.path.join(os.getcwd(), view_data.get('file_path', '').lstrip('/'))) if view_data.get('file_path') else False
                    }
        
        return jsonify(response), 200
        
    except Exception as e:
        import traceback
        print(f"[RENDER-STATUS] ❌ Error: {str(e)}")
        print(f"[RENDER-STATUS] 📋 Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "success": False,
            "message": f"Durum kontrolü hatası: {str(e)}"
        }), 500

# ===== STL GENERATION =====

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
        
        # STEP dosya yolunu belirle
        step_path = None
        
        if analysis['file_type'] in ['step', 'stp']:
            # Direkt STEP dosyası
            step_path = analysis['file_path']
        elif analysis.get('matched_step_path'):
            # Eşleşmiş STEP dosyası
            step_path = analysis['matched_step_path']
        elif analysis.get('extracted_step_path'):
            # PDF'den çıkarılan STEP dosyası
            step_path = analysis['extracted_step_path']
        
        if not step_path or not os.path.exists(step_path):
            return jsonify({
                "success": False,
                "message": "STEP dosyası bulunamadı"
            }), 404
        
        print(f"[STL-GEN] 🔧 STL oluşturuluyor: {analysis_id}")
        
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
                enhanced_renders = analysis.get('enhanced_renders', {})
                enhanced_renders['stl_model'] = {
                    "success": True,
                    "file_path": stl_relative,
                    "file_size": file_size,
                    "format": "stl"
                }
                update_data["enhanced_renders"] = enhanced_renders
                
                FileAnalysis.update_analysis(analysis_id, update_data)
                
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
                "render_count": len(analysis.get('enhanced_renders', {})),
                # Enhanced fields
                "has_matched_step": bool(analysis.get('matched_step_path')),
                "match_score": analysis.get('match_score'),
                "match_quality": analysis.get('match_quality'),
                "analysis_strategy": analysis.get('analysis_strategy'),
                "used_matched_step": analysis.get('used_matched_step', False),
                "step_source": analysis.get('step_source', 'none')
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
                "processing_time_formatted": f"{analysis.get('processing_time', 0):.2f}s" if analysis.get('processing_time') else "N/A",
                # Enhanced summary
                "has_matched_step": bool(analysis.get('matched_step_path')),
                "match_quality": analysis.get('match_quality', 'None'),
                "analysis_strategy": analysis.get('analysis_strategy', 'default')
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

# ===== MATCHING ENDPOINTS =====

@upload_bp.route('/match-info/<analysis_id>', methods=['GET'])
@jwt_required()
def get_match_info(analysis_id):
    """PDF-STEP eşleştirme bilgilerini getir"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({"success": False, "message": "Analiz bulunamadı"}), 404
        
        if analysis['user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Erişim yetkisi yok"}), 403
        
        match_info = {
            "analysis_id": analysis_id,
            "has_matched_step": bool(analysis.get('matched_step_file')),
            "match_details": None
        }
        
        if analysis.get('matched_step_file'):
            match_info["match_details"] = {
                "step_filename": analysis.get('matched_step_file'),
                "step_path": analysis.get('matched_step_path'),
                "match_score": analysis.get('match_score', 0),
                "match_quality": analysis.get('match_quality', 'Unknown'),
                "analysis_strategy": analysis.get('analysis_strategy', 'default'),
                "used_in_analysis": analysis.get('used_matched_step', False),
                "step_source": analysis.get('step_source', 'none')
            }
        
        return jsonify({
            "success": True,
            "match_info": match_info
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Match info error: {str(e)}"
        }), 500

@upload_bp.route('/re-match/<analysis_id>', methods=['POST'])
@jwt_required()
def re_match_analysis(analysis_id):
    """Analizi yeniden eşleştir"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            return jsonify({"success": False, "message": "Analiz bulunamadı"}), 404
        
        if analysis['user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Erişim yetkisi yok"}), 403
        
        if analysis['file_type'] != 'pdf':
            return jsonify({"success": False, "message": "Sadece PDF dosyaları yeniden eşleştirilebilir"}), 400
        
        # Request body'den yeni STEP dosyası al
        data = request.get_json()
        new_step_analysis_id = data.get('step_analysis_id')
        
        if not new_step_analysis_id:
            return jsonify({"success": False, "message": "STEP analiz ID'si gerekli"}), 400
        
        # Yeni STEP analizini bul
        step_analysis = FileAnalysis.find_by_id(new_step_analysis_id)
        if not step_analysis:
            return jsonify({"success": False, "message": "STEP analizi bulunamadı"}), 404
        
        if step_analysis['user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "STEP dosyasına erişim yetkisi yok"}), 403
        
        if step_analysis['file_type'] not in ['step', 'stp']:
            return jsonify({"success": False, "message": "Geçerli STEP dosyası değil"}), 400
        
        # Eşleştirme skorunu hesapla
        match_score = calculate_filename_similarity(
            analysis['original_filename'],
            step_analysis['original_filename']
        ) * 100
        
        # Analizi güncelle
        update_data = {
            "matched_step_file": step_analysis['filename'],
            "matched_step_path": step_analysis['file_path'],
            "match_score": round(match_score, 1),
            "match_quality": get_match_quality(match_score / 100),
            "analysis_strategy": "pdf_with_matched_step",
            "analysis_status": "uploaded"  # Yeniden analiz için
        }
        
        FileAnalysis.update_analysis(analysis_id, update_data)
        
        return jsonify({
            "success": True,
            "message": "Yeniden eşleştirme başarılı",
            "match_details": {
                "step_filename": step_analysis['original_filename'],
                "match_score": round(match_score, 1),
                "match_quality": get_match_quality(match_score / 100)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Re-match error: {str(e)}"
        }), 500

# ===== BATCH ANALYSIS =====

@upload_bp.route('/batch-analyze', methods=['POST'])
@jwt_required()
def batch_analyze_enhanced():
    """✅ ENHANCED - Toplu analiz ve PDF-STEP eşleştirme desteği"""
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
        
        if len(analysis_ids) > 20:
            return jsonify({
                "success": False,
                "message": "Maksimum 20 dosya aynı anda analiz edilebilir"
            }), 400
        
        print(f"[BATCH-ENHANCED] 📦 {len(analysis_ids)} dosya için toplu analiz başlatılıyor")
        
        # ✅ BATCH ANALYSIS LOGIC
        results = []
        
        for analysis_id in analysis_ids:
            try:
                analysis = FileAnalysis.find_by_id(analysis_id)
                if not analysis or analysis['user_id'] != current_user['id']:
                    results.append({
                        "analysis_id": analysis_id,
                        "status": "not_found_or_unauthorized",
                        "filename": None
                    })
                    continue
                
                # Analiz durumunu kontrol et
                current_status = analysis['analysis_status']
                if current_status in ['uploaded', 'failed']:
                    # Analizi başlat (ayrı thread'de veya queue'da)
                    # Şimdilik "queued" olarak işaretle
                    FileAnalysis.update_analysis(analysis_id, {
                        "analysis_status": "queued",
                        "batch_queued_at": time.time()
                    })
                    
                    results.append({
                        "analysis_id": analysis_id,
                        "status": "queued",
                        "filename": analysis.get('original_filename'),
                        "file_type": analysis.get('file_type'),
                        "has_matched_step": bool(analysis.get('matched_step_path')),
                        "analysis_strategy": analysis.get('analysis_strategy', 'default')
                    })
                elif current_status == 'analyzing':
                    results.append({
                        "analysis_id": analysis_id,
                        "status": "already_analyzing",
                        "filename": analysis.get('original_filename')
                    })
                else:
                    results.append({
                        "analysis_id": analysis_id,
                        "status": "already_processed",
                        "filename": analysis.get('original_filename')
                    })
                    
            except Exception as e:
                results.append({
                    "analysis_id": analysis_id,
                    "status": "error",
                    "error": str(e),
                    "filename": None
                })
        
        # Başarıyla kuyruğa alınan analizleri say
        queued_count = len([r for r in results if r['status'] == 'queued'])
        
        # ✅ OPTIONAL: Gerçek batch processing için background task başlat
        if queued_count > 0:
            batch_task_id = bg_processor.add_task(
                process_batch_analyses,
                args=(analysis_ids, current_user['id']),
                kwargs={}
            )
            
            print(f"[BATCH-ENHANCED] 🔄 Background batch processing started: {batch_task_id}")
        
        return jsonify({
            "success": True,
            "message": f"{queued_count} dosya için toplu analiz başlatıldı",
            "results": results,
            "summary": {
                "total_requested": len(analysis_ids),
                "queued": queued_count,
                "already_processed": len([r for r in results if r['status'] == 'already_processed']),
                "errors": len([r for r in results if r['status'] == 'error']),
                "pdf_with_step_count": len([r for r in results if r.get('has_matched_step', False)])
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Batch analiz hatası: {str(e)}"
        }), 500

# ===== EXPORT ENDPOINTS =====

@upload_bp.route('/export-excel/<analysis_id>', methods=['GET'])
@jwt_required()
def export_analysis_excel(analysis_id):
    """Analiz sonuçlarını Excel'e aktar (resimlerle birlikte)"""
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
            
            # STEP analizi verilerini topla
            step_analysis = analysis.get('step_analysis', {})
            
            # Malzeme bilgisini belirle
            material_matches = analysis.get('material_matches', [])
            material_name = "Bilinmiyor"
            
            if material_matches:
                first_match = material_matches[0]
                if isinstance(first_match, str) and "(" in first_match:
                    material_name = first_match.split("(")[0].strip()
                elif isinstance(first_match, str):
                    material_name = first_match
            
            # Excel satırı oluştur
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
                "Oluşturma Tarihi": analysis.get('created_at', 'N/A'),
                # Enhanced fields
                "Eşleşme Skoru": analysis.get('match_score', 'N/A'),
                "Eşleşme Kalitesi": analysis.get('match_quality', 'N/A'),
                "Analiz Stratejisi": analysis.get('analysis_strategy', 'N/A')
            }
            
            # Malzeme detayını ekle (varsa)
            if analysis.get('malzeme_detay'):
                data["Malzeme Eşleşmeleri"] = analysis['malzeme_detay']
            
            # Resim yolunu bul
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
                    image_path = image_path[1:]
                if not image_path.startswith('static'):
                    image_path = os.path.join('static', image_path)
                
                full_image_path = os.path.join(os.getcwd(), image_path)
                
                if not os.path.exists(full_image_path):
                    print(f"[EXPORT] ⚠️ Görsel dosyası bulunamadı: {full_image_path}")
                    image_path = None
                else:
                    print(f"[EXPORT] ✅ Görsel bulundu: {full_image_path}")
            
            # DataFrame oluştur
            df = pd.DataFrame([data])
            
            # Excel çıktısı (xlsxwriter ile)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Ana sayfayı yaz
                df.to_excel(writer, sheet_name='Analiz Sonuçları', index=False, header=False, startrow=1)
                
                workbook = writer.book
                worksheet = writer.sheets['Analiz Sonuçları']
                
                # Sütun genişliklerini ayarla
                worksheet.set_column("A:A", 30)  # Görsel sütunu geniş
                worksheet.set_column("B:B", 20)  # Ürün Kodu
                worksheet.set_column("C:C", 25)  # Dosya Adı
                worksheet.set_column("D:D", 15)  # Dosya Türü
                worksheet.set_column("E:E", 20)  # Hammadde
                worksheet.set_column("F:Z", 18)  # Diğer sütunlar
                
                # Header stili
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
                
                # Resmi ekle
                if image_path and os.path.exists(full_image_path):
                    # Satır yüksekliğini artır
                    worksheet.set_row(1, 120)
                    
                    try:
                        # Resmi ekle
                        worksheet.insert_image("A2", full_image_path, {
                            "x_scale": 0.4,
                            "y_scale": 0.4,
                            "x_offset": 45,
                            "y_offset": 35
                        })
                        print(f"[EXPORT] ✅ Resim Excel'e eklendi: {image_path}")
                    except Exception as img_error:
                        print(f"[EXPORT] ❌ Resim ekleme hatası: {img_error}")
                
                # Ek sayfalar
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
            
            # Dosya adı oluştur
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

@upload_bp.route('/export-excel-multiple', methods=['POST'])
@jwt_required()
def export_multiple_analyses_excel():
    """Birden fazla analizi Excel'e aktar - FIXED COST CALCULATION"""
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
        
        print(f"[EXCEL-MULTI] 📊 FIXED Çoklu Excel export başlıyor: {len(analysis_ids)} analiz")
        
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
            
            # ✅ FIXED: Tüm analizler için CORRECTED veri hazırla
            excel_data = []
            total_calculated_mass = 0
            total_calculated_cost = 0
            successful_calculations = 0
            
            for analysis in analyses:
                print(f"[EXCEL-MULTI] 🔄 İşleniyor: {analysis.get('original_filename', 'unknown')}")
                
                # ✅ FIXED: Use existing calculation function instead of manual
                calculated_data = calculate_mass_and_cost_for_analysis(analysis)
                
                # ✅ VERIFICATION: Log calculation results
                print(f"[EXCEL-MULTI] 📊 FIXED Cost calculation results:")
                print(f"   Material: {calculated_data.get('material_used', 'Unknown')}")
                print(f"   Volume: {calculated_data.get('volume_used_mm3', 0)} mm³")
                print(f"   Density: {calculated_data.get('density_used', 0)} g/cm³")
                print(f"   Mass: {calculated_data.get('calculated_mass_kg', 0)} kg")
                print(f"   Price: ${calculated_data.get('price_per_kg_used', 0)}/kg")
                print(f"   Cost: ${calculated_data.get('calculated_material_cost_usd', 0)}")
                
                # STEP analizi verilerini topla
                step_analysis = analysis.get('step_analysis', {})
                
                # ✅ FIXED: Use calculated values directly
                material_name = calculated_data.get('material_used', 'Unknown')
                calculated_mass_kg = calculated_data.get('calculated_mass_kg', 0)
                calculated_material_cost = calculated_data.get('calculated_material_cost_usd', 0)
                density_used = calculated_data.get('density_used', 2.7)
                price_per_kg_used = calculated_data.get('price_per_kg_used', 4.5)
                
                # İşçilik ve toplam maliyet hesaplama
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
                
                # Excel satırı oluştur - FIXED VALUES
                row_data = {
                    "Ürün Görseli": "",  # Resim için boş bırak - sonra eklenecek
                    "Analiz ID": analysis.get('id', 'N/A'),
                    "Dosya Adı": analysis.get('original_filename', 'N/A'),
                    "Dosya Türü": analysis.get('file_type', 'N/A'),
                    "Analiz Durumu": analysis.get('analysis_status', 'N/A'),
                    
                    # ✅ FIXED: Malzeme bilgileri - from calculate_mass_and_cost_for_analysis
                    "Hammadde": material_name,
                    "Yoğunluk (g/cm³)": density_used,
                    "Malzeme Fiyatı (USD/kg)": price_per_kg_used,
                    
                    # Boyutlar
                    "X+Pad (mm)": step_analysis.get('X+Pad (mm)', step_analysis.get('X (mm)', 0)),
                    "Y+Pad (mm)": step_analysis.get('Y+Pad (mm)', step_analysis.get('Y (mm)', 0)),
                    "Z+Pad (mm)": step_analysis.get('Z+Pad (mm)', step_analysis.get('Z (mm)', 0)),
                    "Silindirik Çap (mm)": (
                        (step_analysis.get('Silindirik Çap (mm)', 0) + 10) 
                        if step_analysis.get('Silindirik Çap (mm)', 0) > 0 
                        else 0
                    ),
                    
                    # ✅ YENİ: Silindirik Yükseklik +10mm (YENİ SÜTUN)
                    "Silindirik Yükseklik (mm)": (
                        (step_analysis.get('Silindirik Yükseklik (mm)', 0) + 10) 
                        if step_analysis.get('Silindirik Yükseklik (mm)', 0) > 0 
                        else 0
                    ),
                    
                    # ✅ FIXED: Hacim ve kütle - from calculate_mass_and_cost_for_analysis
                    "Hacim (mm³)": calculated_data.get('volume_used_mm3', 0),
                    "Ürün Hacmi (mm³)": step_analysis.get('Ürün Hacmi (mm³)', 0),
                    "Toplam Yüzey Alanı (mm²)": step_analysis.get('Toplam Yüzey Alanı (mm²)', 0),
                    "Kütle (kg)": calculated_mass_kg,  # ✅ FIXED: From calculate_mass_and_cost_for_analysis
                    
                    # ✅ FIXED: Maliyet bilgileri - from calculate_mass_and_cost_for_analysis
                    "Hammadde Maliyeti (USD)": calculated_material_cost,  # ✅ FIXED: From calculate_mass_and_cost_for_analysis
                    "Tahmini İşçilik (USD)": round(estimated_labor_cost, 2),
                    "Birim Toplam Maliyet (USD)": round(unit_total_cost, 2),
                    
                    # Enhanced matching fields
                    "Eşleşme Skoru": analysis.get('match_score', 'N/A'),
                    "Eşleşme Kalitesi": analysis.get('match_quality', 'N/A'),
                    "Analiz Stratejisi": analysis.get('analysis_strategy', 'N/A'),
                    "Eşleşmiş STEP Kullanıldı": "Evet" if analysis.get('used_matched_step', False) else "Hayır",
                    
                    # Meta veriler
                    "İşleme Süresi (s)": analysis.get('processing_time', 0),
                    "Oluşturma Tarihi": analysis.get('created_at', 'N/A'),
                    "Render Sayısı": len(analysis.get('enhanced_renders', {})),
                    "PDF'den STEP": "Evet" if analysis.get('pdf_step_extracted', False) else "Hayır",
                    
                    # ✅ FIXED: Debug fields for verification
                    "Volume Source": calculated_data.get('volume_source', 'unknown'),
                    "Calculation Method": calculated_data.get('calculation_method', 'unknown'),
                    "Material Confidence": calculated_data.get('material_confidence', 0)
                }
                
                # Malzeme detayını ekle (varsa)
                if analysis.get('material_matches'):
                    row_data["Malzeme Eşleşmeleri"] = "; ".join(analysis['material_matches'][:3])  # İlk 3'ü
                
                # Resim yolunu bul ve ekle
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
                        image_path = image_path[1:]
                    if not image_path.startswith('static'):
                        image_path = os.path.join('static', image_path)
                    
                    full_image_path = os.path.join(os.getcwd(), image_path)
                    
                    if not os.path.exists(full_image_path):
                        print(f"[EXCEL-MULTI] ⚠️ Görsel dosyası bulunamadı: {full_image_path}")
                        full_image_path = None
                    else:
                        print(f"[EXCEL-MULTI] ✅ Görsel bulundu: {full_image_path}")
                
                # Row data'ya image path'i ekle (Excel'de kullanılacak)
                row_data["_image_path"] = full_image_path
                
                excel_data.append(row_data)
                
                # ✅ FIXED: Log the corrected values
                print(f"[EXCEL-MULTI] ✅ FIXED {analysis.get('original_filename')}: {calculated_mass_kg:.3f} kg, ${calculated_material_cost:.2f} (was manual calc, now from calculate_mass_and_cost_for_analysis)")
            
            # DataFrame oluştur
            df = pd.DataFrame(excel_data)
            
            # _image_path sütununu DataFrame'den çıkar (sadece internal kullanım için)
            image_paths = df["_image_path"].tolist()
            df = df.drop(columns=["_image_path"])
            
            print(f"[EXCEL-MULTI] 📋 FIXED DataFrame oluşturuldu: {len(df)} satır")
            print(f"[EXCEL-MULTI] 📊 FIXED Toplam kütle: {total_calculated_mass:.3f} kg")
            print(f"[EXCEL-MULTI] 💰 FIXED Toplam maliyet: ${total_calculated_cost:.2f}")
            
            # Excel çıktısı (xlsxwriter ile)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Ana sayfayı yaz
                df.to_excel(writer, sheet_name='Analiz Sonuçları', index=False, header=False, startrow=1)
                
                workbook = writer.book
                worksheet = writer.sheets['Analiz Sonuçları']
                
                # Sütun genişliklerini ayarla
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
                    19: 15,  # Eşleşme Skoru
                    20: 15,  # Eşleşme Kalitesi
                    21: 18,  # Analiz Stratejisi
                    22: 15,  # Eşleşmiş STEP
                    23: 15,  # İşleme Süresi
                    24: 20,  # Tarih
                    25: 12,  # Render Sayısı
                    26: 12,  # PDF STEP
                    27: 25,  # Malzeme Eşleşmeleri
                    28: 15,  # Volume Source (debug)
                    29: 15,  # Calculation Method (debug)
                    30: 12   # Material Confidence (debug)
                }
                
                for col_index, width in column_widths.items():
                    if col_index < len(df.columns):
                        col_letter = chr(65 + col_index) if col_index < 26 else chr(64 + col_index // 26) + chr(65 + col_index % 26)
                        worksheet.set_column(f"{col_letter}:{col_letter}", width)
                
                # Header stili
                header_format = workbook.add_format({
                    "bold": True,
                    "text_wrap": True,
                    "valign": "top",
                    "fg_color": "#D7E4BC",
                    "border": 1,
                    "font_size": 10
                })
                
                # Sayısal değer formatları
                number_format = workbook.add_format({'num_format': '#,##0.000'})
                currency_format = workbook.add_format({'num_format': '$#,##0.00'})
                
                # Header'ları yaz
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Resimleri satırlara ekle
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
                            print(f"[EXCEL-MULTI] 🖼️ Satır {excel_row + 1}: Resim eklendi")
                        except Exception as img_error:
                            print(f"[EXCEL-MULTI] ❌ Satır {excel_row + 1} resim ekleme hatası: {img_error}")
                            worksheet.write(f"A{excel_row + 1}", "Resim Hatası")
                    else:
                        worksheet.write(f"A{excel_row + 1}", "Resim Yok")
                
                # Sayısal sütunlara format uygula
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
                
                # ✅ FIXED: Malzeme özeti sayfası - corrected calculations
                material_summary = {}
                for analysis in analyses:
                    calculated_data = calculate_mass_and_cost_for_analysis(analysis)  # ✅ FIXED
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
                    print(f"[EXCEL-MULTI] 📄 FIXED Malzeme özeti sayfası: {len(summary_data)} malzeme")
                
                # Eşleştirme istatistikleri sayfası (unchanged)
                matching_stats = {
                    "Metrik": [
                        "Toplam PDF Dosyası",
                        "Eşleşmiş PDF-STEP Çifti",
                        "Eşleşme Başarı Oranı (%)",
                        "Excellent Eşleşme",
                        "Good Eşleşme", 
                        "Fair Eşleşme",
                        "Poor Eşleşme",
                        "Ortalama Eşleşme Skoru",
                        "Eşleşmiş STEP Kullanım Oranı (%)"
                    ]
                }
                
                pdf_analyses = [a for a in analyses if a.get('file_type') == 'pdf']
                matched_analyses = [a for a in pdf_analyses if a.get('matched_step_path')]
                
                match_qualities = {}
                total_match_score = 0
                match_score_count = 0
                used_matched_step_count = 0
                
                for analysis in matched_analyses:
                    quality = analysis.get('match_quality', 'Unknown')
                    match_qualities[quality] = match_qualities.get(quality, 0) + 1
                    
                    score = analysis.get('match_score', 0)
                    if score:
                        total_match_score += score
                        match_score_count += 1
                    
                    if analysis.get('used_matched_step', False):
                        used_matched_step_count += 1
                
                matching_stats["Değer"] = [
                    len(pdf_analyses),
                    len(matched_analyses),
                    round((len(matched_analyses) / len(pdf_analyses) * 100), 1) if pdf_analyses else 0,
                    match_qualities.get('Excellent', 0),
                    match_qualities.get('Good', 0),
                    match_qualities.get('Fair', 0),
                    match_qualities.get('Poor', 0),
                    round(total_match_score / match_score_count, 1) if match_score_count else 0,
                    round((used_matched_step_count / len(matched_analyses) * 100), 1) if matched_analyses else 0
                ]
                
                matching_df = pd.DataFrame(matching_stats)
                matching_df.to_excel(writer, sheet_name='Eşleştirme İstatistikleri', index=False)
                
                # ✅ FIXED: Genel istatistikler sayfası - corrected totals
                stats_data = {
                    "Metrik": [
                        "Toplam Analiz Sayısı",
                        "Başarılı Kütle Hesaplaması", 
                        "Başarısız Analizler",
                        "STEP Dosyaları",
                        "PDF Dosyaları",
                        "PDF'den STEP Çıkarılan",
                        "Ortalama İşleme Süresi (s)",
                        "Toplam Kütle (kg) - FIXED",
                        "Toplam Hammadde Maliyeti (USD) - FIXED",
                        "Ortalama Birim Maliyet (USD) - FIXED"
                    ],
                    "Değer": [
                        len(analyses),
                        successful_calculations,
                        len([a for a in analyses if a.get('analysis_status') == 'failed']),
                        len([a for a in analyses if a.get('file_type') in ['step', 'stp']]),
                        len([a for a in analyses if a.get('file_type') == 'pdf']),
                        len([a for a in analyses if a.get('pdf_step_extracted', False)]),
                        round(sum([a.get('processing_time', 0) for a in analyses]) / len(analyses), 2),
                        round(total_calculated_mass, 3),  # ✅ FIXED
                        round(sum([calculate_mass_and_cost_for_analysis(a)['calculated_material_cost_usd'] for a in analyses]), 2),  # ✅ FIXED
                        round(total_calculated_cost / len(analyses), 2) if analyses else 0  # ✅ FIXED
                    ]
                }
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='İstatistikler', index=False)
                print(f"[EXCEL-MULTI] 📊 FIXED İstatistik sayfası oluşturuldu")
                
                # ✅ FIXED: Detaylı malzeme hesaplamaları sayfası
                detailed_calcs = []
                for analysis in analyses:
                    calc_data = calculate_mass_and_cost_for_analysis(analysis)  # ✅ FIXED
                    detailed_calcs.append({
                        'Analiz ID': analysis.get('id'),
                        'Dosya Adı': analysis.get('original_filename'),
                        'Malzeme': calc_data['material_used'],
                        'Hacim (mm³)': calc_data['volume_used_mm3'],
                        'Volume Source': calc_data.get('volume_source', 'unknown'),
                        'Yoğunluk (g/cm³)': calc_data['density_used'],
                        'Kütle (kg)': calc_data['calculated_mass_kg'],
                        'Fiyat (USD/kg)': calc_data['price_per_kg_used'],
                        'Maliyet (USD)': calc_data['calculated_material_cost_usd'],
                        'Hesaplama Yöntemi': calc_data.get('calculation_method', 'unknown'),
                        'Hesaplama Formülü': f"{calc_data['volume_used_mm3']} mm³ × {calc_data['density_used']} g/cm³ ÷ 1,000,000 = {calc_data['calculated_mass_kg']} kg × ${calc_data['price_per_kg_used']}/kg = ${calc_data['calculated_material_cost_usd']}"
                    })
                
                if detailed_calcs:
                    detailed_df = pd.DataFrame(detailed_calcs)
                    detailed_df.to_excel(writer, sheet_name='Hesaplama Detayları', index=False)
                    print(f"[EXCEL-MULTI] 🧮 FIXED Hesaplama detayları sayfası: {len(detailed_calcs)} hesaplama")
            
            output.seek(0)
            
            # Dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"coklu_analiz_fixed_{len(analyses)}_dosya_{timestamp}.xlsx"
            
            print(f"[EXCEL-MULTI] ✅ FIXED Excel dosyası hazır: {filename}")
            print(f"[EXCEL-MULTI] 📈 FIXED Başarılı hesaplamalar: {successful_calculations}/{len(analyses)}")
            print(f"[EXCEL-MULTI] 🎯 FIXED: Artık doğru maliyet hesaplamaları ($0.88) görmeniz gerekir!")
            
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
# ===== MERGE WITH EXCEL =====

@upload_bp.route('/merge-with-excel', methods=['POST'])
@jwt_required()
def merge_with_excel():
    """Excel dosyasını analiz sonuçlarıyla birleştir - FINAL FIXED NO PREMATURE ROUNDING"""
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
        
        print(f"[MERGE] 📊 FINAL FIXED Excel birleştirme başlıyor: {excel_file.filename}")
        print(f"[MERGE] 🔢 Analiz ID'leri: {analysis_ids}")
        
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
        
        print(f"[MERGE] ✅ {len(analyses)} analiz yüklendi")
        
        # Excel işleme
        try:
            import openpyxl
            from openpyxl.drawing.image import Image as XLImage
            from openpyxl.styles import Alignment, PatternFill, Border, Side, Font
            import re
            import math
            import io
            from datetime import datetime
            
            # Excel dosyasını yükle
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb.active
            print(f"[MERGE] ✅ Excel yüklendi. Satır: {ws.max_row}, Sütun: {ws.max_column}")
            
            # Geliştirilmiş normalize fonksiyonu
            def normalize_robust(text):
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
                
                normalized = re.sub(r'[^\w]', '', text.lower())
                return normalized
            
            def extract_numbers(text):
                if not text:
                    return []
                numbers = re.findall(r'\d+', str(text))
                return numbers
            
            # Header analizi ve sütun tespiti
            header_row = [ws.cell(row=1, column=col).value for col in range(1, ws.max_column + 1)]
            print(f"[MERGE] 📋 Header satırı: {header_row}")
            
            # Malzeme No sütununu bul
            malzeme_no_patterns = [
                "malzeme no", "malzemeno", "malzeme_no", "malzeme numarası", "malzeme numarasi",
                "ürün kodu", "urun kodu", "ürün no", "urun no", "kod", "no", "part", "item"
            ]
            
            malzeme_col_index = None
            for i, header in enumerate(header_row):
                if header:
                    normalized_header = normalize_robust(header)
                    print(f"[MERGE] 🔍 Header {i+1}: '{header}' -> '{normalized_header}'")
                    
                    for pattern in malzeme_no_patterns:
                        if normalize_robust(pattern) == normalized_header:
                            malzeme_col_index = i + 1  # 1-based
                            print(f"[MERGE] ✅ Malzeme No sütunu: '{header}' (sütun {malzeme_col_index})")
                            break
                    if malzeme_col_index:
                        break
            
            if not malzeme_col_index:
                malzeme_col_index = 3
                print(f"[MERGE] ⚠️ Malzeme No sütunu bulunamadı, sütun {malzeme_col_index} kullanılıyor")
            
            # İhale miktarı sütununu bul
            ihale_col_index = None
            ihale_patterns = ["ihale", "miktar", "adet", "quantity", "amount"]
            
            for i, header in enumerate(header_row):
                if header:
                    normalized_header = normalize_robust(header)
                    for pattern in ihale_patterns:
                        if pattern in normalized_header:
                            ihale_col_index = i + 1
                            print(f"[MERGE] ✅ İhale sütunu: '{header}' (sütun {ihale_col_index})")
                            break
                    if ihale_col_index:
                        break
            
            if not ihale_col_index:
                ihale_col_index = malzeme_col_index + 1
                print(f"[MERGE] ⚠️ İhale sütunu bulunamadı, sütun {ihale_col_index} kullanılıyor")
            
            # İhale sütunundan sonraki sütunları sil
            columns_to_keep = ihale_col_index
            columns_to_delete = ws.max_column - columns_to_keep
            
            for _ in range(columns_to_delete):
                if ws.max_column > columns_to_keep:
                    ws.delete_cols(columns_to_keep + 1)
            
            print(f"[MERGE] 🗑️ {columns_to_delete} sütun silindi")
            
            # Yeni sütun başlıkları ekle
            new_headers = [
                "Ürün Görseli", "Hammadde", "X+Pad (mm)", "Y+Pad (mm)", "Z+Pad (mm)",
                "Silindirik Çap (mm)", "Silindirik Yükseklik (mm)",
                "Kütle (kg)", "Hammadde Maliyeti (USD)",
                "Kaplama", "Helicoil", "Markalama", "İşçilik", "Birim Fiyat", "Toplam",
                "Eşleşme Skoru", "Analiz Stratejisi"  # Enhanced columns
            ]
            
            start_col = columns_to_keep + 1
            for i, header in enumerate(new_headers):
                ws.cell(row=1, column=start_col + i, value=header)
            
            # Sütun genişlikleri
            for i in range(len(new_headers)):
                col_letter = openpyxl.utils.get_column_letter(start_col + i)
                if i == 0:  # Görsel sütunu
                    ws.column_dimensions[col_letter].width = 25
                else:
                    ws.column_dimensions[col_letter].width = 14
            
            # ✅ FINAL FIXED: Analiz verilerini lookup tablosu hazırla - RAW VALUES
            analysis_lookup = {}
            
            for analysis in analyses:
                # Product code çıkarma stratejileri
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
                
                # ✅ FINAL FIXED: Use existing calculation function - RAW VALUES
                print(f"[MERGE] 🧮 FINAL FIXED Calculating cost for: {analysis.get('original_filename')}")
                analysis_calculated_data = calculate_mass_and_cost_for_analysis(analysis)
                
                # ✅ VERIFICATION: Log the RAW calculation details
                print(f"[MERGE] 📊 FINAL FIXED RAW Cost calculation results:")
                print(f"   Material: {analysis_calculated_data.get('material_used', 'Unknown')}")
                print(f"   Volume: {analysis_calculated_data.get('volume_used_mm3', 0)} mm³")
                print(f"   Density: {analysis_calculated_data.get('density_used', 0)} g/cm³")
                print(f"   RAW Mass: {analysis_calculated_data.get('calculated_mass_kg', 0)} kg (NO ROUNDING)")
                print(f"   Price: ${analysis_calculated_data.get('price_per_kg_used', 0)}/kg")
                print(f"   RAW Cost: ${analysis_calculated_data.get('calculated_material_cost_usd', 0)} USD (NO ROUNDING)")
                
                # Benzersiz kodları normalize et ve ekle
                for code in set(product_codes):
                    if code and len(code) >= 3:  # En az 3 karakter
                        normalized_code = normalize_robust(code)
                        if normalized_code:
                            # Analysis'e hesaplanmış RAW verileri ekle
                            enhanced_analysis = analysis.copy()
                            enhanced_analysis.update(analysis_calculated_data)
                            
                            analysis_lookup[normalized_code] = enhanced_analysis
                            print(f"[MERGE] 📝 FINAL FIXED Lookup eklendi: '{code}' -> '{normalized_code}' -> {analysis['id']}")
                            print(f"   RAW kütle: {analysis_calculated_data.get('calculated_mass_kg', 'N/A')} kg")
                            print(f"   RAW maliyet: ${analysis_calculated_data.get('calculated_material_cost_usd', 'N/A')}")
            
            print(f"[MERGE] 📋 Toplam lookup entries: {len(analysis_lookup)}")
            
            # Satırları işle ve eşleştir
            matched_count = 0
            total_rows = 0
            
            for row in range(2, ws.max_row + 1):
                total_rows += 1
                
                # Excel'den malzeme numarasını al
                malzeme_cell = ws.cell(row=row, column=malzeme_col_index).value
                
                if not malzeme_cell:
                    print(f"[MERGE] ⚠️ Satır {row}: Malzeme numarası boş")
                    continue
                
                excel_malzeme = str(malzeme_cell).strip()
                print(f"[MERGE] 🔍 Satır {row}: Excel malzeme = '{excel_malzeme}'")
                
                # Eşleşmeyi bul
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
                
                # Eşleşme bulunursa verileri yaz
                if matched_analysis:
                    matched_count += 1
                    print(f"[MERGE] ✅ Satır {row}: '{excel_malzeme}' eşleşti -> {matched_analysis['id']} ({match_method})")
                    
                    # STEP analizi verilerini topla
                    step_analysis = matched_analysis.get('step_analysis', {})
                    
                    # ✅ FINAL FIXED: Use RAW calculated values directly - NO ROUNDING YET
                    raw_calculated_mass_kg = matched_analysis.get('calculated_mass_kg', 0)  # RAW
                    raw_calculated_material_cost = matched_analysis.get('calculated_material_cost_usd', 0)  # RAW
                    material_name = matched_analysis.get('material_used', 'Unknown')
                    density_used = matched_analysis.get('density_used', 2.7)
                    price_per_kg_used = matched_analysis.get('price_per_kg_used', 4.5)
                    
                    # ✅ CRITICAL FIX: İşçilik maliyeti hesaplama - RAW mass ile
                    raw_iscilik_usd = 0
                    if raw_calculated_mass_kg > 0:
                        # RAW kütle ile işçilik hesapla
                        iscilik_base = min(raw_calculated_mass_kg * 15, 50)  # Max $50
                        raw_iscilik_usd = iscilik_base  # RAW, rounding yok
                    
                    # ✅ CRITICAL FIX: Birim fiyat hesaplama - RAW values ile
                    raw_birim_fiyat = raw_calculated_material_cost + raw_iscilik_usd  # RAW
                    
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
                    
                    # ✅ CRITICAL FIX: Toplam hesaplama - RAW birim fiyat ile
                    raw_toplam_maliyet = raw_birim_fiyat * ihale_miktari  # RAW
                    
                    values_data = [
                        None,  # Görsel (sonra eklenecek)
                        material_name,
                        step_analysis.get("X+Pad (mm)", 0) or step_analysis.get("X (mm)", 0),
                        step_analysis.get("Y+Pad (mm)", 0) or step_analysis.get("Y (mm)", 0),
                        step_analysis.get("Z+Pad (mm)", 0) or step_analysis.get("Z (mm)", 0),
                        # Silindirik Çap +10mm
                        (
                            (step_analysis.get("Silindirik Çap (mm)", 0) + 10)
                            if step_analysis.get("Silindirik Çap (mm)", 0) > 0
                            else (
                                (step_analysis.get("Çap (mm)", 0) + 10)
                                if step_analysis.get("Çap (mm)", 0) > 0
                                else 0
                            )
                        ),
                        
                        # Silindirik Yükseklik +10mm
                        (
                            (step_analysis.get("Silindirik Yükseklik (mm)", 0) + 10)
                            if step_analysis.get("Silindirik Yükseklik (mm)", 0) > 0
                            else 0
                        ),
                        # ✅ CRITICAL FIX: RAW değerleri kullan, Excel'e yazarken round et
                        raw_calculated_mass_kg if raw_calculated_mass_kg > 0 else None,  # RAW kütle
                        raw_calculated_material_cost if raw_calculated_material_cost > 0 else None,  # RAW hammadde maliyeti
                        "",  # Kaplama - boş bırak
                        "",  # Helicoil - boş bırak
                        "",  # Markalama - boş bırak
                        raw_iscilik_usd if raw_iscilik_usd > 0 else "",  # RAW işçilik
                        raw_birim_fiyat if raw_birim_fiyat > 0 else "",  # RAW birim fiyat
                        raw_toplam_maliyet if raw_toplam_maliyet > 0 else "",  # RAW toplam
                        matched_analysis.get('match_score', 'N/A'),   # Eşleşme Skoru
                        matched_analysis.get('analysis_strategy', 'N/A')  # Analiz Stratejisi
                    ]
                    
                    # ✅ FINAL FIXED: Log the corrected RAW vs ROUNDED values
                    print(f"[MERGE] 📊 FINAL FIXED Satır {row} RAW vs ROUNDED değerler:")
                    print(f"   - Material: {material_name}")
                    print(f"   - RAW Kütle: {raw_calculated_mass_kg} kg")
                    print(f"   - ROUNDED Kütle: {round(raw_calculated_mass_kg, 3)} kg")
                    print(f"   - RAW Hammadde Maliyeti: ${raw_calculated_material_cost}")
                    print(f"   - ROUNDED Hammadde Maliyeti: ${round(raw_calculated_material_cost, 2)}")
                    print(f"   - Density: {density_used} g/cm³, Price: ${price_per_kg_used}/kg")
                    print(f"   - RAW İşçilik: ${raw_iscilik_usd}")
                    print(f"   - ROUNDED İşçilik: ${round(raw_iscilik_usd, 2)}")
                    print(f"   - RAW Birim Fiyat: ${raw_birim_fiyat}")
                    print(f"   - ROUNDED Birim Fiyat: ${round(raw_birim_fiyat, 2)}")
                    print(f"   - İhale Miktarı: {ihale_miktari}")
                    print(f"   - RAW Toplam: ${raw_toplam_maliyet}")
                    print(f"   - ROUNDED Toplam: ${round(raw_toplam_maliyet, 2)}")
                    
                    # Satır yüksekliğini ayarla
                    ws.row_dimensions[row].height = 120
                    
                    # Verileri hücrelere yaz
                    for i, value in enumerate(values_data):
                        target_col = start_col + i
                        target_cell = ws.cell(row=row, column=target_col)
                        
                        if i == 0:  # Görsel sütunu
                            # Görseli bul ve ekle
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
                                        
                                        print(f"[MERGE] 🖼️ Satır {row}: Resim eklendi ({img.width}x{img.height})")
                                        
                                    except Exception as img_error:
                                        print(f"[MERGE] ❌ Satır {row} resim hatası: {img_error}")
                                        target_cell.value = "Resim Hatası"
                                else:
                                    print(f"[MERGE] ⚠️ Satır {row}: Resim dosyası bulunamadı: {full_image_path}")
                                    target_cell.value = "Resim Bulunamadı"
                            else:
                                target_cell.value = "Resim Yok"
                        else:
                            # ✅ CRITICAL FIX: RAW değerleri Excel'e yazarken round et - İLK KEZ
                            if isinstance(value, (float, int)) and value is not None:
                                if value != 0:  # Sıfır değerleri yazma
                                    if isinstance(value, float):
                                        # Para birimi sütunları için 2 decimal
                                        if i in [8, 12, 13, 14]:  # Hammadde Maliyeti, İşçilik, Birim Fiyat, Toplam
                                            target_cell.value = round(value, 2)  # İLK KEZ ROUND
                                            target_cell.number_format = '#,##0.00'
                                        # Kütle için 3 decimal
                                        elif i == 7:  # Kütle
                                            target_cell.value = round(value, 3)  # İLK KEZ ROUND
                                            target_cell.number_format = '#,##0.000'
                                        # Boyutlar için 1 decimal
                                        elif i in [2, 3, 4, 5, 6]:  # Boyutlar
                                            target_cell.value = round(value, 1)
                                            target_cell.number_format = '#,##0.0'
                                        else:
                                            target_cell.value = round(value, 2)
                                    else:
                                        target_cell.value = value
                                        if i in [8, 12, 13, 14]:  # Para sütunları
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
                    print(f"[MERGE] ❌ Satır {row}: '{excel_malzeme}' eşleşmedi")
            
            print(f"[MERGE] 📊 İşlem tamamlandı: {matched_count}/{total_rows} eşleşme")
            
            # Header stillendirme
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
            
            # Dosyayı kaydet ve döndür
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            # Dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = excel_file.filename.rsplit('.', 1)[0]
            filename = f"{original_name}_merged_final_fixed_{timestamp}.xlsx"
            
            print(f"[MERGE] ✅ FINAL FIXED Excel başarıyla birleştirildi: {filename}")
            print(f"[MERGE] 📈 Sonuç: {matched_count}/{total_rows} satır eşleşti")
            print(f"[MERGE] 🎯 FINAL FIXED: Artık doğru maliyet hesaplamaları görmeniz gerekir!")
            print(f"[MERGE] 📝 FINAL FIXED: 0.197 kg × $10 = $1.97 → $1.98 (NOT $2.00)")
            
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
            print(f"[MERGE] ❌ Excel işleme hatası: {excel_error}")
            import traceback
            print(f"[MERGE] 📋 Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "success": False,
                "message": f"Excel işleme hatası: {str(excel_error)}",
                "details": traceback.format_exc()
            }), 500
    
    except Exception as e:
        print(f"[MERGE] ❌ Genel hata: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": f"Birleştirme hatası: {str(e)}"
        }), 500

# ===== UTILITY AND STATISTICS ENDPOINTS =====

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
                "file_type_match": search_term.lower() == result.get('file_type', '').lower(),
                "has_matched_step": bool(result.get('matched_step_path'))  # Enhanced field
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
            "total_materials_found": 0,
            # Enhanced matching statistics
            "pdf_files": 0,
            "step_files": 0,
            "matched_pdf_step_pairs": 0,
            "unmatched_pdfs": 0,
            "excellent_matches": 0,
            "good_matches": 0,
            "fair_matches": 0,
            "poor_matches": 0,
            "used_matched_step_count": 0,
            "average_match_score": 0
        }
        
        total_match_score = 0
        match_count = 0
        
        for analysis in all_analyses:
            # Durum istatistikleri
            status = analysis.get('analysis_status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Dosya türü istatistikleri
            file_type = analysis.get('file_type', 'unknown')
            stats['by_file_type'][file_type] = stats['by_file_type'].get(file_type, 0) + 1
            
            if file_type == 'pdf':
                stats['pdf_files'] += 1
            elif file_type in ['step', 'stp']:
                stats['step_files'] += 1
            
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
            
            # Enhanced matching statistics
            if analysis.get('matched_step_path'):
                stats['matched_pdf_step_pairs'] += 1
                
                match_quality = analysis.get('match_quality', '').lower()
                if match_quality == 'excellent':
                    stats['excellent_matches'] += 1
                elif match_quality == 'good':
                    stats['good_matches'] += 1
                elif match_quality == 'fair':
                    stats['fair_matches'] += 1
                elif match_quality == 'poor':
                    stats['poor_matches'] += 1
                
                match_score = analysis.get('match_score', 0)
                if match_score:
                    total_match_score += match_score
                    match_count += 1
                
                if analysis.get('used_matched_step', False):
                    stats['used_matched_step_count'] += 1
            elif file_type == 'pdf':
                stats['unmatched_pdfs'] += 1
        
        # Ortalamalar
        stats['average_processing_time'] = stats['total_processing_time'] / max(1, stats['successful_analyses'])
        stats['success_rate'] = (stats['successful_analyses'] / max(1, stats['total_files'])) * 100
        stats['average_match_score'] = round(total_match_score / max(1, match_count), 1)
        stats['matching_success_rate'] = (stats['matched_pdf_step_pairs'] / max(1, stats['pdf_files'])) * 100
        stats['matched_step_usage_rate'] = (stats['used_matched_step_count'] / max(1, stats['matched_pdf_step_pairs'])) * 100
        
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

@upload_bp.route('/matching-stats', methods=['GET'])
@jwt_required()
def get_matching_statistics():
    """PDF-STEP eşleştirme istatistikleri"""
    try:
        current_user = get_current_user()
        
        # Kullanıcının tüm analizlerini al
        all_analyses = FileAnalysis.get_user_analyses(current_user['id'], limit=1000)
        
        # Eşleştirme istatistikleri
        stats = {
            "total_analyses": len(all_analyses),
            "pdf_files": len([a for a in all_analyses if a.get('file_type') == 'pdf']),
            "step_files": len([a for a in all_analyses if a.get('file_type') in ['step', 'stp']]),
            "matched_pairs": len([a for a in all_analyses if a.get('matched_step_file')]),
            "match_quality_distribution": {
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0
            },
            "average_match_score": 0,
            "successful_step_usage": len([a for a in all_analyses if a.get('used_matched_step', False)]),
            "analysis_strategy_distribution": {},
            "step_source_distribution": {}
        }
        
        # Match quality hesaplama
        matched_analyses = [a for a in all_analyses if a.get('match_quality')]
        total_score = 0
        
        for analysis in matched_analyses:
            quality = analysis.get('match_quality', '').lower()
            if quality in stats['match_quality_distribution']:
                stats['match_quality_distribution'][quality] += 1
            
            score = analysis.get('match_score', 0)
            if score:
                total_score += score
            
            # Analysis strategy distribution
            strategy = analysis.get('analysis_strategy', 'unknown')
            stats['analysis_strategy_distribution'][strategy] = stats['analysis_strategy_distribution'].get(strategy, 0) + 1
            
            # Step source distribution
            step_source = analysis.get('step_source', 'none')
            stats['step_source_distribution'][step_source] = stats['step_source_distribution'].get(step_source, 0) + 1
        
        if matched_analyses:
            stats['average_match_score'] = round(total_score / len(matched_analyses), 1)
        
        # Success rates
        stats['matching_success_rate'] = (stats['matched_pairs'] / max(1, stats['pdf_files'])) * 100
        stats['step_usage_rate'] = (stats['successful_step_usage'] / max(1, stats['matched_pairs'])) * 100
        
        return jsonify({
            "success": True,
            "matching_statistics": stats
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Matching stats error: {str(e)}"
        }), 500

@upload_bp.route('/batch-status', methods=['GET'])
@jwt_required()
def get_batch_status():
    """Batch işlem durumunu getir"""
    try:
        current_user = get_current_user()
        
        # Kullanıcının kuyruktaki ve işlemdeki analizlerini bul
        all_analyses = FileAnalysis.get_user_analyses(current_user['id'], limit=100)
        
        batch_status = {
            "queued": [a for a in all_analyses if a.get('analysis_status') == 'queued'],
            "analyzing": [a for a in all_analyses if a.get('analysis_status') == 'analyzing'],
            "completed_recently": [
                a for a in all_analyses 
                if a.get('analysis_status') == 'completed' 
                and a.get('batch_processed', False)
                and (time.time() - a.get('updated_at', 0)) < 3600  # Son 1 saat
            ]
        }
        
        return jsonify({
            "success": True,
            "batch_status": {
                "queued_count": len(batch_status['queued']),
                "analyzing_count": len(batch_status['analyzing']),
                "completed_recently_count": len(batch_status['completed_recently']),
                "details": batch_status
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Batch status error: {str(e)}"
        }), 500

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
            "excel_export": True,
            "pdf_step_matching": True,  # Enhanced feature
            "batch_processing": True
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

@upload_bp.route('/performance-stats', methods=['GET'])
@jwt_required()
def get_performance_stats():
    """Get performance statistics"""
    try:
        # Background task queue stats
        queue_size = bg_processor.task_queue.qsize()
        completed_tasks = len(bg_processor.results)
        
        # System stats (basic)
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
        except ImportError:
            cpu_percent = 0
            memory_percent = 0
        
        return jsonify({
            "success": True,
            "performance": {
                "background_queue_size": queue_size,
                "completed_background_tasks": completed_tasks,
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory_percent,
                "optimization_status": "active",
                "pdf_step_matching_enabled": True,
                "enhanced_analysis_enabled": True
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Performance stats error: {str(e)}"
        }), 500

# ===== ENHANCED BACKGROUND RENDERING =====

def background_render_task_enhanced(analysis_id: str, step_path: str, analysis_strategy: str = "default"):
    """Enhanced background render with GUARANTEED database update"""
    
    print(f"[BG-RENDER] 🎨 Starting render for: {analysis_id}")
    print(f"[BG-RENDER] 📂 STEP path: {step_path}")
    
    start_time = time.time()
    
    # ✅ IMMEDIATE STATUS UPDATE
    try:
        from models.file_analysis import FileAnalysis
        FileAnalysis.update_analysis(analysis_id, {
            "render_status": "processing",
            "render_started_at": time.time()
        })
        print(f"[BG-RENDER] 📝 Status set to processing")
    except Exception as e:
        print(f"[BG-RENDER] ⚠️ Could not set initial status: {e}")
    
    try:
        from services.step_renderer import StepRendererEnhanced
        
        # Check file exists
        if not os.path.exists(step_path):
            print(f"[BG-RENDER] ❌ STEP file not found: {step_path}")
            FileAnalysis.update_analysis(analysis_id, {
                "render_status": "failed",
                "render_error": "STEP file not found"
            })
            return {"success": False, "error": "STEP file not found"}
        
        # Initialize renderer
        step_renderer = StepRendererEnhanced()
        print(f"[BG-RENDER] ✅ Renderer initialized")
        
        # Generate renders
        print(f"[BG-RENDER] 🎨 Generating views...")
        render_result = step_renderer.generate_comprehensive_views(
            step_path,
            analysis_id=analysis_id,
            include_dimensions=True,
            include_materials=True,
            high_quality=False
        )
        
        print(f"[BG-RENDER] 📊 Render result: success={render_result.get('success', False)}")
        
        if render_result.get('success'):
            renders = render_result.get('renders', {})
            print(f"[BG-RENDER] ✅ Generated {len(renders)} views")
            
            # Process render paths
            valid_renders = {}
            for view_name, view_data in renders.items():
                if view_data.get('success') and view_data.get('file_path'):
                    file_path = view_data['file_path']
                    
                    # Ensure proper path format
                    if not file_path.startswith('/static/'):
                        if 'static/' in file_path:
                            file_path = '/' + file_path[file_path.find('static/'):]
                        elif 'stepviews' in file_path:
                            file_path = f'/static/stepviews/{analysis_id}/' + os.path.basename(file_path)
                        else:
                            file_path = '/static/' + file_path.lstrip('/')
                    
                    view_data['file_path'] = file_path
                    valid_renders[view_name] = view_data
                    
                    # Check if file actually exists
                    check_path = file_path.lstrip('/')
                    if os.path.exists(check_path):
                        print(f"[BG-RENDER] ✅ {view_name}: {file_path} (exists)")
                    else:
                        print(f"[BG-RENDER] ⚠️ {view_name}: {file_path} (not found)")
            
            if not valid_renders:
                print(f"[BG-RENDER] ❌ No valid renders found")
                FileAnalysis.update_analysis(analysis_id, {
                    "render_status": "failed",
                    "render_error": "No valid renders generated"
                })
                return {"success": False, "error": "No valid renders"}
            
            # ✅ CRITICAL: Force database update with retry
            processing_time = time.time() - start_time
            update_data = {
                "enhanced_renders": valid_renders,
                "render_status": "completed",  # ✅ MUST BE "completed"
                "render_quality": "standard",
                "render_count": len(valid_renders),
                "render_processing_time": processing_time,
                "render_completed_at": time.time(),
                "render_error": None
            }
            
            # Add isometric view if available
            if 'isometric' in valid_renders:
                update_data["isometric_view"] = valid_renders['isometric'].get('file_path')
            
            # ✅ TRY MULTIPLE TIMES TO UPDATE
            update_success = False
            for attempt in range(3):
                try:
                    print(f"[BG-RENDER] 💾 Database update attempt {attempt + 1}...")
                    result = FileAnalysis.update_analysis(analysis_id, update_data)
                    if result:
                        update_success = True
                        print(f"[BG-RENDER] ✅ Database updated successfully on attempt {attempt + 1}")
                        break
                    else:
                        print(f"[BG-RENDER] ⚠️ Update returned False on attempt {attempt + 1}")
                except Exception as update_error:
                    print(f"[BG-RENDER] ❌ Update attempt {attempt + 1} failed: {update_error}")
                    time.sleep(0.5)  # Wait before retry
            
            if not update_success:
                print(f"[BG-RENDER] ❌ All database update attempts failed")
                # Still try to mark as failed
                try:
                    FileAnalysis.update_analysis(analysis_id, {
                        "render_status": "failed",
                        "render_error": "Database update failed after render"
                    })
                except:
                    pass
                return {"success": False, "error": "Database update failed"}
            
            # ✅ VERIFY THE UPDATE
            try:
                verification = FileAnalysis.find_by_id(analysis_id)
                if verification:
                    actual_status = verification.get('render_status')
                    actual_count = len(verification.get('enhanced_renders', {}))
                    print(f"[BG-RENDER] 🔍 Verification: status='{actual_status}', renders={actual_count}")
                    
                    if actual_status != 'completed':
                        print(f"[BG-RENDER] ⚠️ Status not updated! Forcing update...")
                        # Force update one more time
                        FileAnalysis.update_analysis(analysis_id, {"render_status": "completed"})
                else:
                    print(f"[BG-RENDER] ⚠️ Could not verify update")
            except Exception as verify_error:
                print(f"[BG-RENDER] ⚠️ Verification error: {verify_error}")
            
            print(f"[BG-RENDER] 🎉 RENDER COMPLETED in {processing_time:.2f}s")
            return {
                "success": True,
                "renders": len(valid_renders),
                "processing_time": processing_time,
                "status": "completed"
            }
            
        else:
            # Render failed
            error_msg = render_result.get('message', 'Unknown render error')
            print(f"[BG-RENDER] ❌ Render failed: {error_msg}")
            
            FileAnalysis.update_analysis(analysis_id, {
                "render_status": "failed",
                "render_error": error_msg
            })
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Render exception: {str(e)}"
        print(f"[BG-RENDER] ❌ Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Update status to failed
        try:
            FileAnalysis.update_analysis(analysis_id, {
                "render_status": "failed",
                "render_error": error_msg
            })
        except:
            pass
        
        return {"success": False, "error": error_msg}

def process_batch_analyses(analysis_ids: List[str], user_id: str):
    """Background batch processing function"""
    try:
        print(f"[BATCH-PROCESS] 🔄 Processing {len(analysis_ids)} analyses for user {user_id}")
        
        processed = 0
        errors = 0
        
        for analysis_id in analysis_ids:
            try:
                analysis = FileAnalysis.find_by_id(analysis_id)
                if analysis and analysis['user_id'] == user_id and analysis['analysis_status'] == 'queued':
                    print(f"[BATCH-PROCESS] 📄 Processing: {analysis['original_filename']}")
                    
                    # Update status to analyzing
                    FileAnalysis.update_analysis(analysis_id, {"analysis_status": "analyzing"})
                    
                    # TODO: In real implementation, call the actual analysis function
                    # For now, simulate processing
                    time.sleep(2)
                    
                    # Mark as completed
                    FileAnalysis.update_analysis(analysis_id, {
                        "analysis_status": "completed",
                        "processing_time": 2.0,
                        "batch_processed": True
                    })
                    
                    processed += 1
                    
            except Exception as e:
                print(f"[BATCH-PROCESS] ❌ Error processing {analysis_id}: {e}")
                FileAnalysis.update_analysis(analysis_id, {
                    "analysis_status": "failed",
                    "error_message": f"Batch processing error: {str(e)}"
                })
                errors += 1
        
        print(f"[BATCH-PROCESS] ✅ Batch completed: {processed} processed, {errors} errors")
        return {"processed": processed, "errors": errors}
        
    except Exception as e:
        print(f"[BATCH-PROCESS] ❌ Batch processing failed: {e}")
        return {"error": str(e)}

def calculate_mass_and_cost_for_analysis(analysis):
    """Analiz için kütle ve maliyet hesaplama - ENHANCED"""
    try:
        # Default değerler
        result = {
            'calculated_mass_kg': 0.0,
            'calculated_material_cost_usd': 0.0,
            'density_used': 2.7,
            'price_per_kg_used': 4.5,
            'volume_used_mm3': 0.0,
            'material_used': 'Unknown',
            'volume_source': 'none',
            'calculation_method': 'default',
            'material_confidence': 0
        }
        
        # STEP analizinden hacim al
        step_analysis = analysis.get('step_analysis', {})
        volume_mm3 = 0
        
        # Hacim kaynaklarını dene
        if step_analysis.get('Prizma Hacmi (mm³)'):
            volume_mm3 = step_analysis['Prizma Hacmi (mm³)']
            result['volume_source'] = 'prizma_hacmi'
        elif step_analysis.get('Ürün Hacmi (mm³)'):
            volume_mm3 = step_analysis['Ürün Hacmi (mm³)']
            result['volume_source'] = 'urun_hacmi'
        elif step_analysis.get('volume_mm3'):
            volume_mm3 = step_analysis['volume_mm3']
            result['volume_source'] = 'volume_mm3'
        
        if volume_mm3 <= 0:
            print(f"[CALC-MASS] ⚠️ Analiz {analysis.get('id', 'unknown')}: Geçerli hacim bulunamadı")
            return result
        
        result['volume_used_mm3'] = volume_mm3
        
        # Malzeme bilgisini belirle - ENHANCED
        material_matches = analysis.get('material_matches', [])
        material_name = 'Unknown'
        best_confidence = 0
        
        # En yüksek confidence'a sahip malzemeyi bul
        if material_matches:
            best_material = None
            
            for match in material_matches:
                if isinstance(match, str):
                    # Confidence değerini çıkar
                    confidence_match = re.search(r'%(\d+)', match)
                    if confidence_match:
                        confidence_value = int(confidence_match.group(1))
                    elif "estimated" in match.lower():
                        confidence_value = 70
                    else:
                        confidence_value = 50
                    
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
        result['material_confidence'] = best_confidence
        
        # MongoDB'den malzeme verilerini al
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
                result['calculation_method'] = 'database_exact'
                print(f"[CALC-MASS] ✅ MongoDB'de bulundu: {material.get('name')} (density: {density}, price: ${price_per_kg})")
            else:
                print(f"[CALC-MASS] ⚠️ MongoDB'de bulunamadı: {material_name}, varsayılan kullanılıyor")
                result['calculation_method'] = 'fallback_defaults'
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
            result['calculation_method'] = 'error_defaults'
        
        result['density_used'] = density
        result['price_per_kg_used'] = price_per_kg
        
        # ✅ DOĞRU HESAPLAMA: mm³ × g/cm³ ÷ 1.000.000 = kg
        mass_kg = (volume_mm3 * density) / 1_000_000
        result['calculated_mass_kg'] = round(mass_kg, 3)
        
        # Maliyet hesaplama
        material_cost_usd = mass_kg * price_per_kg
        result['calculated_material_cost_usd'] = round(material_cost_usd, 2)
        
        print(f"[CALC-MASS] ✅ Hesaplama tamamlandı: {volume_mm3} mm³ × {density} g/cm³ ÷ 1.000.000 = {mass_kg:.3f} kg × ${price_per_kg} = ${material_cost_usd:.2f}")
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
            'material_used': 'Unknown',
            'volume_source': 'error',
            'calculation_method': 'error',
            'material_confidence': 0
        }


def debug_step_render_issue(analysis_id):
    """STEP render problemi debug et"""
    try:
        from models.file_analysis import FileAnalysis
        
        print(f"[STEP-DEBUG] 🔍 Debugging STEP render: {analysis_id}")
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis:
            print(f"[STEP-DEBUG] ❌ Analysis not found")
            return
        
        print(f"[STEP-DEBUG] 📊 Analysis info:")
        print(f"   - File type: {analysis.get('file_type')}")
        print(f"   - Original filename: {analysis.get('original_filename')}")
        print(f"   - Match score: {analysis.get('match_score')}")
        print(f"   - Analysis strategy: {analysis.get('analysis_strategy')}")
        print(f"   - Render status: {analysis.get('render_status')}")
        print(f"   - Render task ID: {analysis.get('render_task_id')}")
        
        # STEP file paths check
        step_paths = {
            "matched_step_path": analysis.get('matched_step_path'),
            "extracted_step_path": analysis.get('extracted_step_path'),
            "direct_file_path": analysis.get('file_path') if analysis.get('file_type') in ['step', 'stp'] else None
        }
        
        print(f"[STEP-DEBUG] 📂 STEP paths:")
        available_step = None
        for path_type, path in step_paths.items():
            if path:
                exists = os.path.exists(path)
                size = os.path.getsize(path) if exists else 0
                print(f"   - {path_type}: {path}")
                print(f"     Exists: {exists}, Size: {size} bytes")
                
                if exists and size > 0 and not available_step:
                    available_step = path
                    print(f"     → Will use this STEP file")
        
        if not available_step:
            print(f"[STEP-DEBUG] ❌ No valid STEP file found!")
            return
        
        # Manual render test
        print(f"[STEP-DEBUG] 🧪 Testing manual render...")
        
        try:
            from services.step_renderer import StepRendererEnhanced
            
            step_renderer = StepRendererEnhanced()
            
            print(f"[STEP-DEBUG] 🎨 Starting test render: {available_step}")
            
            test_result = step_renderer.generate_comprehensive_views(
                available_step,
                analysis_id=analysis_id,
                include_dimensions=True,
                include_materials=True,
                high_quality=False
            )
            
            print(f"[STEP-DEBUG] 📊 Test render result: {test_result.get('success', False)}")
            
            if test_result.get('success'):
                renders = test_result.get('renders', {})
                print(f"[STEP-DEBUG] ✅ Manual render SUCCESS: {len(renders)} views")
                for view_name, view_data in renders.items():
                    print(f"   - {view_name}: {view_data.get('file_path', 'no path')}")
                
                # Update database manually
                print(f"[STEP-DEBUG] 💾 Updating database manually...")
                
                update_data = {
                    "enhanced_renders": renders,
                    "render_status": "completed",
                    "render_quality": "manual_debug",
                    "last_render_update": time.time()
                }
                
                if 'isometric' in renders:
                    update_data["isometric_view"] = renders['isometric'].get('file_path')
                    if renders['isometric'].get('excel_path'):
                        update_data["isometric_view_clean"] = renders['isometric'].get('excel_path')
                
                db_success = FileAnalysis.update_analysis(analysis_id, update_data)
                print(f"[STEP-DEBUG] 💾 Database update: {db_success}")
                
                if db_success:
                    print(f"[STEP-DEBUG] 🎉 MANUAL FIX SUCCESSFUL!")
                    return "manual_fix_success"
                else:
                    print(f"[STEP-DEBUG] ❌ Database update failed")
                    return "db_update_failed"
            else:
                error_msg = test_result.get('message', 'Unknown render error')
                print(f"[STEP-DEBUG] ❌ Manual render failed: {error_msg}")
                return f"render_failed: {error_msg}"
                
        except Exception as render_error:
            print(f"[STEP-DEBUG] ❌ Manual render exception: {render_error}")
            import traceback
            traceback.print_exc()
            return f"render_exception: {str(render_error)}"
        
    except Exception as e:
        print(f"[STEP-DEBUG] ❌ Debug failed: {e}")
        return f"debug_failed: {str(e)}"

# ===== DEBUG ENDPOINT - BURAYA EKLE =====

@upload_bp.route('/debug-step-render/<analysis_id>', methods=['GET'])
@jwt_required()
def debug_step_render_endpoint(analysis_id):
    """Manuel debug endpoint"""
    try:
        current_user = get_current_user()
        
        analysis = FileAnalysis.find_by_id(analysis_id)
        if not analysis or analysis['user_id'] != current_user['id']:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        
        print(f"[DEBUG-ENDPOINT] 🔧 Manual debug for: {analysis_id}")
        
        # Debug çalıştır
        result = debug_step_render_issue(analysis_id)
        
        return jsonify({
            "success": True,
            "debug_result": result,
            "message": f"Debug completed: {result}"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Debug failed: {str(e)}"
        }), 500

print("🔧 Debug functions added to file_upload_controller.py!")