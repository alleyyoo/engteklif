# services/visualization_service.py

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

def generate_isometric_view(analysis_data, output_path):
   """Analiz verilerine göre izometrik görünüm oluştur"""
   
   # Analiz verilerini debug et
   print(f"[DEBUG] Analysis data keys: {list(analysis_data.keys())}")
   
   step_analysis = analysis_data.get('step_analysis', {})
   print(f"[DEBUG] Step analysis keys: {list(step_analysis.keys())}")
   print(f"[DEBUG] Step analysis data: {step_analysis}")
   
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
           
           # Gerçek boyutları al, yoksa varsayılan
           x = step_analysis.get("X (mm)", 50.0)
           y = step_analysis.get("Y (mm)", 30.0)
           z = step_analysis.get("Z (mm)", 20.0)
           
           print(f"[DEBUG] Kullanılan boyutlar: X={x}, Y={y}, Z={z}")
           
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

def generate_wireframe_data(analysis_data):
   """Analiz verilerine göre wireframe data oluştur"""
   
   viz_type = determine_visualization_type(analysis_data)
   print(f"[DEBUG] Wireframe için visualization type: {viz_type}")
   
   if viz_type == 'step_file':
       return create_step_wireframe_data_from_file(analysis_data)
   elif viz_type == 'step_from_analysis':
       return create_wireframe_from_analysis(analysis_data)
   else:
       return create_simple_wireframe_data(analysis_data)

def create_step_wireframe_data_from_file(analysis_data):
   """Gerçek STEP dosyasından wireframe data oluştur"""
   try:
       file_path = analysis_data.get('file_path')
       if not file_path or not os.path.exists(file_path):
           return None
           
       # Mevcut step_renderer.py'deki create_step_wireframe_data kullan
       from services.step_renderer import create_step_wireframe_data
       return create_step_wireframe_data(file_path)
       
   except Exception as e:
       print(f"[ERROR] STEP wireframe data hatası: {e}")
       return None

def create_wireframe_from_analysis(analysis_data):
   """PDF analizi verilerinden wireframe data oluştur"""
   try:
       step_analysis = analysis_data.get('step_analysis', {})
       if not step_analysis:
           return None
           
       # pdf_3d_renderer.py'deki create_pdf_wireframe_data kullan
       from services.pdf_3d_renderer import create_pdf_wireframe_data
       return create_pdf_wireframe_data(step_analysis)
       
   except Exception as e:
       print(f"[ERROR] Analysis wireframe data hatası: {e}")
       return None

def create_simple_wireframe_data(analysis_data):
   """Basit wireframe data oluştur"""
   try:
       step_analysis = analysis_data.get('step_analysis', {})
       
       # Gerçek boyutları al
       x = step_analysis.get("X (mm)", 50.0)
       y = step_analysis.get("Y (mm)", 30.0)
       z = step_analysis.get("Z (mm)", 20.0)
       
       print(f"[DEBUG] Wireframe boyutları: {x}x{y}x{z} mm")
       
       vertices = [
           [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],  # alt yüz
           [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]   # üst yüz
       ]
       
       edges = [
           [0, 1], [1, 2], [2, 3], [3, 0],  # alt yüz
           [4, 5], [5, 6], [6, 7], [7, 4],  # üst yüz
           [0, 4], [1, 5], [2, 6], [3, 7]   # dikey
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
           }
       }
       
   except Exception as e:
       print(f"[ERROR] Simple wireframe data hatası: {e}")
       return None

def generate_3d_view(analysis_data, output_path):
   """3D görünüm oluştur"""
   
   viz_type = determine_visualization_type(analysis_data)
   print(f"[DEBUG] 3D view için visualization type: {viz_type}")
   
   if viz_type == 'step_file':
       return render_step_3d(analysis_data, output_path)
   elif viz_type == 'step_from_analysis':
       return render_analysis_3d(analysis_data, output_path)
   else:
       return render_estimated_3d(analysis_data, output_path)

def render_step_3d(analysis_data, output_path):
   """Gerçek STEP dosyasından 3D render"""
   try:
       file_path = analysis_data.get('file_path')
       if not file_path or not os.path.exists(file_path):
           return False
           
       # step_renderer.py'deki render_step_3d kullan
       from services.step_renderer import render_step_3d
       return render_step_3d(file_path, output_path)
       
   except Exception as e:
       print(f"[ERROR] STEP 3D render hatası: {e}")
       return False

def render_analysis_3d(analysis_data, output_path):
   """PDF analizi verilerinden 3D render"""
   try:
       step_analysis = analysis_data.get('step_analysis', {})
       if not step_analysis:
           return False
           
       # pdf_3d_renderer.py'deki render_pdf_3d kullan
       from services.pdf_3d_renderer import render_pdf_3d
       
       x = step_analysis.get("X (mm)", 50.0)
       y = step_analysis.get("Y (mm)", 30.0)
       z = step_analysis.get("Z (mm)", 20.0)
       
       return render_pdf_3d(x, y, z, output_path, step_analysis)
       
   except Exception as e:
       print(f"[ERROR] Analysis 3D render hatası: {e}")
       return False

def render_estimated_3d(analysis_data, output_path):
   """Tahmini verilerden 3D render"""
   try:
       step_analysis = analysis_data.get('step_analysis', {})
       
       # pdf_3d_renderer.py'deki render_pdf_3d kullan
       from services.pdf_3d_renderer import render_pdf_3d
       
       x = step_analysis.get("X (mm)", 50.0)
       y = step_analysis.get("Y (mm)", 30.0)
       z = step_analysis.get("Z (mm)", 20.0)
       
       return render_pdf_3d(x, y, z, output_path, step_analysis)
       
   except Exception as e:
       print(f"[ERROR] Estimated 3D render hatası: {e}")
       return False