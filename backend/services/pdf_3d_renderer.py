# services/pdf_3d_renderer.py
import os
import uuid
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from typing import List, Dict, Any, Optional

print("[INFO] ✅ PDF 3D Renderer aktif - PDF analizlerinden 3D model oluşturma")

def create_pdf_wireframe_data(step_analysis: Dict[str, Any]) -> Optional[dict]:
    """
    PDF'den çıkarılan STEP analizi verilerinden wireframe data oluşturur
    
    Args:
        step_analysis: PDF'den çıkarılan STEP analiz verileri
        
    Returns:
        dict: 3D viewer için wireframe data
    """
    try:
        print(f"[DEBUG] PDF wireframe data oluşturuluyor: {step_analysis.get('method', 'unknown')}")
        
        # Boyutları al
        x = step_analysis.get("X (mm)", 50.0)
        y = step_analysis.get("Y (mm)", 30.0)
        z = step_analysis.get("Z (mm)", 20.0)
        
        print(f"[DEBUG] PDF boyutları: {x}x{y}x{z} mm")
        
        # Basit kutu wireframe oluştur (PDF'lerden genellikle basit geometriler çıkar)
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
        
        # Bounding box hesapla
        bounding_box = {
            'min': [0, 0, 0],
            'max': [x, y, z],
            'center': [x/2, y/2, z/2],
            'dimensions': [x, y, z]
        }
        
        wireframe_data = {
            'vertices': vertices,
            'edges': edges,
            'vertex_count': len(vertices),
            'edge_count': len(edges),
            'bounding_box': bounding_box,
            'source_type': 'pdf_analysis',
            'analysis_method': step_analysis.get('method', 'estimated_from_pdf')
        }
        
        print(f"[SUCCESS] PDF wireframe data oluşturuldu - {len(vertices)} vertex, {len(edges)} edge")
        return wireframe_data
        
    except Exception as e:
        print(f"[ERROR] PDF wireframe data oluşturma hatası: {e}")
        return None

def create_enhanced_pdf_wireframe(step_analysis: Dict[str, Any]) -> Optional[dict]:
    """
    PDF'den çıkarılan verilerle gelişmiş wireframe oluşturur
    Silindirik boyutlar ve daha karmaşık geometriler dahil
    """
    try:
        print(f"[DEBUG] Enhanced PDF wireframe oluşturuluyor...")
        
        # Temel boyutlar
        x = step_analysis.get("X (mm)", 50.0)
        y = step_analysis.get("Y (mm)", 30.0)
        z = step_analysis.get("Z (mm)", 20.0)
        
        # Silindirik boyutlar varsa
        cyl_diameter = step_analysis.get("Silindirik Çap (mm)")
        cyl_height = step_analysis.get("Silindirik Yükseklik (mm)")
        
        vertices = []
        edges = []
        
        if cyl_diameter and cyl_height:
            # Silindirik geometri oluştur
            print(f"[DEBUG] Silindirik geometri: Çap {cyl_diameter}mm, Yükseklik {cyl_height}mm")
            
            radius = cyl_diameter / 2
            segments = 16  # Silindir çözünürlüğü
            
            # Alt çember vertices
            for i in range(segments):
                angle = (i / segments) * 2 * np.pi
                x_pos = radius * np.cos(angle)
                y_pos = radius * np.sin(angle)
                vertices.append([x_pos, y_pos, 0])  # Alt
                vertices.append([x_pos, y_pos, cyl_height])  # Üst
            
            # Alt çember edges
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
            
        else:
            # Dikdörtgen prizma (varsayılan)
            vertices = [
                [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],  # alt yüz
                [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]   # üst yüz
            ]
            
            edges = [
                [0, 1], [1, 2], [2, 3], [3, 0],  # alt yüz
                [4, 5], [5, 6], [6, 7], [7, 4],  # üst yüz
                [0, 4], [1, 5], [2, 6], [3, 7]   # dikey
            ]
            
            bounding_box = {
                'min': [0, 0, 0],
                'max': [x, y, z],
                'center': [x/2, y/2, z/2],
                'dimensions': [x, y, z]
            }
        
        wireframe_data = {
            'vertices': vertices,
            'edges': edges,
            'vertex_count': len(vertices),
            'edge_count': len(edges),
            'bounding_box': bounding_box,
            'source_type': 'pdf_enhanced',
            'geometry_type': 'cylindrical' if cyl_diameter else 'prismatic',
            'analysis_method': step_analysis.get('method', 'estimated_from_pdf')
        }
        
        print(f"[SUCCESS] Enhanced PDF wireframe oluşturuldu - {len(vertices)} vertex, {len(edges)} edge")
        return wireframe_data
        
    except Exception as e:
        print(f"[ERROR] Enhanced PDF wireframe hatası: {e}")
        return None

def generate_pdf_3d_render(step_analysis: Dict[str, Any], output_path: str = None, 
                          views: List[str] = None) -> List[str]:
    """
    PDF analizi verilerinden 3D render görüntüleri oluşturur
    
    Args:
        step_analysis: PDF'den çıkarılan STEP analiz verileri
        output_path: Çıktı klasörü
        views: Render edilecek görünümler
        
    Returns:
        List[str]: Oluşturulan görsel dosyalarının yolları
    """
    if views is None:
        views = ['isometric']
    
    if output_path is None:
        output_path = "static"
    
    os.makedirs(output_path, exist_ok=True)
    
    try:
        print(f"[DEBUG] PDF 3D render oluşturuluyor: {views}")
        
        # Boyutları al
        x = step_analysis.get("X (mm)", 50.0)
        y = step_analysis.get("Y (mm)", 30.0)
        z = step_analysis.get("Z (mm)", 20.0)
        
        generated_files = []
        session_id = str(uuid.uuid4())[:8]
        
        for view in views:
            try:
                image_filename = f"pdf_{session_id}_{view}.png"
                image_path = os.path.join(output_path, image_filename)
                
                if view == 'isometric':
                    success = render_pdf_isometric(x, y, z, image_path, step_analysis)
                elif view == 'front':
                    success = render_pdf_orthographic(x, y, z, image_path, 'front')
                elif view == 'top':
                    success = render_pdf_orthographic(x, y, z, image_path, 'top')
                elif view == 'side':
                    success = render_pdf_orthographic(x, y, z, image_path, 'side')
                else:
                    continue
                
                if success and os.path.exists(image_path):
                    generated_files.append(image_path)
                    print(f"[SUCCESS] ✅ PDF {view} görünümü oluşturuldu: {image_path}")
                
            except Exception as e:
                print(f"[ERROR] ❌ PDF {view} görünümü oluşturulamadı: {e}")
                continue
        
        print(f"[INFO] Toplam {len(generated_files)} PDF render oluşturuldu")
        return generated_files
        
    except Exception as e:
        print(f"[ERROR] PDF 3D render hatası: {e}")
        return []

def render_pdf_isometric(x: float, y: float, z: float, output_path: str, 
                         step_analysis: Dict[str, Any]) -> bool:
    """PDF verilerinden izometrik görünüm render'ı"""
    try:
        print(f"[DEBUG] PDF izometrik render: {x}x{y}x{z} mm")
        
        fig = plt.figure(figsize=(10, 8), dpi=150)
        ax = fig.add_subplot(111, projection='3d')
        
        # Silindirik geometri kontrolü
        cyl_diameter = step_analysis.get("Silindirik Çap (mm)")
        cyl_height = step_analysis.get("Silindirik Yükseklik (mm)")
        
        if cyl_diameter and cyl_height:
            # Silindir çiz
            render_cylinder(ax, cyl_diameter/2, cyl_height)
            title = f'PDF Analizi - Silindirik Model\nÇap: {cyl_diameter}mm, Yükseklik: {cyl_height}mm'
        else:
            # Dikdörtgen prizma çiz
            render_box(ax, x, y, z)
            title = f'PDF Analizi - Prizmatik Model\n{x}x{y}x{z} mm'
        
        # Styling
        ax.set_xlabel('X (mm)', fontsize=10)
        ax.set_ylabel('Y (mm)', fontsize=10)
        ax.set_zlabel('Z (mm)', fontsize=10)
        ax.set_title(title, fontsize=12, weight='bold', pad=20)
        
        # Görünüm açısı
        ax.view_init(elev=25, azim=45)
        
        # Grid ve arka plan
        ax.grid(True, alpha=0.3)
        
        # Renk ve stil
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        
        # Eksen oranları
        max_range = max(x, y, z) / 2
        mid_x, mid_y, mid_z = x/2, y/2, z/2
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', format='png')
        plt.close()
        
        print(f"[SUCCESS] PDF izometrik render kaydedildi: {output_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] PDF izometrik render hatası: {e}")
        plt.close('all')
        return False

def render_box(ax, x: float, y: float, z: float):
    """3D kutusunu çiz"""
    # Kutu köşeleri
    vertices = np.array([
        [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],  # alt
        [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]   # üst
    ])
    
    # Yüzleri tanımla
    faces = [
        [vertices[0], vertices[1], vertices[2], vertices[3]],  # alt
        [vertices[4], vertices[5], vertices[6], vertices[7]],  # üst
        [vertices[0], vertices[1], vertices[5], vertices[4]],  # ön
        [vertices[2], vertices[3], vertices[7], vertices[6]],  # arka
        [vertices[1], vertices[2], vertices[6], vertices[5]],  # sağ
        [vertices[4], vertices[7], vertices[3], vertices[0]]   # sol
    ]
    
    # Yüzleri çiz
    poly3d = Poly3DCollection(faces, alpha=0.7, facecolor='lightblue', edgecolor='navy')
    ax.add_collection3d(poly3d)
    
    # Kenarları çiz
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # alt
        [4, 5], [5, 6], [6, 7], [7, 4],  # üst
        [0, 4], [1, 5], [2, 6], [3, 7]   # dikey
    ]
    
    for edge in edges:
        points = vertices[edge]
        ax.plot3D(points[:, 0], points[:, 1], points[:, 2], 'b-', linewidth=2)

def render_cylinder(ax, radius: float, height: float, segments: int = 20):
    """3D silindiri çiz"""
    # Silindir parametreleri
    theta = np.linspace(0, 2*np.pi, segments)
    z_bottom = np.zeros(segments)
    z_top = np.full(segments, height)
    
    x_circle = radius * np.cos(theta)
    y_circle = radius * np.sin(theta)
    
    # Alt ve üst çemberler
    ax.plot(x_circle, y_circle, z_bottom, 'b-', linewidth=2)
    ax.plot(x_circle, y_circle, z_top, 'b-', linewidth=2)
    
    # Dikey çizgiler
    for i in range(0, segments, segments//8):  # 8 dikey çizgi
        ax.plot([x_circle[i], x_circle[i]], [y_circle[i], y_circle[i]], [0, height], 'b-', linewidth=1)
    
    # Yüzey (şeffaf)
    z_surf = np.linspace(0, height, 10)
    theta_surf = np.linspace(0, 2*np.pi, segments)
    THETA, Z = np.meshgrid(theta_surf, z_surf)
    X = radius * np.cos(THETA)
    Y = radius * np.sin(THETA)
    
    ax.plot_surface(X, Y, Z, alpha=0.3, color='lightblue')

def render_pdf_orthographic(x: float, y: float, z: float, output_path: str, view_type: str) -> bool:
    """PDF verilerinden ortografik görünüm render'ı"""
    try:
        print(f"[DEBUG] PDF {view_type} ortografik render: {x}x{y}x{z} mm")
        
        fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
        
        # Görünüm türüne göre projeksiyon
        if view_type == 'front':  # X-Z düzlemi
            ax.add_patch(plt.Rectangle((0, 0), x, z, fill=False, edgecolor='blue', linewidth=2))
            ax.set_xlim(-x*0.1, x*1.1)
            ax.set_ylim(-z*0.1, z*1.1)
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Z (mm)')
            title = f'PDF Analizi - Ön Görünüm\n{x}x{z} mm'
            
        elif view_type == 'top':  # X-Y düzlemi
            ax.add_patch(plt.Rectangle((0, 0), x, y, fill=False, edgecolor='blue', linewidth=2))
            ax.set_xlim(-x*0.1, x*1.1)
            ax.set_ylim(-y*0.1, y*1.1)
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Y (mm)')
            title = f'PDF Analizi - Üst Görünüm\n{x}x{y} mm'
            
        else:  # side - Y-Z düzlemi
            ax.add_patch(plt.Rectangle((0, 0), y, z, fill=False, edgecolor='blue', linewidth=2))
            ax.set_xlim(-y*0.1, y*1.1)
            ax.set_ylim(-z*0.1, z*1.1)
            ax.set_xlabel('Y (mm)')
            ax.set_ylabel('Z (mm)')
            title = f'PDF Analizi - Yan Görünüm\n{y}x{z} mm'
        
        ax.set_title(title, fontsize=12, weight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none', format='png')
        plt.close()
        
        print(f"[SUCCESS] PDF {view_type} render kaydedildi: {output_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] PDF ortografik render hatası ({view_type}): {e}")
        plt.close('all')
        return False

def create_pdf_thumbnail(step_analysis: Dict[str, Any], output_path: str, size: tuple = (200, 150)) -> bool:
    """PDF analizi için küçük thumbnail oluştur"""
    try:
        print(f"[DEBUG] PDF thumbnail oluşturuluyor: {output_path}")
        
        x = step_analysis.get("X (mm)", 50.0)
        y = step_analysis.get("Y (mm)", 30.0)
        z = step_analysis.get("Z (mm)", 20.0)
        
        success = render_pdf_isometric(x, y, z, output_path, step_analysis)
        
        if success:
            print(f"[SUCCESS] PDF thumbnail oluşturuldu: {output_path}")
        
        return success
        
    except Exception as e:
        print(f"[ERROR] PDF thumbnail oluşturma hatası: {e}")
        return False

def get_pdf_render_info(step_analysis: Dict[str, Any]) -> dict:
    """PDF analizi render bilgilerini al"""
    try:
        x = step_analysis.get("X (mm)", 0)
        y = step_analysis.get("Y (mm)", 0)
        z = step_analysis.get("Z (mm)", 0)
        volume = step_analysis.get("Prizma Hacmi (mm³)", 0)
        
        return {
            "source_type": "pdf_analysis",
            "dimensions": [x, y, z],
            "volume_mm3": volume,
            "analysis_method": step_analysis.get("method", "estimated"),
            "bounding_box": {
                "x_range": [0, x],
                "y_range": [0, y],
                "z_range": [0, z],
                "dimensions": [x, y, z]
            },
            "render_ready": True,
            "geometry_type": "cylindrical" if step_analysis.get("Silindirik Çap (mm)") else "prismatic"
        }
        
    except Exception as e:
        return {"error": str(e), "render_ready": False}

# Utility functions
def cleanup_pdf_renders(pattern: str = "static/pdf_*_temp_*.png"):
    """PDF render dosyalarını temizle"""
    import glob
    temp_files = glob.glob(pattern)
    cleaned = 0
    for file_path in temp_files:
        try:
            os.remove(file_path)
            cleaned += 1
        except:
            continue
    
    if cleaned > 0:
        print(f"[INFO] {cleaned} PDF render dosyası temizlendi")