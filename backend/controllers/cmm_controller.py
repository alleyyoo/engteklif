# backend/controllers/cmm_controller.py
"""
CMM (Coordinate Measuring Machine) API controller
RTF dosya yükleme ve işleme endpoint'leri
"""

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import sys
import tempfile
import traceback
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from utils.database import db
from bson import ObjectId

# CMM Service'i import et
try:
    from services.cmm_service import CMMService
except ImportError:
    print("❌ CMM Service modülü bulunamadı!")
    print("   cmm_service.py dosyasını backend/services/ klasörüne yerleştirin")
    raise ImportError("CMM Service modülü bulunamadı")

cmm_bp = Blueprint('cmm', __name__, url_prefix='/api/cmm')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'rtf', 'RTF'}

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_PER_UPLOAD = 50

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def save_uploaded_file(file, upload_folder):
    """Save uploaded file and return path"""
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    return file_path, unique_filename

@cmm_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_cmm_files():
    """
    CMM RTF dosyalarını yükle ve işle
    
    Request:
        - files: RTF dosya listesi (multipart/form-data)
    
    Response:
        - success: boolean
        - analysis_id: string (başarılı ise)
        - data: işlem sonucu verileri
        - message: durum mesajı
    """
    try:
        user_id = get_jwt_identity()
        
        # Dosya kontrolü
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Dosya bulunamadı'
            }), 400
        
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({
                'success': False,
                'message': 'En az bir dosya seçilmelidir'
            }), 400
        
        # Dosya sayısı kontrolü
        if len(files) > MAX_FILES_PER_UPLOAD:
            return jsonify({
                'success': False,
                'message': f'En fazla {MAX_FILES_PER_UPLOAD} dosya yüklenebilir'
            }), 400
        
        # Dosya türü ve boyut kontrolü
        invalid_files = []
        for file in files:
            if not file or file.filename == '':
                invalid_files.append('Boş dosya adı')
            elif not allowed_file(file.filename):
                invalid_files.append(f'{file.filename} - Sadece RTF dosyaları desteklenir')
            elif file.content_length > MAX_FILE_SIZE:
                invalid_files.append(f'{file.filename} - Dosya boyutu çok büyük (max {MAX_FILE_SIZE//1024//1024}MB)')
        
        if invalid_files:
            return jsonify({
                'success': False,
                'message': 'Geçersiz dosyalar',
                'invalid_files': invalid_files
            }), 400
        
        # Upload folder oluştur
        upload_folder = os.path.join('uploads', 'cmm', user_id)
        uploaded_files = []
        file_paths = []
        
        # Dosyaları kaydet
        print(f"📁 {len(files)} dosya yükleniyor...")
        for file in files:
            try:
                file_path, unique_filename = save_uploaded_file(file, upload_folder)
                file_paths.append(file_path)
                uploaded_files.append({
                    'original_name': file.filename,
                    'saved_name': unique_filename,
                    'file_path': file_path,
                    'file_size': os.path.getsize(file_path)
                })
                print(f"✅ Yüklendi: {file.filename} → {unique_filename}")
            except Exception as e:
                # Önceki dosyaları temizle
                for fp in file_paths:
                    if os.path.exists(fp):
                        os.remove(fp)
                
                return jsonify({
                    'success': False,
                    'message': f'Dosya kaydedilemedi: {str(e)}'
                }), 500
        
        # Excel output path oluştur
        output_folder = os.path.join('static', 'cmm_exports', user_id)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f'cmm_raporu_{len(files)}dosya_{timestamp}.xlsx'
        excel_path = os.path.join(output_folder, excel_filename)
        
        # CMM Service ile dosyaları işle
        print(f"🔄 CMM işleme başlıyor...")
        cmm_service = CMMService()
        result = cmm_service.process_files(file_paths, excel_path)
        
        if not result['success']:
            # Hata durumunda yüklenen dosyaları temizle
            for fp in file_paths:
                if os.path.exists(fp):
                    os.remove(fp)
            
            return jsonify({
                'success': False,
                'message': result.get('error', 'CMM işleme başarısız'),
                'debug_info': {
                    'file_count': len(file_paths),
                    'error_details': result.get('error', 'Bilinmeyen hata')
                }
            }), 500
        
        # Sonuçları veritabanına kaydet
        cmm_analysis = {
            'user_id': user_id,
            'analysis_id': f"cmm_{user_id}_{timestamp}",
            'uploaded_files': uploaded_files,
            'file_count': len(files),
            'operations': result.get('operations', []),
            'measurement_count': result.get('count', 0),
            'excel_path': excel_path,
            'excel_filename': excel_filename,
            'status': 'completed',
            'created_at': datetime.utcnow(),
            'processing_summary': {
                'total_files': len(files),
                'successful_files': len(uploaded_files),
                'total_measurements': result.get('count', 0),
                'operations_found': result.get('operations', []),
                'summary': result.get('summary', {})
            }
        }
        
        # MongoDB'ye kaydet
        db_result = db.get_db().cmm_analyses.insert_one(cmm_analysis)
        analysis_id = str(db_result.inserted_id)
        
        # Upload edilen dosyaları temizle
        try:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
            print(f"🗑️ Geçici dosyalar temizlendi")
        except Exception as e:
            print(f"⚠️ Geçici dosyalar temizlenemedi: {e}")
        
        # Başarılı yanıt
        return jsonify({
            'success': True,
            'message': f'✅ {len(files)} CMM dosyası başarıyla işlendi',
            'analysis_id': analysis_id,
            'data': {
                'file_count': len(files),
                'measurement_count': result.get('count', 0),
                'operations': result.get('operations', []),
                'excel_available': True,
                'excel_filename': excel_filename,
                'excel_download_url': f'/api/cmm/download/{analysis_id}',
                'processing_time': '< 5 saniye',
                'summary': result.get('summary', {})
            },
            'upload_summary': {
                'total_uploaded': len(uploaded_files),
                'total_measurements': result.get('count', 0),
                'operations_detected': result.get('operations', []),
                'excel_generated': True,
                'success_rate': result.get('summary', {}).get('success_rate', 0)
            }
        })
        
    except Exception as e:
        print(f"❌ CMM upload hatası: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'CMM işleme hatası: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@cmm_bp.route('/download/<analysis_id>', methods=['GET'])
@jwt_required()
def download_cmm_excel(analysis_id):
    """
    CMM analiz sonucu Excel dosyasını indir
    
    Args:
        analysis_id: Analiz ID'si
        
    Returns:
        Excel dosyası veya hata mesajı
    """
    try:
        user_id = get_jwt_identity()
        
        # Analiz kaydını bul
        analysis = db.get_db().cmm_analyses.find_one({
            '_id': ObjectId(analysis_id),
            'user_id': user_id
        })
        
        if not analysis:
            return jsonify({
                'success': False,
                'message': 'CMM analizi bulunamadı'
            }), 404
        
        excel_path = analysis.get('excel_path')
        if not excel_path or not os.path.exists(excel_path):
            return jsonify({
                'success': False,
                'message': 'Excel dosyası bulunamadı'
            }), 404
        
        excel_filename = analysis.get('excel_filename', 'cmm_raporu.xlsx')
        
        # İndirme kaydı ekle
        db.get_db().cmm_analyses.update_one(
            {'_id': ObjectId(analysis_id)},
            {
                '$push': {
                    'download_history': {
                        'downloaded_at': datetime.utcnow(),
                        'user_id': user_id
                    }
                },
                '$inc': {'download_count': 1}
            }
        )
        
        return send_file(
            excel_path,
            as_attachment=True,
            download_name=excel_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"❌ CMM download hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'İndirme hatası: {str(e)}'
        }), 500

@cmm_bp.route('/my-analyses', methods=['GET'])
@jwt_required()
def get_my_cmm_analyses():
    """
    Kullanıcının CMM analizlerini listele
    
    Query Parameters:
        - page: Sayfa numarası (default: 1)
        - limit: Sayfa başına kayıt (default: 20)
        - operation: Operasyon filtresi (opsiyonel)
        - date_from: Başlangıç tarihi (opsiyonel)
        - date_to: Bitiş tarihi (opsiyonel)
        
    Returns:
        Analiz listesi ve sayfalama bilgileri
    """
    try:
        user_id = get_jwt_identity()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Filtreler
        filters = {'user_id': user_id}
        
        # Operasyon filtresi
        operation = request.args.get('operation')
        if operation:
            filters['operations'] = operation
        
        # Tarih filtresi
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        if date_from or date_to:
            date_filter = {}
            if date_from:
                date_filter['$gte'] = datetime.fromisoformat(date_from)
            if date_to:
                date_filter['$lte'] = datetime.fromisoformat(date_to)
            if date_filter:
                filters['created_at'] = date_filter
        
        # MongoDB'den kullanıcının analizlerini al
        skip = (page - 1) * limit
        analyses = list(db.get_db().cmm_analyses.find(filters)
                       .sort('created_at', -1)
                       .skip(skip)
                       .limit(limit))
        
        # ObjectId'leri string'e çevir ve ek bilgiler ekle
        for analysis in analyses:
            analysis['_id'] = str(analysis['_id'])
            analysis['created_at'] = analysis['created_at'].isoformat()
            
            # Excel dosya durumu
            excel_path = analysis.get('excel_path')
            analysis['excel_exists'] = bool(excel_path and os.path.exists(excel_path))
            
            # İndirme sayısı
            analysis['download_count'] = analysis.get('download_count', 0)
        
        total_count = db.get_db().cmm_analyses.count_documents(filters)
        
        return jsonify({
            'success': True,
            'analyses': analyses,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            },
            'filters_applied': {
                'operation': operation,
                'date_from': date_from,
                'date_to': date_to
            }
        })
        
    except Exception as e:
        print(f"❌ CMM liste hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Liste alınamadı: {str(e)}'
        }), 500

@cmm_bp.route('/analysis/<analysis_id>', methods=['GET'])
@jwt_required()
def get_cmm_analysis(analysis_id):
    """
    Belirli bir CMM analizinin detaylarını al
    
    Args:
        analysis_id: Analiz ID'si
        
    Returns:
        Analiz detayları
    """
    try:
        user_id = get_jwt_identity()
        
        analysis = db.get_db().cmm_analyses.find_one({
            '_id': ObjectId(analysis_id),
            'user_id': user_id
        })
        
        if not analysis:
            return jsonify({
                'success': False,
                'message': 'CMM analizi bulunamadı'
            }), 404
        
        # ObjectId'yi string'e çevir
        analysis['_id'] = str(analysis['_id'])
        analysis['created_at'] = analysis['created_at'].isoformat()
        
        # Excel dosyasının varlığını kontrol et
        excel_exists = False
        if analysis.get('excel_path'):
            excel_exists = os.path.exists(analysis['excel_path'])
        
        analysis['excel_available'] = excel_exists
        
        # İndirme geçmişi
        if 'download_history' in analysis:
            for download in analysis['download_history']:
                download['downloaded_at'] = download['downloaded_at'].isoformat()
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        print(f"❌ CMM analiz detay hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analiz detayı alınamadı: {str(e)}'
        }), 500

@cmm_bp.route('/delete/<analysis_id>', methods=['DELETE'])
@jwt_required()
def delete_cmm_analysis(analysis_id):
    """
    CMM analizini sil
    
    Args:
        analysis_id: Silinecek analiz ID'si
        
    Returns:
        İşlem sonucu
    """
    try:
        user_id = get_jwt_identity()
        
        analysis = db.get_db().cmm_analyses.find_one({
            '_id': ObjectId(analysis_id),
            'user_id': user_id
        })
        
        if not analysis:
            return jsonify({
                'success': False,
                'message': 'CMM analizi bulunamadı'
            }), 404
        
        # Excel dosyasını sil
        if analysis.get('excel_path') and os.path.exists(analysis['excel_path']):
            try:
                os.remove(analysis['excel_path'])
                print(f"✅ Excel dosyası silindi: {analysis['excel_path']}")
            except Exception as e:
                print(f"⚠️ Excel dosyası silinemedi: {e}")
        
        # Veritabanından sil
        db.get_db().cmm_analyses.delete_one({'_id': ObjectId(analysis_id)})
        
        return jsonify({
            'success': True,
            'message': 'CMM analizi başarıyla silindi'
        })
        
    except Exception as e:
        print(f"❌ CMM silme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Silme hatası: {str(e)}'
        }), 500

@cmm_bp.route('/batch-delete', methods=['POST'])
@jwt_required()
def batch_delete_cmm_analyses():
    """
    Birden fazla CMM analizini toplu sil
    
    Request Body:
        - analysis_ids: Silinecek analiz ID'leri listesi
        
    Returns:
        İşlem sonucu
    """
    try:
        user_id = get_jwt_identity()
        
        data = request.get_json()
        analysis_ids = data.get('analysis_ids', [])
        
        if not analysis_ids:
            return jsonify({
                'success': False,
                'message': 'Silinecek analiz seçilmedi'
            }), 400
        
        # ID'leri ObjectId'ye çevir
        object_ids = [ObjectId(aid) for aid in analysis_ids]
        
        # Kullanıcıya ait analizleri bul
        analyses = list(db.get_db().cmm_analyses.find({
            '_id': {'$in': object_ids},
            'user_id': user_id
        }))
        
        if not analyses:
            return jsonify({
                'success': False,
                'message': 'Silinecek analiz bulunamadı'
            }), 404
        
        # Excel dosyalarını sil
        deleted_files = 0
        for analysis in analyses:
            if analysis.get('excel_path') and os.path.exists(analysis['excel_path']):
                try:
                    os.remove(analysis['excel_path'])
                    deleted_files += 1
                except Exception as e:
                    print(f"⚠️ Excel dosyası silinemedi: {e}")
        
        # Veritabanından sil
        delete_result = db.get_db().cmm_analyses.delete_many({
            '_id': {'$in': object_ids},
            'user_id': user_id
        })
        
        return jsonify({
            'success': True,
            'message': f'{delete_result.deleted_count} analiz silindi',
            'deleted_count': delete_result.deleted_count,
            'deleted_files': deleted_files
        })
        
    except Exception as e:
        print(f"❌ Toplu silme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Toplu silme hatası: {str(e)}'
        }), 500

@cmm_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_cmm_stats():
    """
    CMM istatistiklerini al
    
    Returns:
        İstatistik verileri
    """
    try:
        user_id = get_jwt_identity()
        
        # Toplam analiz sayısı
        total_analyses = db.get_db().cmm_analyses.count_documents({'user_id': user_id})
        
        # Bu ayki analizler
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_analyses = db.get_db().cmm_analyses.count_documents({
            'user_id': user_id,
            'created_at': {'$gte': this_month_start}
        })
        
        # Bu haftaki analizler
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        this_week_analyses = db.get_db().cmm_analyses.count_documents({
            'user_id': user_id,
            'created_at': {'$gte': week_start}
        })
        
        # Toplam ölçüm sayısı
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$group': {
                '_id': None, 
                'total_measurements': {'$sum': '$measurement_count'},
                'total_files': {'$sum': '$file_count'}
            }}
        ]
        measurement_stats = list(db.get_db().cmm_analyses.aggregate(pipeline))
        
        total_measurements = 0
        total_files = 0
        if measurement_stats:
            total_measurements = measurement_stats[0].get('total_measurements', 0)
            total_files = measurement_stats[0].get('total_files', 0)
        
        # En çok kullanılan operasyonlar
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$unwind': '$operations'},
            {'$group': {'_id': '$operations', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 5}
        ]
        top_operations = list(db.get_db().cmm_analyses.aggregate(pipeline))
        
        # Son analizler
        recent_analyses = list(db.get_db().cmm_analyses.find(
            {'user_id': user_id}
        ).sort('created_at', -1).limit(5))
        
        for analysis in recent_analyses:
            analysis['_id'] = str(analysis['_id'])
            analysis['created_at'] = analysis['created_at'].isoformat()
        
        # Başarı oranı hesapla
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$group': {
                '_id': None,
                'avg_success_rate': {'$avg': '$processing_summary.summary.success_rate'}
            }}
        ]
        success_rate_stats = list(db.get_db().cmm_analyses.aggregate(pipeline))
        avg_success_rate = success_rate_stats[0].get('avg_success_rate', 0) if success_rate_stats else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'total_analyses': total_analyses,
                'this_month_analyses': this_month_analyses,
                'this_week_analyses': this_week_analyses,
                'total_measurements': total_measurements,
                'total_files': total_files,
                'avg_measurements_per_analysis': round(total_measurements / total_analyses, 1) if total_analyses > 0 else 0,
                'avg_files_per_analysis': round(total_files / total_analyses, 1) if total_analyses > 0 else 0,
                'avg_success_rate': round(avg_success_rate, 2),
                'top_operations': [
                    {'operation': op['_id'], 'count': op['count']} 
                    for op in top_operations
                ],
                'recent_analyses': recent_analyses
            }
        })
        
    except Exception as e:
        print(f"❌ CMM stats hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'İstatistik alınamadı: {str(e)}'
        }), 500

@cmm_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """
    Desteklenen dosya formatlarını döndür
    
    Returns:
        Desteklenen format bilgileri
    """
    return jsonify({
        'success': True,
        'supported_formats': {
            'rtf': {
                'extensions': ['.rtf', '.RTF'],
                'description': 'Rich Text Format - CMM ölçüm raporları',
                'mime_types': ['application/rtf', 'text/rtf']
            }
        },
        'max_file_size': f'{MAX_FILE_SIZE//1024//1024}MB',
        'max_files': MAX_FILES_PER_UPLOAD,
        'features': [
            'Çoklu operasyon desteği (1OP, 2OP, 3OP)',
            'Otomatik ölçüm numarası sıralama',
            'Aralık formatı desteği (10-18)',
            'Position ölçümü desteği (X, Y, Z, TP, DF)',
            'Surface profil birleştirme',
            'Min/Max değer hesaplama',
            'Excel raporu (3 sayfa)',
            'FAI Form 3 desteği',
            'Duplikat temizleme',
            'Tolerans dışı değer tespiti',
            'Detaylı özet istatistikleri'
        ]
    })

@cmm_bp.route('/test-service', methods=['POST'])
@jwt_required()
def test_cmm_service():
    """
    CMM service'i test et (debug amaçlı)
    
    Returns:
        Test sonuçları
    """
    try:
        # Test dosyası yolları
        test_files = [
            'test_data/cmm_sample_1OP.RTF',
            'test_data/cmm_sample_2OP.RTF'
        ]
        
        # Var olan test dosyalarını kontrol et
        existing_files = [f for f in test_files if os.path.exists(f)]
        
        if not existing_files:
            return jsonify({
                'success': False,
                'message': 'Test dosyaları bulunamadı',
                'expected_paths': test_files
            })
        
        # Service'i test et
        cmm_service = CMMService()
        result = cmm_service.process_files(existing_files)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'CMM service test başarılı',
                'test_results': {
                    'files_processed': len(existing_files),
                    'total_measurements': result.get('count', 0),
                    'operations_found': result.get('operations', []),
                    'summary': result.get('summary', {}),
                    'excel_generated': bool(result.get('excel_path'))
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'CMM service test başarısız',
                'error': result.get('error', 'Bilinmeyen hata')
            })
        
    except Exception as e:
        print(f"❌ CMM test hatası: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Test hatası: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@cmm_bp.route('/export-history', methods=['GET'])
@jwt_required()
def get_export_history():
    """
    Kullanıcının export geçmişini al
    
    Query Parameters:
        - days: Kaç günlük geçmiş (default: 30)
        
    Returns:
        Export geçmişi
    """
    try:
        user_id = get_jwt_identity()
        days = int(request.args.get('days', 30))
        
        # Tarih filtresi
        date_filter = datetime.utcnow() - timedelta(days=days)
        
        # Export geçmişini al
        pipeline = [
            {
                '$match': {
                    'user_id': user_id,
                    'created_at': {'$gte': date_filter}
                }
            },
            {
                '$project': {
                    'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                    'file_count': 1,
                    'measurement_count': 1,
                    'operations': 1
                }
            },
            {
                '$group': {
                    '_id': '$date',
                    'export_count': {'$sum': 1},
                    'total_files': {'$sum': '$file_count'},
                    'total_measurements': {'$sum': '$measurement_count'}
                }
            },
            {
                '$sort': {'_id': -1}
            }
        ]
        
        export_history = list(db.get_db().cmm_analyses.aggregate(pipeline))
        
        # Tarih formatını düzenle
        for item in export_history:
            item['date'] = item.pop('_id')
        
        return jsonify({
            'success': True,
            'history': export_history,
            'period_days': days,
            'total_exports': sum(item['export_count'] for item in export_history)
        })
        
    except Exception as e:
        print(f"❌ Export geçmişi hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Geçmiş alınamadı: {str(e)}'
        }), 500
