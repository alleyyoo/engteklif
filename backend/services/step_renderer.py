# services/step_renderer.py
import os
import uuid
import cadquery as cq
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
from typing import List, Optional

print("[INFO] ✅ STEP Renderer aktif - Full 3D görselleştirme mevcut")

def generate_step_views(step_path: str, views: List[str] = None, output_dir: str = "static") -> List[str]:
    """
    STEP dosyasından görsel render'lar oluşturur - FULL ACTIVE
    
    Args:
        step_path: STEP dosya yolu
        views: Render edilecek görünümler ['isometric', 'front', 'top', 'side']
        output_dir: Çıktı klasörü
        
    Returns:
        List[str]: Oluşturulan görsel dosyalarının yolları
    """
    if views is None:
        views = ['isometric']
    
    # Çıktı klasörünü oluştur
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[DEBUG] STEP render başlatılıyor: {step_path}")
    
    try:
        # STEP dosyasını yükle
        assembly = cq.importers.importStep(step_path)
        if not assembly.objects:
            print(f"[ERROR] STEP dosyasında obje bulunamadı: {step_path}")
            return []
        
        # Session ID oluştur
        session_id = str(uuid.uuid4())[:8]
        
        generated_files = []
        
        # Ana şekli al
        shapes = assembly.objects
        main_shape = max(shapes, key=lambda s: s.Volume()) if shapes else None
        
        if not main_shape:
            return []
        
        print(f"[DEBUG] Ana şekil bulundu - Volume: {main_shape.Volume():.0f} mm³")
        
        # Her görünüm için render
        for view in views:
            try:
                image_filename = f"{session_id}_{view}.png"
                image_path = os.path.join(output_dir, image_filename)
                
                if view == 'isometric':
                    success = render_isometric_view(main_shape, image_path)
                elif view == 'front':
                    success = render_orthographic_view(main_shape, image_path, 'front')
                elif view == 'top':
                    success = render_orthographic_view(main_shape, image_path, 'top')
                elif view == 'side':
                    success = render_orthographic_view(main_shape, image_path, 'side')
                else:
                    continue
                
                if success and os.path.exists(image_path):
                    generated_files.append(image_path)
                    print(f"[SUCCESS] ✅ {view} görünümü oluşturuldu: {image_path}")
                
            except Exception as e:
                print(f"[ERROR] ❌ {view} görünümü oluşturulamadı: {e}")
                continue
        
        print(f"[INFO] Toplam {len(generated_files)} görsel oluşturuldu")
        return generated_files
        
    except Exception as e:
        print(f"[ERROR] STEP render hatası: {e}")
        return []

def render_isometric_view(shape, output_path: str, size: tuple = (800, 600)) -> bool:
    """İzometrik görünüm render'ı"""
    try:
        print(f"[DEBUG] İzometrik render başlıyor: {output_path}")
        
        # Bounding box al
        bbox = shape.BoundingBox()
        
        # Merkez noktası
        center_x = (bbox.xmin + bbox.xmax) / 2
        center_y = (bbox.ymin + bbox.ymax) / 2
        center_z = (bbox.zmin + bbox.zmax) / 2
        
        # Matplotlib figure oluştur
        fig = plt.figure(figsize=(size[0]/100, size[1]/100), dpi=100)
        ax = fig.add_subplot(111, projection='3d')
        
        # İzometrik görünüm için döndürme
        try:
            rotated_shape = shape.rotate((center_x, center_y, center_z), (1, 0, 0), 35)\
                                .rotate((center_x, center_y, center_z), (0, 0, 1), 45)
        except Exception as rot_error:
            print(f"[WARN] Rotasyon hatası, orijinal şekil kullanılıyor: {rot_error}")
            rotated_shape = shape
        
        # Wireframe çizimi
        edge_count = 0
        try:
            # Kenarları al
            edges = rotated_shape.Edges()
            
            for edge in edges:
                try:
                    # Basit vertex noktalarını kullan
                    vertices = edge.Vertices()
                    if len(vertices) >= 2:
                        v1 = vertices[0].Center()
                        v2 = vertices[-1].Center()
                        ax.plot([v1.x, v2.x], [v1.y, v2.y], [v1.z, v2.z], 'b-', linewidth=1.5)
                        edge_count += 1
                        
                except Exception as edge_error:
                    # Curve-based çizim denemesi
                    try:
                        # Edge'i basit çizgilere böl
                        start = edge.startPoint()
                        end = edge.endPoint()
                        ax.plot([start.x, end.x], [start.y, end.y], [start.z, end.z], 'b-', linewidth=1.5)
                        edge_count += 1
                    except:
                        continue
        
        except Exception as wireframe_error:
            print(f"[WARN] Wireframe çizimi başarısız, vertices kullanılıyor: {wireframe_error}")
            
            # Fallback: Sadece vertices'leri göster
            try:
                vertices = rotated_shape.Vertices()
                if vertices:
                    vertex_points = np.array([[v.Center().x, v.Center().y, v.Center().z] for v in vertices])
                    ax.scatter(vertex_points[:, 0], vertex_points[:, 1], vertex_points[:, 2], 
                             c='blue', s=30, alpha=0.8)
                    print(f"[INFO] {len(vertices)} vertex noktası çizildi")
            except Exception as vertex_error:
                print(f"[ERROR] Vertex rendering de başarısız: {vertex_error}")
                return False
        
        print(f"[DEBUG] {edge_count} kenar çizildi")
        
        # Eksen ayarları
        ax.set_xlabel('X (mm)', fontsize=10)
        ax.set_ylabel('Y (mm)', fontsize=10)
        ax.set_zlabel('Z (mm)', fontsize=10)
        ax.set_title('İzometrik Görünüm', fontsize=12, weight='bold')
        
        # Eksen oranlarını eşitle
        max_range = max(bbox.xlen, bbox.ylen, bbox.zlen) / 2
        mid_x, mid_y, mid_z = center_x, center_y, center_z
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Grid ve arka plan
        ax.grid(True, alpha=0.3)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        
        # Pane colors (daha temiz görünüm)
        ax.xaxis.pane.set_edgecolor('gray')
        ax.yaxis.pane.set_edgecolor('gray')
        ax.zaxis.pane.set_edgecolor('gray')
        ax.xaxis.pane.set_alpha(0.1)
        ax.yaxis.pane.set_alpha(0.1)
        ax.zaxis.pane.set_alpha(0.1)
        
        # Görünüm açısını ayarla
        ax.view_init(elev=20, azim=45)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', format='png')
        plt.close()
        
        print(f"[SUCCESS] İzometrik render kaydedildi: {output_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] İzometrik render hatası: {e}")
        plt.close('all')  # Cleanup
        return False

def render_orthographic_view(shape, output_path: str, view_type: str, size: tuple = (800, 600)) -> bool:
    """Ortografik görünüm render'ı (front, top, side)"""
    try:
        print(f"[DEBUG] {view_type} ortografik render başlıyor: {output_path}")
        
        bbox = shape.BoundingBox()
        
        fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=100)
        
        # Görünüm türüne göre projeksiyon
        if view_type == 'front':  # X-Z düzlemi
            title = 'Ön Görünüm (X-Z)'
            xlabel, ylabel = 'X (mm)', 'Z (mm)'
        elif view_type == 'top':  # X-Y düzlemi
            title = 'Üst Görünüm (X-Y)'
            xlabel, ylabel = 'X (mm)', 'Y (mm)'
        elif view_type == 'side':  # Y-Z düzlemi
            title = 'Yan Görünüm (Y-Z)'
            xlabel, ylabel = 'Y (mm)', 'Z (mm)'
        else:
            return False
        
        # Kenarları çiz
        edges = shape.Edges()
        edge_count = 0
        
        for edge in edges:
            try:
                vertices = edge.Vertices()
                if len(vertices) >= 2:
                    v1 = vertices[0].Center()
                    v2 = vertices[-1].Center()
                    
                    # Koordinatları al
                    if view_type == 'front':
                        x1, y1 = v1.x, v1.z
                        x2, y2 = v2.x, v2.z
                    elif view_type == 'top':
                        x1, y1 = v1.x, v1.y
                        x2, y2 = v2.x, v2.y
                    else:  # side
                        x1, y1 = v1.y, v1.z
                        x2, y2 = v2.y, v2.z
                    
                    ax.plot([x1, x2], [y1, y2], 'b-', linewidth=1.2)
                    edge_count += 1
                    
            except Exception as e:
                continue
        
        print(f"[DEBUG] {edge_count} kenar çizildi ({view_type})")
        
        # Eksen ayarları
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=12, weight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        # Margins
        ax.margins(0.1)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none', format='png')
        plt.close()
        
        print(f"[SUCCESS] {view_type} render kaydedildi: {output_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ortografik render hatası ({view_type}): {e}")
        plt.close('all')  # Cleanup
        return False

def generate_step_thumbnail(step_path: str, output_path: str, size: tuple = (200, 150)) -> bool:
    """STEP dosyası için küçük thumbnail oluştur"""
    try:
        print(f"[DEBUG] Thumbnail oluşturuluyor: {output_path}")
        
        assembly = cq.importers.importStep(step_path)
        if not assembly.objects:
            return False
        
        main_shape = max(assembly.objects, key=lambda s: s.Volume())
        success = render_isometric_view(main_shape, output_path, size)
        
        if success:
            print(f"[SUCCESS] Thumbnail oluşturuldu: {output_path}")
        
        return success
        
    except Exception as e:
        print(f"[ERROR] Thumbnail oluşturma hatası: {e}")
        return False

def create_step_wireframe_data(step_path: str) -> Optional[dict]:
    """STEP dosyasından 3D viewer için wireframe data oluştur"""
    try:
        print(f"[DEBUG] Wireframe data oluşturuluyor: {step_path}")
        
        assembly = cq.importers.importStep(step_path)
        if not assembly.objects:
            return None
        
        main_shape = max(assembly.objects, key=lambda s: s.Volume())
        
        # Vertices ve edges'leri topla
        vertices = []
        edges = []
        
        # Tüm vertex'leri al
        shape_vertices = main_shape.Vertices()
        vertex_map = {}
        
        for i, vertex in enumerate(shape_vertices):
            center = vertex.Center()
            vertices.append([center.x, center.y, center.z])
            vertex_map[id(vertex)] = i
        
        # Edge'leri al
        shape_edges = main_shape.Edges()
        for edge in shape_edges:
            try:
                edge_vertices = edge.Vertices()
                if len(edge_vertices) >= 2:
                    v1_id = id(edge_vertices[0])
                    v2_id = id(edge_vertices[-1])
                    
                    if v1_id in vertex_map and v2_id in vertex_map:
                        edges.append([vertex_map[v1_id], vertex_map[v2_id]])
            except:
                continue
        
        # Bounding box
        bbox = main_shape.BoundingBox()
        
        wireframe_data = {
            'vertices': vertices,
            'edges': edges,
            'vertex_count': len(vertices),
            'edge_count': len(edges),
            'bounding_box': {
                'min': [bbox.xmin, bbox.ymin, bbox.zmin],
                'max': [bbox.xmax, bbox.ymax, bbox.zmax],
                'center': [(bbox.xmin + bbox.xmax)/2, 
                          (bbox.ymin + bbox.ymax)/2, 
                          (bbox.zmin + bbox.zmax)/2],
                'dimensions': [bbox.xlen, bbox.ylen, bbox.zlen]
            }
        }
        
        print(f"[SUCCESS] Wireframe data oluşturuldu - {len(vertices)} vertex, {len(edges)} edge")
        return wireframe_data
        
    except Exception as e:
        print(f"[ERROR] Wireframe data oluşturma hatası: {e}")
        return None

def create_step_cross_section(step_path: str, plane: str = "xy", position: float = 0.0, output_path: str = None) -> Optional[str]:
    """STEP dosyasından kesit görünümü oluştur"""
    try:
        print(f"[DEBUG] Kesit görünümü oluşturuluyor - Plane: {plane}, Position: {position}")
        
        assembly = cq.importers.importStep(step_path)
        if not assembly.objects:
            return None
        
        main_shape = max(assembly.objects, key=lambda s: s.Volume())
        bbox = main_shape.BoundingBox()
        
        # Kesit düzlemini belirle
        if plane.lower() == "xy":
            plane_origin = (0, 0, position)
            plane_normal = (0, 0, 1)
        elif plane.lower() == "xz":
            plane_origin = (0, position, 0)
            plane_normal = (0, 1, 0)
        elif plane.lower() == "yz":
            plane_origin = (position, 0, 0)
            plane_normal = (1, 0, 0)
        else:
            return None
        
        # Kesit al
        try:
            section = main_shape.section(plane_origin=plane_origin, plane_normal=plane_normal)
            if not section:
                print("[WARN] Kesit oluşturulamadı")
                return None
            
            # Output path oluştur
            if not output_path:
                session_id = str(uuid.uuid4())[:8]
                output_path = os.path.join("static", f"section_{session_id}_{plane}_{position:.1f}.png")
            
            # 2D çizim
            section_2d, _ = section.to_2D()
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Section edges çiz
            if hasattr(section_2d, 'Edges'):
                for edge in section_2d.Edges():
                    vertices = edge.Vertices()
                    if len(vertices) >= 2:
                        v1 = vertices[0].Center()
                        v2 = vertices[-1].Center()
                        ax.plot([v1.x, v2.x], [v1.y, v2.y], 'r-', linewidth=2)
            
            ax.set_title(f'Kesit Görünümü - {plane.upper()} @ {position:.1f}mm', fontsize=12, weight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"[SUCCESS] Kesit görünümü kaydedildi: {output_path}")
            return output_path
            
        except Exception as section_error:
            print(f"[ERROR] Kesit alma hatası: {section_error}")
            return None
        
    except Exception as e:
        print(f"[ERROR] Kesit görünümü oluşturma hatası: {e}")
        return None

# Utility functions
def cleanup_temp_images(pattern: str = "static/*_temp_*.png"):
    """Geçici render dosyalarını temizle"""
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
        print(f"[INFO] {cleaned} geçici dosya temizlendi")

def get_step_render_info(step_path: str) -> dict:
    """STEP dosyası render bilgilerini al"""
    try:
        assembly = cq.importers.importStep(step_path)
        if not assembly.objects:
            return {"error": "No objects found"}
        
        shapes = assembly.objects
        main_shape = max(shapes, key=lambda s: s.Volume())
        bbox = main_shape.BoundingBox()
        
        return {
            "file_path": step_path,
            "file_size_mb": round(os.path.getsize(step_path) / (1024*1024), 2),
            "shapes_count": len(shapes),
            "main_volume_mm3": round(main_shape.Volume(), 2),
            "bounding_box": {
                "x_range": [round(bbox.xmin, 2), round(bbox.xmax, 2)],
                "y_range": [round(bbox.ymin, 2), round(bbox.ymax, 2)],
                "z_range": [round(bbox.zmin, 2), round(bbox.zmax, 2)],
                "dimensions": [round(bbox.xlen, 2), round(bbox.ylen, 2), round(bbox.zlen, 2)]
            },
            "render_ready": True
        }
        
    except Exception as e:
        return {"error": str(e), "render_ready": False}