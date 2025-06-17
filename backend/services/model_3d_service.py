# services/model_3d_service.py - Complete 3D Model Generation Service
import os
import uuid
import json
import time
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from models.file_analysis import FileAnalysis

print("[INFO] ✅ 3D Model Service - Full Active with Isometric View Generation")

class Model3DService:
    def __init__(self):
        self.output_dir = "static"
        self.temp_dir = "temp"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def generate_3d_views_from_analysis(self, analysis_id: str, views: List[str] = None) -> Dict[str, Any]:
        """
        FileAnalysis'den 3D görünümler oluştur - app.py benzeri
        
        Args:
            analysis_id: Analiz ID'si
            views: Oluşturulacak görünümler ['isometric', 'front', 'top', 'side']
            
        Returns:
            Dict: Oluşturulan dosya yolları ve bilgiler
        """
        if views is None:
            views = ['isometric']
        
        try:
            print(f"[DEBUG] 3D views oluşturuluyor - Analysis ID: {analysis_id}")
            
            # Analiz verisini al
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis:
                return {
                    "success": False,
                    "message": "Analiz bulunamadı",
                    "views": []
                }
            
            # STEP analizi var mı kontrol et
            step_analysis = analysis.get('step_analysis', {})
            if not step_analysis or step_analysis.get('error'):
                return {
                    "success": False,
                    "message": "STEP analizi mevcut değil",
                    "views": []
                }
            
            # Session ID oluştur
            session_id = f"{analysis_id}_{str(uuid.uuid4())[:8]}"
            
            generated_views = []
            
            # Her görünüm için render
            for view in views:
                try:
                    view_result = self._generate_single_view(
                        step_analysis, 
                        view, 
                        session_id,
                        analysis.get('file_type', 'unknown')
                    )
                    
                    if view_result['success']:
                        generated_views.append(view_result)
                        print(f"[SUCCESS] ✅ {view} görünümü oluşturuldu")
                    
                except Exception as e:
                    print(f"[ERROR] ❌ {view} görünümü oluşturulamadı: {e}")
                    continue
            
            # Ana isometric view'ı analiz kaydına ekle
            isometric_view = next(
                (v for v in generated_views if v['view'] == 'isometric'), 
                None
            )
            
            if isometric_view:
                # FileAnalysis'e isometric_view yolunu kaydet
                FileAnalysis.update_analysis(analysis_id, {
                    "isometric_view": isometric_view['file_path'],
                    "3d_views_generated": True,
                    "3d_session_id": session_id
                })
            
            return {
                "success": True,
                "message": f"{len(generated_views)} görünüm oluşturuldu",
                "views": generated_views,
                "session_id": session_id,
                "analysis_id": analysis_id
            }
            
        except Exception as e:
            print(f"[ERROR] 3D views oluşturma hatası: {e}")
            return {
                "success": False,
                "message": f"3D görünüm hatası: {str(e)}",
                "views": []
            }
    
    def _generate_single_view(self, step_analysis: Dict[str, Any], view: str, 
                            session_id: str, file_type: str) -> Dict[str, Any]:
        """Tek görünüm oluştur"""
        try:
            # Dosya yolu oluştur
            filename = f"model_{session_id}_{view}.png"
            file_path = os.path.join(self.output_dir, filename)
            
            # Boyutları al
            x = step_analysis.get("X (mm)", 50.0)
            y = step_analysis.get("Y (mm)", 30.0)
            z = step_analysis.get("Z (mm)", 20.0)
            
            # Görünüm tipine göre render
            if view == 'isometric':
                success = self._render_isometric(x, y, z, file_path, step_analysis)
            elif view == 'front':
                success = self._render_orthographic(x, y, z, file_path, 'front')
            elif view == 'top':
                success = self._render_orthographic(x, y, z, file_path, 'top')
            elif view == 'side':
                success = self._render_orthographic(x, y, z, file_path, 'side')
            else:
                return {"success": False, "message": f"Desteklenmeyen görünüm: {view}"}
            
            if success and os.path.exists(file_path):
                # Dosya boyutunu al
                file_size = os.path.getsize(file_path)
                
                return {
                    "success": True,
                    "view": view,
                    "file_path": file_path,
                    "filename": filename,
                    "file_size": file_size,
                    "dimensions": [x, y, z],
                    "file_type": file_type,
                    "created_at": time.time()
                }
            else:
                return {
                    "success": False,
                    "view": view,
                    "message": "Render oluşturulamadı"
                }
                
        except Exception as e:
            return {
                "success": False,
                "view": view,
                "message": f"Render hatası: {str(e)}"
            }
    
    def _render_isometric(self, x: float, y: float, z: float, output_path: str, 
                         step_analysis: Dict[str, Any]) -> bool:
        """İzometrik görünüm render'ı - app.py benzeri"""
        try:
            print(f"[DEBUG] İzometrik render: {x}x{y}x{z} mm -> {output_path}")
            
            fig = plt.figure(figsize=(10, 8), dpi=150)
            ax = fig.add_subplot(111, projection='3d')
            
            # Silindirik geometri kontrolü
            cyl_diameter = step_analysis.get("Silindirik Çap (mm)")
            cyl_height = step_analysis.get("Silindirik Yükseklik (mm)")
            
            if cyl_diameter and cyl_height and cyl_diameter > 0 and cyl_height > 0:
                # Silindir çiz
                self._render_cylinder(ax, cyl_diameter/2, cyl_height)
                title = f'3D Model - Silindirik\nÇap: {cyl_diameter}mm, Yükseklik: {cyl_height}mm'
                print(f"[DEBUG] Silindirik model: Çap {cyl_diameter}mm, Yükseklik {cyl_height}mm")
            else:
                # Dikdörtgen prizma çiz
                self._render_box(ax, x, y, z)
                title = f'3D Model - Prizmatik\n{x}x{y}x{z} mm'
                print(f"[DEBUG] Prizmatik model: {x}x{y}x{z} mm")
            
            # Hacim bilgisi ekle
            volume = step_analysis.get("Ürün Hacmi (mm³)")
            if volume:
                title += f'\nHacim: {volume:,.0f} mm³'
            
            # Material bilgisi ekle (varsa)
            analysis_method = step_analysis.get("method", "")
            if analysis_method:
                title += f'\n({analysis_method})'
            
            # Styling
            ax.set_xlabel('X (mm)', fontsize=10)
            ax.set_ylabel('Y (mm)', fontsize=10)
            ax.set_zlabel('Z (mm)', fontsize=10)
            ax.set_title(title, fontsize=12, weight='bold', pad=20)
            
            # İzometrik görünüm açısı
            ax.view_init(elev=25, azim=45)
            
            # Grid ve arka plan
            ax.grid(True, alpha=0.3)
            
            # Pane styling
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.xaxis.pane.set_edgecolor('gray')
            ax.yaxis.pane.set_edgecolor('gray')
            ax.zaxis.pane.set_edgecolor('gray')
            ax.xaxis.pane.set_alpha(0.1)
            ax.yaxis.pane.set_alpha(0.1)
            ax.zaxis.pane.set_alpha(0.1)
            
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
            
            print(f"[SUCCESS] İzometrik render kaydedildi: {output_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] İzometrik render hatası: {e}")
            plt.close('all')
            return False
    
    def _render_box(self, ax, x: float, y: float, z: float):
        """3D kutu çiz - app.py benzeri"""
        # Kutu köşeleri
        vertices = np.array([
            [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],  # alt yüz
            [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]   # üst yüz
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
        
        # Yüzleri çiz (şeffaf)
        poly3d = Poly3DCollection(faces, alpha=0.7, facecolor='lightblue', edgecolor='navy')
        ax.add_collection3d(poly3d)
        
        # Kenarları çiz (wireframe)
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # alt
            [4, 5], [5, 6], [6, 7], [7, 4],  # üst
            [0, 4], [1, 5], [2, 6], [3, 7]   # dikey
        ]
        
        for edge in edges:
            points = vertices[edge]
            ax.plot3D(points[:, 0], points[:, 1], points[:, 2], 'b-', linewidth=2)
    
    def _render_cylinder(self, ax, radius: float, height: float, segments: int = 20):
        """3D silindir çiz - app.py benzeri"""
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
    
    def _render_orthographic(self, x: float, y: float, z: float, output_path: str, view_type: str) -> bool:
        """Ortografik görünüm render'ı"""
        try:
            print(f"[DEBUG] {view_type} ortografik render: {x}x{y}x{z} mm")
            
            fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
            
            # Görünüm türüne göre projeksiyon
            if view_type == 'front':  # X-Z düzlemi
                ax.add_patch(plt.Rectangle((0, 0), x, z, fill=False, edgecolor='blue', linewidth=2))
                ax.set_xlim(-x*0.1, x*1.1)
                ax.set_ylim(-z*0.1, z*1.1)
                ax.set_xlabel('X (mm)')
                ax.set_ylabel('Z (mm)')
                title = f'Ön Görünüm - {x}x{z} mm'
                
            elif view_type == 'top':  # X-Y düzlemi
                ax.add_patch(plt.Rectangle((0, 0), x, y, fill=False, edgecolor='blue', linewidth=2))
                ax.set_xlim(-x*0.1, x*1.1)
                ax.set_ylim(-y*0.1, y*1.1)
                ax.set_xlabel('X (mm)')
                ax.set_ylabel('Y (mm)')
                title = f'Üst Görünüm - {x}x{y} mm'
                
            else:  # side - Y-Z düzlemi
                ax.add_patch(plt.Rectangle((0, 0), y, z, fill=False, edgecolor='blue', linewidth=2))
                ax.set_xlim(-y*0.1, y*1.1)
                ax.set_ylim(-z*0.1, z*1.1)
                ax.set_xlabel('Y (mm)')
                ax.set_ylabel('Z (mm)')
                title = f'Yan Görünüm - {y}x{z} mm'
            
            ax.set_title(title, fontsize=12, weight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            print(f"[SUCCESS] {view_type} render kaydedildi: {output_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ortografik render hatası ({view_type}): {e}")
            plt.close('all')
            return False
    
    def generate_wireframe_data(self, analysis_id: str) -> Dict[str, Any]:
        """
        3D viewer için wireframe data oluştur - upload_controller.py ile uyumlu
        """
        try:
            print(f"[DEBUG] Wireframe data oluşturuluyor - Analysis ID: {analysis_id}")
            
            # Analiz verisini al
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis:
                return {
                    "success": False,
                    "message": "Analiz bulunamadı"
                }
            
            # STEP analizi kontrol et
            step_analysis = analysis.get('step_analysis', {})
            if not step_analysis or step_analysis.get('error'):
                return {
                    "success": False,
                    "message": "STEP analizi mevcut değil"
                }
            
            # Gerçek STEP dosyası varsa onu kullan
            file_path = analysis.get('file_path')
            if file_path and os.path.exists(file_path) and file_path.lower().endswith(('.step', '.stp')):
                try:
                    from services.step_renderer import create_step_wireframe_data
                    wireframe_data = create_step_wireframe_data(file_path)
                    if wireframe_data:
                        return {
                            "success": True,
                            "wireframe_data": wireframe_data,
                            "source": "real_step_file"
                        }
                except ImportError:
                    print("[WARN] STEP renderer mevcut değil, basit wireframe kullanılıyor")
                except Exception as e:
                    print(f"[WARN] STEP wireframe hatası: {e}")
            
            # Fallback: STEP analizinden basit wireframe oluştur
            wireframe_data = self._create_simple_wireframe(step_analysis)
            
            return {
                "success": True,
                "wireframe_data": wireframe_data,
                "source": "step_analysis_data"
            }
            
        except Exception as e:
            print(f"[ERROR] Wireframe data hatası: {e}")
            return {
                "success": False,
                "message": f"Wireframe data hatası: {str(e)}"
            }
    
    def _create_simple_wireframe(self, step_analysis: Dict[str, Any]) -> dict:
        """STEP analizinden basit wireframe oluştur"""
        try:
            x = step_analysis.get("X (mm)", 50.0)
            y = step_analysis.get("Y (mm)", 30.0)
            z = step_analysis.get("Z (mm)", 20.0)
            
            # Silindirik geometri kontrolü
            cyl_diameter = step_analysis.get("Silindirik Çap (mm)")
            cyl_height = step_analysis.get("Silindirik Yükseklik (mm)")
            
            if cyl_diameter and cyl_height:
                # Silindirik wireframe
                return self._create_cylindrical_wireframe(cyl_diameter/2, cyl_height)
            else:
                # Kutu wireframe
                return self._create_box_wireframe(x, y, z)
                
        except Exception as e:
            print(f"[ERROR] Basit wireframe oluşturma hatası: {e}")
            # En temel fallback
            return self._create_box_wireframe(50, 30, 20)
    
    def _create_box_wireframe(self, x: float, y: float, z: float) -> dict:
        """Kutu wireframe data"""
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
            'geometry_type': 'box',
            'bounding_box': {
                'min': [0, 0, 0],
                'max': [x, y, z],
                'center': [x/2, y/2, z/2],
                'dimensions': [x, y, z]
            }
        }
    
    def _create_cylindrical_wireframe(self, radius: float, height: float, segments: int = 16) -> dict:
        """Silindirik wireframe data"""
        vertices = []
        edges = []
        
        # Alt ve üst çember vertices
        for i in range(segments):
            angle = (i / segments) * 2 * np.pi
            x_pos = radius * np.cos(angle)
            y_pos = radius * np.sin(angle)
            vertices.append([x_pos, y_pos, 0])      # Alt çember
            vertices.append([x_pos, y_pos, height]) # Üst çember
        
        # Edges
        for i in range(segments):
            next_i = (i + 1) % segments
            # Alt çember
            edges.append([i * 2, next_i * 2])
            # Üst çember  
            edges.append([i * 2 + 1, next_i * 2 + 1])
            # Dikey bağlantılar
            edges.append([i * 2, i * 2 + 1])
        
        return {
            'vertices': vertices,
            'edges': edges,
            'vertex_count': len(vertices),
            'edge_count': len(edges),
            'geometry_type': 'cylinder',
            'bounding_box': {
                'min': [-radius, -radius, 0],
                'max': [radius, radius, height],
                'center': [0, 0, height/2],
                'dimensions': [radius*2, radius*2, height]
            }
        }
    
    def cleanup_old_renders(self, days_old: int = 7):
        """Eski render dosyalarını temizle"""
        try:
            import glob
            import time
            
            pattern = os.path.join(self.output_dir, "model_*.png")
            files = glob.glob(pattern)
            current_time = time.time()
            cleaned = 0
            
            for file_path in files:
                try:
                    file_time = os.path.getmtime(file_path)
                    if (current_time - file_time) > (days_old * 24 * 3600):
                        os.remove(file_path)
                        cleaned += 1
                except:
                    continue
            
            if cleaned > 0:
                print(f"[INFO] {cleaned} eski render dosyası temizlendi")
                
        except Exception as e:
            print(f"[WARN] Render temizleme hatası: {e}")
    
    def get_analysis_3d_info(self, analysis_id: str) -> Dict[str, Any]:
        """Analiz için 3D bilgilerini al"""
        try:
            analysis = FileAnalysis.find_by_id(analysis_id)
            if not analysis:
                return {"error": "Analiz bulunamadı"}
            
            step_analysis = analysis.get('step_analysis', {})
            
            return {
                "analysis_id": analysis_id,
                "has_step_analysis": bool(step_analysis and not step_analysis.get('error')),
                "has_isometric_view": bool(analysis.get('isometric_view')),
                "3d_views_generated": analysis.get('3d_views_generated', False),
                "3d_session_id": analysis.get('3d_session_id'),
                "file_type": analysis.get('file_type'),
                "dimensions": {
                    "x": step_analysis.get("X (mm)", 0),
                    "y": step_analysis.get("Y (mm)", 0), 
                    "z": step_analysis.get("Z (mm)", 0)
                },
                "volume_mm3": step_analysis.get("Ürün Hacmi (mm³)", 0),
                "geometry_type": "cylindrical" if step_analysis.get("Silindirik Çap (mm)") else "prismatic",
                "render_ready": True
            }
            
        except Exception as e:
            return {"error": str(e), "render_ready": False}