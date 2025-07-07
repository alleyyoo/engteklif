# backend/controllers/cmm_controller.py
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import sys
import tempfile
import traceback
from datetime import datetime
from werkzeug.utils import secure_filename
from utils.database import db

# CMM Parser'ı import et - dosya konumuna göre ayarla
try:
    # Önce root dizinden dene
    from cmm_parser import CMMParser, CMMExcelExporter, process_cmm_files
except ImportError:
    try:
        # Backend dizini içinden dene
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from cmm_parser import CMMParser, CMMExcelExporter, process_cmm_files
    except ImportError:
        # Utils klasöründen dene
        try:
            from utils.cmm_parser import CMMParser, CMMExcelExporter, process_cmm_files
        except ImportError:
            print("❌ CMM Parser modülü bulunamadı!")
            print("   cmm_parser.py dosyasını şu konumlardan birine yerleştirin:")
            print("   1. backend/cmm_parser.py")
            print("   2. backend/utils/cmm_parser.py")
            print("   3. backend/controllers/cmm_parser.py")
            raise ImportError("CMM Parser modülü bulunamadı")

cmm_bp = Blueprint('cmm', __name__, url_prefix='/api/cmm')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'rtf', 'RTF'}

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
    CMM RTF dosyalarını yükle ve parse et
    """
    try:
        user_id = get_jwt_identity()
        
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
        
        # Dosya türü kontrolü
        invalid_files = []
        for file in files:
            if not file or file.filename == '':
                invalid_files.append('Boş dosya adı')
            elif not allowed_file(file.filename):
                invalid_files.append(f'{file.filename} - Sadece RTF dosyaları desteklenir')
        
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
            except Exception as e:
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
        
        # CMM dosyalarını parse et
        print(f"🔄 CMM parsing başlıyor: {len(file_paths)} dosya")
        result = process_cmm_files(file_paths, excel_path)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': result.get('error', 'CMM parsing başarısız'),
                'debug_info': {
                    'file_count': len(file_paths),
                    'file_paths': file_paths
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
                'operations_found': result.get('operations', [])
            }
        }
        
        # MongoDB'ye kaydet
        db_result = db.get_db().cmm_analyses.insert_one(cmm_analysis)
        analysis_id = str(db_result.inserted_id)
        
        # Upload edilen dosyaları temizle (opsiyonel)
        try:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Temp dosyalar temizlenemedi: {e}")
        
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
                'processing_time': '< 5 saniye'
            },
            'upload_summary': {
                'total_uploaded': len(uploaded_files),
                'total_measurements': result.get('count', 0),
                'operations_detected': result.get('operations', []),
                'excel_generated': True
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
    """
    try:
        user_id = get_jwt_identity()
        
        # Analiz kaydını bul
        from bson import ObjectId
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
    """
    try:
        user_id = get_jwt_identity()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # MongoDB'den kullanıcının analizlerini al
        skip = (page - 1) * limit
        analyses = list(db.get_db().cmm_analyses.find(
            {'user_id': user_id}
        ).sort('created_at', -1).skip(skip).limit(limit))
        
        # ObjectId'leri string'e çevir
        for analysis in analyses:
            analysis['_id'] = str(analysis['_id'])
            analysis['created_at'] = analysis['created_at'].isoformat()
        
        total_count = db.get_db().cmm_analyses.count_documents({'user_id': user_id})
        
        return jsonify({
            'success': True,
            'analyses': analyses,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
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
    """
    try:
        user_id = get_jwt_identity()
        
        from bson import ObjectId
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
    """
    try:
        user_id = get_jwt_identity()
        
        from bson import ObjectId
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

@cmm_bp.route('/test-parser', methods=['POST'])
@jwt_required()
def test_cmm_parser():
    """
    CMM parser'ı test et (debug amaçlı)
    """
    try:
        # Test dosyası yolu
        test_files = [
            'test_data/cmm_sample.RTF'
        ]
        
        # Parser'ı test et
        parser = CMMParser()
        exporter = CMMExcelExporter()
        
        measurements = []
        for file_path in test_files:
            if os.path.exists(file_path):
                file_measurements = parser.parse_file(file_path)
                measurements.extend(file_measurements)
        
        if not measurements:
            return jsonify({
                'success': False,
                'message': 'Test dosyası bulunamadı veya ölçüm verisi çıkarılamadı'
            })
        
        # Test DataFrame oluştur
        df = exporter.to_dataframe(measurements)
        
        return jsonify({
            'success': True,
            'message': 'CMM parser test başarılı',
            'test_results': {
                'total_measurements': len(measurements),
                'dataframe_rows': len(df),
                'columns': list(df.columns),
                'sample_data': df.head().to_dict('records') if len(df) > 0 else [],
                'operations': list(df['Operasyon'].unique()) if 'Operasyon' in df.columns else []
            }
        })
        
    except Exception as e:
        print(f"❌ CMM test hatası: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Test hatası: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@cmm_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """
    Desteklenen dosya formatlarını döndür
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
        'max_file_size': '10MB',
        'max_files': 50,
        'features': [
            '1OP ve 2OP operasyon tanıma',
            'Otomatik ölçüm numarası sıralama',
            'Position ölçümü desteği (X, Y, TP, DF)',
            'Excel export',
            'Duplikat temizleme',
            'Tolerans dışı değer tespiti'
        ]
    })

@cmm_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_cmm_stats():
    """
    CMM istatistiklerini al
    """
    try:
        user_id = get_jwt_identity()
        
        # Toplam analiz sayısı
        total_analyses = db.get_db().cmm_analyses.count_documents({'user_id': user_id})
        
        # Bu ayki analizler
        from datetime import datetime, timedelta
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_analyses = db.get_db().cmm_analyses.count_documents({
            'user_id': user_id,
            'created_at': {'$gte': this_month_start}
        })
        
        # Toplam ölçüm sayısı
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$group': {'_id': None, 'total_measurements': {'$sum': '$measurement_count'}}}
        ]
        measurement_stats = list(db.get_db().cmm_analyses.aggregate(pipeline))
        total_measurements = measurement_stats[0]['total_measurements'] if measurement_stats else 0
        
        # En çok kullanılan operasyonlar
        pipeline = [
            {'$match': {'user_id': user_id}},
            {'$unwind': '$operations'},
            {'$group': {'_id': '$operations', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 5}
        ]
        top_operations = list(db.get_db().cmm_analyses.aggregate(pipeline))
        
        return jsonify({
            'success': True,
            'stats': {
                'total_analyses': total_analyses,
                'this_month_analyses': this_month_analyses,
                'total_measurements': total_measurements,
                'avg_measurements_per_analysis': round(total_measurements / total_analyses, 1) if total_analyses > 0 else 0,
                'top_operations': [
                    {'operation': op['_id'], 'count': op['count']} 
                    for op in top_operations
                ]
            }
        })
        
    except Exception as e:
        print(f"❌ CMM stats hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'İstatistik alınamadı: {str(e)}'
        }), 500