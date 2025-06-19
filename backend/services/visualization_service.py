import os
import uuid
from typing import Optional

def determine_visualization_type(analysis_data):
    """Analiz verilerine göre görselleştirme türünü belirle"""
    
    step_analysis = analysis_data.get('step_analysis', {})
    file_type = analysis_data.get('file_type', '')
    file_path = analysis_data.get('file_path', '')
    
    print(f"[DEBUG] File type: {file_type}")
    print(f"[DEBUG] File path: {file_path}")
    print(f"[DEBUG] Step analysis method: {step_analysis.get('method', 'none')}")
    
    # STEP dosyası ve gerçek cadquery analizi varsa
    if (file_type in ['step', 'stp'] and 
        step_analysis and 
        step_analysis.get('method') == 'cadquery_analysis' and
        file_path and os.path.exists(file_path)):
        return 'step_file'
    
    # PDF'den çıkarılan STEP analizi
    elif step_analysis and step_analysis.get('method') in ['estimated_from_pdf', 'estimated_from_document']:
        return 'step_from_analysis'
    
    # Diğer durumlar
    else:
        return 'estimated_geometry'
    
# services/visualization_service.py (devamı)
def generate_isometric_view(analysis_data, output_path):
    """Analiz verilerine göre izometrik görünüm oluştur"""
    
    viz_type = determine_visualization_type(analysis_data)
    print(f"[DEBUG] Visualization type: {viz_type}")
    
    if viz_type == 'step_file':
        return render_step_isometric(analysis_data, output_path)
    elif viz_type == 'step_from_analysis':
        return render_analysis_isometric(analysis_data, output_path)
    else:
        # Gerçek analiz verilerini kullan
        try:
            from services.pdf_3d_renderer import render_pdf_isometric
            
            step_analysis = analysis_data.get('step_analysis', {})
            
            # Gerçek boyutları al, yoksa varsayılan
            x = step_analysis.get("X (mm)", 50.0)
            y = step_analysis.get("Y (mm)", 30.0)
            z = step_analysis.get("Z (mm)", 20.0)
            
            print(f"[DEBUG] Rendering boyutları: {x}x{y}x{z} mm")
            
            return render_pdf_isometric(x, y, z, output_path, step_analysis)
            
        except Exception as e:
            print(f"[ERROR] Estimated izometrik render hatası: {e}")
            return False

def render_step_isometric(analysis_data, output_path):
    """Gerçek STEP dosyasından izometrik render"""
    try:
        file_path = analysis_data.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return False
            
        # Mevcut step_renderer.py'deki generate_step_views kullan
        from services.step_renderer import generate_step_views
        rendered_files = generate_step_views(file_path, ['isometric'], os.path.dirname(output_path))
        
        if rendered_files and len(rendered_files) > 0:
            # Dosyayı hedef yere taşı
            import shutil
            shutil.move(rendered_files[0], output_path)
            return True
        return False
        
    except Exception as e:
        print(f"[ERROR] STEP izometrik render hatası: {e}")
        return False
    
# services/visualization_service.py (devamı)
def render_analysis_isometric(analysis_data, output_path):
    """PDF'den çıkarılan STEP analizi verilerinden izometrik render"""
    try:
        step_analysis = analysis_data.get('step_analysis', {})
        if not step_analysis:
            return False
            
        # Mevcut pdf_3d_renderer.py'deki render_pdf_isometric kullan
        from services.pdf_3d_renderer import render_pdf_isometric
        
        x = step_analysis.get("X (mm)", 50.0)
        y = step_analysis.get("Y (mm)", 30.0) 
        z = step_analysis.get("Z (mm)", 20.0)
        
        return render_pdf_isometric(x, y, z, output_path, step_analysis)
        
    except Exception as e:
        print(f"[ERROR] Analysis izometrik render hatası: {e}")
        return False

def render_estimated_isometric(analysis_data, output_path):
    """Tahmini geometri verilerinden izometrik render"""
    try:
        # Varsayılan boyutlarla render
        from services.pdf_3d_renderer import render_pdf_isometric
        
        default_analysis = {
            "X (mm)": 50.0,
            "Y (mm)": 30.0,
            "Z (mm)": 20.0,
            "method": "estimated"
        }
        
        return render_pdf_isometric(50.0, 30.0, 20.0, output_path, default_analysis)
        
    except Exception as e:
        print(f"[ERROR] Estimated izometrik render hatası: {e}")
        return False