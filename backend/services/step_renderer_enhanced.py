# services/step_renderer_enhanced.py - PNG'deki gibi detaylı STEP rendering
import os
import uuid
import time
import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import cadquery as cq
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import seaborn as sns

print("[INFO] 🎨 Enhanced STEP Renderer aktif - PNG kalitesinde detaylı görselleştirme")

class StepRendererEnhanced:
    """PNG'deki gibi detaylı STEP rendering servisi"""
    
    def __init__(self):
        self.output_dir = "static/renders"
        self.wireframe_dir = "static/wireframes"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.wireframe_dir, exist_ok=True)
        
        # Render ayarları
        self.high_dpi = 300
        self.standard_dpi = 150
        self.line_styles = {
            'visible': {'color': '#2E4057', 'linewidth': 2.0, 'alpha': 1.0},
            'hidden': {'color': '#8EAEBC', 'linewidth': 1.0, 'alpha': 0.6, 'linestyle': '--'},
            'construction': {'color': '#E74C3C', 'linewidth': 1.5, 'alpha': 0.8, 'linestyle': '-.'},
            'dimension': {'color': '#27AE60', 'linewidth': 1.2, 'alpha': 0.9}
        }
        
        # Font ayarları
        plt.rcParams.update({
            'font.family': 'DejaVu Sans',
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 8,
            'ytick.labelsize': 8,
            'legend.fontsize': 9
        })

    def generate_comprehensive_views(self, step_path: str, analysis_id: str = None, 
                                   views: List[str] = None, include_dimensions: bool = True,
                                   include_materials: bool = True, high_quality: bool = True,
                                   **kwargs) -> Dict[str, Any]:
        """PNG'deki gibi kapsamlı görünüm seti oluştur"""
        
        if views is None:
            views = ['isometric', 'front', 'top', 'side', 'wireframe']
        
        if analysis_id is None:
            analysis_id = str(uuid.uuid4())[:8]
        
        print(f"[INFO] 🎨 Comprehensive rendering başlıyor: {analysis_id}")
        
        try:
            # STEP dosyasını yükle
            assembly = cq.importers.importStep(step_path)
            if not assembly.objects:
                return {"success": False, "message": "STEP dosyasında obje bulunamadı"}
            
            # Ana şekil analizi
            shapes = assembly.objects
            main_shape = max(shapes, key=lambda s: s.Volume()) if shapes else None
            
            if not main_shape:
                return {"success": False, "message": "Ana şekil bulunamadı"}
            
            # Geometrik analiz
            geometry_analysis = self._analyze_geometry(main_shape)
            
            # Render session
            session_id = f"enhanced_{analysis_id}_{int(time.time())}"
            renders = {}
            
            # Her görünüm için detaylı render
            for view in views:
                try:
                    if view == 'isometric':
                        render_result = self._render_isometric_detailed(
                            main_shape, session_id, geometry_analysis, 
                            include_dimensions, include_materials, high_quality
                        )
                    elif view == 'wireframe':
                        render_result = self._render_wireframe_detailed(
                            main_shape, session_id, geometry_analysis, high_quality
                        )
                    elif view in ['front', 'top', 'side']:
                        render_result = self._render_orthographic_detailed(
                            main_shape, session_id, view, geometry_analysis,
                            include_dimensions, high_quality
                        )
                    elif view == 'annotated':
                        render_result = self._render_annotated_view(
                            main_shape, session_id, geometry_analysis, 
                            include_materials, high_quality
                        )
                    elif view == 'dimensioned':
                        render_result = self._render_dimensioned_view(
                            main_shape, session_id, geometry_analysis, high_quality
                        )
                    else:
                        continue
                    
                    if render_result['success']:
                        renders[view] = render_result
                        print(f"[SUCCESS] ✅ {view} view oluşturuldu")
                    else:
                        print(f"[WARN] ⚠️ {view} view başarısız: {render_result.get('message')}")
                        
                except Exception as view_error:
                    print(f"[ERROR] ❌ {view} view hatası: {view_error}")
                    continue
            
            if renders:
                return {
                    "success": True,
                    "message": f"{len(renders)} detaylı render oluşturuldu",
                    "renders": renders,
                    "session_id": session_id,
                    "geometry_analysis": geometry_analysis
                }
            else:
                return {"success": False, "message": "Hiç render oluşturulamadı"}
            
        except Exception as e:
            return {"success": False, "message": f"Comprehensive rendering hatası: {str(e)}"}

    def _analyze_geometry(self, shape) -> Dict[str, Any]:
        """Detaylı geometrik analiz"""
        try:
            bbox = shape.BoundingBox()
            volume = shape.Volume()
            surface_area = shape.Area()
            
            # Edge analizi
            edges = shape.Edges()
            edge_types = {
                'linear': 0,
                'circular': 0,
                'spline': 0,
                'other': 0
            }
            
            for edge in edges:
                try:
                    if hasattr(edge, 'geomType'):
                        geom_type = edge.geomType()
                        if 'LINE' in geom_type.upper():
                            edge_types['linear'] += 1
                        elif 'CIRCLE' in geom_type.upper():
                            edge_types['circular'] += 1
                        elif 'SPLINE' in geom_type.upper() or 'BSPLINE' in geom_type.upper():
                            edge_types['spline'] += 1
                        else:
                            edge_types['other'] += 1
                    else:
                        edge_types['other'] += 1
                except:
                    edge_types['other'] += 1
            
            # Face analizi
            faces = shape.Faces()
            face_types = {
                'planar': 0,
                'cylindrical': 0,
                'spherical': 0,
                'conical': 0,
                'freeform': 0
            }
            
            for face in faces:
                try:
                    if hasattr(face, 'geomType'):
                        geom_type = face.geomType()
                        if 'PLANE' in geom_type.upper():
                            face_types['planar'] += 1
                        elif 'CYLINDER' in geom_type.upper():
                            face_types['cylindrical'] += 1
                        elif 'SPHERE' in geom_type.upper():
                            face_types['spherical'] += 1
                        elif 'CONE' in geom_type.upper():
                            face_types['conical'] += 1
                        else:
                            face_types['freeform'] += 1
                    else:
                        face_types['freeform'] += 1
                except:
                    face_types['freeform'] += 1
            
            # Komplekslik değerlendirmesi
            total_edges = len(edges)
            total_faces = len(faces)
            
            if total_edges > 200 or total_faces > 100:
                complexity = 'high'
            elif total_edges > 50 or total_faces > 25:
                complexity = 'medium'
            else:
                complexity = 'low'
            
            return {
                'bounding_box': {
                    'min': [bbox.xmin, bbox.ymin, bbox.zmin],
                    'max': [bbox.xmax, bbox.ymax, bbox.zmax],
                    'center': [(bbox.xmin + bbox.xmax)/2, (bbox.ymin + bbox.ymax)/2, (bbox.zmin + bbox.zmax)/2],
                    'dimensions': [bbox.xlen, bbox.ylen, bbox.zlen]
                },
                'volume_mm3': volume,
                'surface_area_mm2': surface_area,
                'edge_count': total_edges,
                'face_count': total_faces,
                'edge_types': edge_types,
                'face_types': face_types,
                'complexity': complexity,
                'aspect_ratios': {
                    'xy': bbox.xlen / bbox.ylen if bbox.ylen > 0 else 1,
                    'xz': bbox.xlen / bbox.zlen if bbox.zlen > 0 else 1,
                    'yz': bbox.ylen / bbox.zlen if bbox.zlen > 0 else 1
                }
            }
            
        except Exception as e:
            print(f"[ERROR] Geometrik analiz hatası: {e}")
            return {'error': str(e)}

    def _render_isometric_detailed(self, shape, session_id: str, geometry: Dict, 
                                 include_dimensions: bool, include_materials: bool, 
                                 high_quality: bool) -> Dict[str, Any]:
        """PNG'deki gibi detaylı izometrik görünüm"""
        try:
            filename = f"{session_id}_isometric_detailed.png"
            output_path = os.path.join(self.output_dir, filename)
            
            # Yüksek kalite ayarları
            dpi = self.high_dpi if high_quality else self.standard_dpi
            figsize = (12, 9) if high_quality else (10, 7.5)
            
            fig = plt.figure(figsize=figsize, dpi=dpi)
            
            # Ana 3D subplot - PNG'deki gibi kompozisyon
            ax_main = fig.add_subplot(2, 2, (1, 2), projection='3d')
            ax_front = fig.add_subplot(2, 2, 3)
            ax_top = fig.add_subplot(2, 2, 4)
            
            bbox = geometry['bounding_box']
            center = bbox['center']
            dimensions = bbox['dimensions']
            
            # Ana izometrik görünüm
            self._draw_isometric_wireframe(ax_main, shape, geometry, high_quality)
            
            # Boyut çizgileri ekle
            if include_dimensions:
                self._add_dimension_lines_3d(ax_main, bbox, dimensions)
            
            # Ön görünüm (projection)
            self._draw_orthographic_projection(ax_front, shape, 'front', geometry)
            ax_front.set_title('Ön Görünüm', fontweight='bold', pad=20)
            
            # Üst görünüm (projection)
            self._draw_orthographic_projection(ax_top, shape, 'top', geometry)
            ax_top.set_title('Üst Görünüm', fontweight='bold', pad=20)
            
            # Ana başlık ve metadata
            fig.suptitle('Detaylı STEP Model Analizi', fontsize=16, fontweight='bold', y=0.95)
            
            # Bilgi paneli ekleme
            info_text = self._generate_info_panel(geometry, include_materials)
            fig.text(0.02, 0.02, info_text, fontsize=8, verticalalignment='bottom',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
            
            # Layout optimization
            plt.tight_layout()
            plt.subplots_adjust(top=0.90, bottom=0.15, left=0.05, right=0.95)
            
            # Kaydet
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            return {
                'success': True,
                'view_type': 'isometric_detailed',
                'file_path': output_path,
                'url': f"/static/renders/{filename}",
                'metadata': {
                    'dimensions': dimensions,
                    'dpi': dpi,
                    'includes_dimensions': include_dimensions,
                    'complexity': geometry.get('complexity', 'medium')
                }
            }
            
        except Exception as e:
            print(f"[ERROR] İzometrik detaylı render hatası: {e}")
            plt.close('all')
            return {'success': False, 'message': str(e)}

    def _render_wireframe_detailed(self, shape, session_id: str, geometry: Dict, 
                                 high_quality: bool) -> Dict[str, Any]:
        """PNG'deki gibi detaylı wireframe görünümü"""
        try:
            filename = f"{session_id}_wireframe_detailed.png"
            output_path = os.path.join(self.wireframe_dir, filename)
            
            dpi = self.high_dpi if high_quality else self.standard_dpi
            figsize = (14, 10) if high_quality else (12, 8)
            
            fig = plt.figure(figsize=figsize, dpi=dpi)
            
            # Multiple wireframe views - PNG'deki gibi
            ax1 = fig.add_subplot(2, 3, 1, projection='3d')  # İzometrik
            ax2 = fig.add_subplot(2, 3, 2, projection='3d')  # Ön açılı
            ax3 = fig.add_subplot(2, 3, 3, projection='3d')  # Yan açılı
            ax4 = fig.add_subplot(2, 3, 4)  # Ön görünüm
            ax5 = fig.add_subplot(2, 3, 5)  # Üst görünüm  
            ax6 = fig.add_subplot(2, 3, 6)  # Yan görünüm
            
            bbox = geometry['bounding_box']
            
            # 3D wireframe görünümleri
            self._draw_detailed_wireframe_3d(ax1, shape, view_angle=(30, 45), title='İzometrik')
            self._draw_detailed_wireframe_3d(ax2, shape, view_angle=(15, 30), title='Ön Açılı')
            self._draw_detailed_wireframe_3d(ax3, shape, view_angle=(30, 120), title='Yan Açılı')
            
            # 2D projeksiyonlar
            self._draw_wireframe_projection(ax4, shape, 'front', bbox)
            self._draw_wireframe_projection(ax5, shape, 'top', bbox)
            self._draw_wireframe_projection(ax6, shape, 'side', bbox)
            
            ax4.set_title('Ön Görünüm (X-Z)', fontweight='bold')
            ax5.set_title('Üst Görünüm (X-Y)', fontweight='bold')
            ax6.set_title('Yan Görünüm (Y-Z)', fontweight='bold')
            
            # Ana başlık
            fig.suptitle('Detaylı Wireframe Analizi', fontsize=16, fontweight='bold')
            
            # Wireframe istatistikleri
            wireframe_stats = self._calculate_wireframe_stats(shape)
            stats_text = f"Vertices: {wireframe_stats['vertex_count']} | Edges: {wireframe_stats['edge_count']} | " \
                        f"Faces: {wireframe_stats['face_count']} | Complexity: {geometry.get('complexity', 'N/A')}"
            
            fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
            
            plt.tight_layout()
            plt.subplots_adjust(top=0.92, bottom=0.08)
            
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            return {
                'success': True,
                'view_type': 'wireframe_detailed',
                'file_path': output_path,
                'url': f"/static/wireframes/{filename}",
                'wireframe_data': self.create_detailed_wireframe(shape, include_hidden_lines=True),
                'stats': wireframe_stats
            }
            
        except Exception as e:
            print(f"[ERROR] Wireframe detaylı render hatası: {e}")
            plt.close('all')
            return {'success': False, 'message': str(e)}

    def _render_orthographic_detailed(self, shape, session_id: str, view_type: str, 
                                    geometry: Dict, include_dimensions: bool, 
                                    high_quality: bool) -> Dict[str, Any]:
        """Detaylı ortografik görünüm"""
        try:
            filename = f"{session_id}_{view_type}_detailed.png"
            output_path = os.path.join(self.output_dir, filename)
            
            dpi = self.high_dpi if high_quality else self.standard_dpi
            figsize = (10, 8) if high_quality else (8, 6)
            
            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            
            bbox = geometry['bounding_box']
            
            # Ortografik projeksiyon çiz
            self._draw_orthographic_projection(ax, shape, view_type, geometry)
            
            # Boyut çizgileri
            if include_dimensions:
                self._add_dimension_lines_2d(ax, bbox, view_type)
            
            # Grid ve eksenler
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.set_aspect('equal')
            
            # Başlık ve etiketler
            view_names = {
                'front': 'Ön Görünüm (X-Z Projeksiyonu)',
                'top': 'Üst Görünüm (X-Y Projeksiyonu)',
                'side': 'Yan Görünüm (Y-Z Projeksiyonu)'
            }
            
            ax.set_title(view_names.get(view_type, f'{view_type.title()} Görünüm'), 
                        fontsize=14, fontweight='bold', pad=20)
            
            # Eksen etiketleri
            if view_type == 'front':
                ax.set_xlabel('X (mm)', fontweight='bold')
                ax.set_ylabel('Z (mm)', fontweight='bold')
            elif view_type == 'top':
                ax.set_xlabel('X (mm)', fontweight='bold') 
                ax.set_ylabel('Y (mm)', fontweight='bold')
            elif view_type == 'side':
                ax.set_xlabel('Y (mm)', fontweight='bold')
                ax.set_ylabel('Z (mm)', fontweight='bold')
            
            # Margin ayarlama
            ax.margins(0.1)
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight',
                       facecolor='white', edgecolor='none', format='png')
            plt.close()
            
            return {
                'success': True,
                'view_type': f'{view_type}_detailed',
                'file_path': output_path,
                'url': f"/static/renders/{filename}",
                'metadata': {
                    'view_type': view_type,
                    'includes_dimensions': include_dimensions,
                    'dpi': dpi
                }
            }
            
        except Exception as e:
            print(f"[ERROR] Ortografik detaylı render hatası ({view_type}): {e}")
            plt.close('all')
            return {'success': False, 'message': str(e)}

    def _draw_isometric_wireframe(self, ax, shape, geometry: Dict, high_quality: bool):
        """İzometrik wireframe çizimi"""
        try:
            bbox = geometry['bounding_box']
            center = bbox['center']
            max_dim = max(bbox['dimensions'])
            
            # Kenarları çiz
            edges = shape.Edges()
            edge_count = 0
            
            line_width = 1.5 if high_quality else 1.0
            
            for edge in edges:
                try:
                    vertices = edge.Vertices()
                    if len(vertices) >= 2:
                        v1 = vertices[0].Center()
                        v2 = vertices[-1].Center()
                        
                        ax.plot([v1.x, v2.x], [v1.y, v2.y], [v1.z, v2.z], 
                               color=self.line_styles['visible']['color'],
                               linewidth=line_width, alpha=0.8)
                        edge_count += 1
                        
                except Exception:
                    continue
            
            # Eksen ayarları
            ax.set_xlabel('X (mm)', fontweight='bold')
            ax.set_ylabel('Y (mm)', fontweight='bold')
            ax.set_zlabel('Z (mm)', fontweight='bold')
            ax.set_title('3D İzometrik Görünüm', fontweight='bold', pad=20)
            
            # Görünüm açısı - izometrik
            ax.view_init(elev=30, azim=45)
            
            # Eksen limitleri
            margin = max_dim * 0.1
            ax.set_xlim(center[0] - max_dim/2 - margin, center[0] + max_dim/2 + margin)
            ax.set_ylim(center[1] - max_dim/2 - margin, center[1] + max_dim/2 + margin)
            ax.set_zlim(center[2] - max_dim/2 - margin, center[2] + max_dim/2 + margin)
            
            # Grid
            ax.grid(True, alpha=0.3)
            
            print(f"[DEBUG] İzometrik wireframe: {edge_count} kenar çizildi")
            
        except Exception as e:
            print(f"[ERROR] İzometrik wireframe çizim hatası: {e}")

    def _draw_detailed_wireframe_3d(self, ax, shape, view_angle: Tuple[int, int], title: str):
        """Detaylı 3D wireframe çizimi"""
        try:
            edges = shape.Edges()
            
            for edge in edges:
                try:
                    vertices = edge.Vertices()
                    if len(vertices) >= 2:
                        v1 = vertices[0].Center()
                        v2 = vertices[-1].Center()
                        
                        ax.plot([v1.x, v2.x], [v1.y, v2.y], [v1.z, v2.z], 
                               color='#2E4057', linewidth=1.2, alpha=0.8)
                        
                except Exception:
                    continue
            
            ax.set_title(title, fontweight='bold', fontsize=10)
            ax.view_init(elev=view_angle[0], azim=view_angle[1])
            ax.grid(True, alpha=0.2)
            
            # Eksen etiketlerini küçült
            ax.set_xlabel('X', fontsize=8)
            ax.set_ylabel('Y', fontsize=8)
            ax.set_zlabel('Z', fontsize=8)
            
        except Exception as e:
            print(f"[ERROR] 3D wireframe çizim hatası ({title}): {e}")

    def _draw_wireframe_projection(self, ax, shape, projection: str, bbox: Dict):
        """2D wireframe projeksiyonu"""
        try:
            edges = shape.Edges()
            
            for edge in edges:
                try:
                    vertices = edge.Vertices()
                    if len(vertices) >= 2:
                        v1 = vertices[0].Center()
                        v2 = vertices[-1].Center()
                        
                        if projection == 'front':  # X-Z
                            ax.plot([v1.x, v2.x], [v1.z, v2.z], 'b-', linewidth=1.0, alpha=0.8)
                        elif projection == 'top':  # X-Y
                            ax.plot([v1.x, v2.x], [v1.y, v2.y], 'b-', linewidth=1.0, alpha=0.8)
                        elif projection == 'side':  # Y-Z
                            ax.plot([v1.y, v2.y], [v1.z, v2.z], 'b-', linewidth=1.0, alpha=0.8)
                            
                except Exception:
                    continue
            
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal')
            
            # Eksen etiketleri
            if projection == 'front':
                ax.set_xlabel('X (mm)', fontsize=8)
                ax.set_ylabel('Z (mm)', fontsize=8)
            elif projection == 'top':
                ax.set_xlabel('X (mm)', fontsize=8)
                ax.set_ylabel('Y (mm)', fontsize=8)
            elif projection == 'side':
                ax.set_xlabel('Y (mm)', fontsize=8)
                ax.set_ylabel('Z (mm)', fontsize=8)
            
        except Exception as e:
            print(f"[ERROR] 2D wireframe projeksiyonu hatası ({projection}): {e}")

    def _draw_orthographic_projection(self, ax, shape, view_type: str, geometry: Dict):
        """Ortografik projeksiyon çizimi"""
        try:
            edges = shape.Edges()
            bbox = geometry['bounding_box']
            
            # Visible ve hidden line detection için basit z-buffer yaklaşımı
            visible_lines = []
            hidden_lines = []
            
            for edge in edges:
                try:
                    vertices = edge.Vertices()
                    if len(vertices) >= 2:
                        v1 = vertices[0].Center()
                        v2 = vertices[-1].Center()
                        
                        # Projeksiyon koordinatları
                        if view_type == 'front':  # X-Z projeksiyonu
                            x1, y1, z1 = v1.x, v1.z, v1.y
                            x2, y2, z2 = v2.x, v2.z, v2.y
                        elif view_type == 'top':  # X-Y projeksiyonu
                            x1, y1, z1 = v1.x, v1.y, v1.z
                            x2, y2, z2 = v2.x, v2.y, v2.z
                        elif view_type == 'side':  # Y-Z projeksiyonu
                            x1, y1, z1 = v1.y, v1.z, v1.x
                            x2, y2, z2 = v2.y, v2.z, v2.x
                        else:
                            continue
                        
                        # Basit hidden line detection
                        avg_z = (z1 + z2) / 2
                        center_z = bbox['center'][2] if view_type == 'front' else \
                                  bbox['center'][1] if view_type == 'side' else bbox['center'][0]
                        
                        if avg_z > center_z:
                            visible_lines.append(([x1, x2], [y1, y2]))
                        else:
                            hidden_lines.append(([x1, x2], [y1, y2]))
                            
                except Exception:
                    continue
            
            # Hidden lines çiz (önce)
            for line_x, line_y in hidden_lines:
                ax.plot(line_x, line_y, 
                       color=self.line_styles['hidden']['color'],
                       linewidth=self.line_styles['hidden']['linewidth'],
                       alpha=self.line_styles['hidden']['alpha'],
                       linestyle=self.line_styles['hidden']['linestyle'])
            
            # Visible lines çiz (üstte)
            for line_x, line_y in visible_lines:
                ax.plot(line_x, line_y,
                       color=self.line_styles['visible']['color'],
                       linewidth=self.line_styles['visible']['linewidth'],
                       alpha=self.line_styles['visible']['alpha'])
            
            print(f"[DEBUG] {view_type} projeksiyon: {len(visible_lines)} visible, {len(hidden_lines)} hidden line")
            
        except Exception as e:
            print(f"[ERROR] Ortografik projeksiyon hatası ({view_type}): {e}")

    def _add_dimension_lines_3d(self, ax, bbox: Dict, dimensions: List[float]):
        """3D boyut çizgileri ekleme"""
        try:
            min_pt = bbox['min']
            max_pt = bbox['max']
            
            # X boyutu
            y_offset = min_pt[1] - dimensions[1] * 0.15
            z_offset = min_pt[2] - dimensions[2] * 0.1
            
            ax.plot([min_pt[0], max_pt[0]], [y_offset, y_offset], [z_offset, z_offset],
                   color=self.line_styles['dimension']['color'], linewidth=2)
            
            # Dimension text
            mid_x = (min_pt[0] + max_pt[0]) / 2
            ax.text(mid_x, y_offset, z_offset, f'{dimensions[0]:.1f}mm', 
                   fontsize=8, ha='center', va='bottom', color='green', weight='bold')
            
            # Y boyutu  
            x_offset = min_pt[0] - dimensions[0] * 0.15
            ax.plot([x_offset, x_offset], [min_pt[1], max_pt[1]], [z_offset, z_offset],
                   color=self.line_styles['dimension']['color'], linewidth=2)
            
            mid_y = (min_pt[1] + max_pt[1]) / 2
            ax.text(x_offset, mid_y, z_offset, f'{dimensions[1]:.1f}mm',
                   fontsize=8, ha='center', va='bottom', color='green', weight='bold')
            
            # Z boyutu
            ax.plot([x_offset, x_offset], [y_offset, y_offset], [min_pt[2], max_pt[2]],
                   color=self.line_styles['dimension']['color'], linewidth=2)
            
            mid_z = (min_pt[2] + max_pt[2]) / 2
            ax.text(x_offset, y_offset, mid_z, f'{dimensions[2]:.1f}mm',
                   fontsize=8, ha='center', va='bottom', color='green', weight='bold')
            
        except Exception as e:
            print(f"[ERROR] 3D boyut çizgileri hatası: {e}")

    def _add_dimension_lines_2d(self, ax, bbox: Dict, view_type: str):
        """2D boyut çizgileri ekleme"""
        try:
            if view_type == 'front':  # X-Z
                x_range = [bbox['min'][0], bbox['max'][0]]
                y_range = [bbox['min'][2], bbox['max'][2]]
                dim_labels = [f"X: {bbox['dimensions'][0]:.1f}mm", f"Z: {bbox['dimensions'][2]:.1f}mm"]
            elif view_type == 'top':  # X-Y
                x_range = [bbox['min'][0], bbox['max'][0]]
                y_range = [bbox['min'][1], bbox['max'][1]]
                dim_labels = [f"X: {bbox['dimensions'][0]:.1f}mm", f"Y: {bbox['dimensions'][1]:.1f}mm"]
            elif view_type == 'side':  # Y-Z
                x_range = [bbox['min'][1], bbox['max'][1]]
                y_range = [bbox['min'][2], bbox['max'][2]]
                dim_labels = [f"Y: {bbox['dimensions'][1]:.1f}mm", f"Z: {bbox['dimensions'][2]:.1f}mm"]
            else:
                return
            
            # X ekseni boyut çizgisi
            y_offset = y_range[0] - (y_range[1] - y_range[0]) * 0.1
            ax.annotate('', xy=(x_range[1], y_offset), xytext=(x_range[0], y_offset),
                       arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
            
            mid_x = (x_range[0] + x_range[1]) / 2
            ax.text(mid_x, y_offset - (y_range[1] - y_range[0]) * 0.05, dim_labels[0],
                   ha='center', va='top', fontsize=8, color='green', weight='bold')
            
            # Y ekseni boyut çizgisi
            x_offset = x_range[0] - (x_range[1] - x_range[0]) * 0.1
            ax.annotate('', xy=(x_offset, y_range[1]), xytext=(x_offset, y_range[0]),
                       arrowprops=dict(arrowstyle='<->', color='green', lw=1.5))
            
            mid_y = (y_range[0] + y_range[1]) / 2
            ax.text(x_offset - (x_range[1] - x_range[0]) * 0.05, mid_y, dim_labels[1],
                   ha='right', va='center', fontsize=8, color='green', weight='bold', rotation=90)
            
        except Exception as e:
            print(f"[ERROR] 2D boyut çizgileri hatası ({view_type}): {e}")

    def _generate_info_panel(self, geometry: Dict, include_materials: bool = True) -> str:
        """Bilgi paneli metni oluştur"""
        try:
            dimensions = geometry['bounding_box']['dimensions']
            
            info_lines = [
                f"📐 Boyutlar: {dimensions[0]:.1f} × {dimensions[1]:.1f} × {dimensions[2]:.1f} mm",
                f"📦 Hacim: {geometry.get('volume_mm3', 0):.0f} mm³",
                f"📏 Yüzey Alanı: {geometry.get('surface_area_mm2', 0):.0f} mm²",
                f"🔗 Kenar Sayısı: {geometry.get('edge_count', 0)}",
                f"🔷 Yüzey Sayısı: {geometry.get('face_count', 0)}",
                f"⚡ Komplekslik: {geometry.get('complexity', 'Orta').title()}"
            ]
            
            if include_materials:
                info_lines.extend([
                    "",
                    "🔧 Malzeme Analizi: Aktif",
                    "💰 Maliyet Hesaplama: Mevcut"
                ])
            
            return "\n".join(info_lines)
            
        except Exception as e:
            return f"Bilgi paneli hatası: {str(e)}"

    def _calculate_wireframe_stats(self, shape) -> Dict[str, int]:
        """Wireframe istatistiklerini hesapla"""
        try:
            vertices = shape.Vertices()
            edges = shape.Edges()
            faces = shape.Faces()
            
            return {
                'vertex_count': len(vertices),
                'edge_count': len(edges),
                'face_count': len(faces)
            }
            
        except Exception as e:
            print(f"[ERROR] Wireframe istatistik hatası: {e}")
            return {'vertex_count': 0, 'edge_count': 0, 'face_count': 0}

    def create_detailed_wireframe(self, step_path: str, include_hidden_lines: bool = True,
                                edge_classification: bool = True, high_precision: bool = True) -> Dict[str, Any]:
        """Detaylı wireframe data oluştur"""
        try:
            if isinstance(step_path, str):
                assembly = cq.importers.importStep(step_path)
                if not assembly.objects:
                    return {"success": False, "message": "STEP dosyasında obje bulunamadı"}
                main_shape = max(assembly.objects, key=lambda s: s.Volume())
            else:
                main_shape = step_path  # Direkt shape objesi
            
            start_time = time.time()
            
            # Vertices topla
            vertices = []
            edges = []
            faces = []
            
            # Vertex mapping
            vertex_map = {}
            vertex_index = 0
            
            # Detaylı edge analizi
            shape_edges = main_shape.Edges()
            edge_classifications = {
                'visible': [],
                'hidden': [],
                'construction': [],
                'silhouette': []
            }
            
            for edge in shape_edges:
                try:
                    # Edge vertices
                    edge_vertices = edge.Vertices()
                    if len(edge_vertices) >= 2:
                        start_vertex = edge_vertices[0].Center()
                        end_vertex = edge_vertices[-1].Center()
                        
                        # Vertex indexing
                        start_key = f"{start_vertex.x:.6f},{start_vertex.y:.6f},{start_vertex.z:.6f}"
                        end_key = f"{end_vertex.x:.6f},{end_vertex.y:.6f},{end_vertex.z:.6f}"
                        
                        if start_key not in vertex_map:
                            vertex_map[start_key] = vertex_index
                            vertices.append([
                                round(start_vertex.x, 6),
                                round(start_vertex.y, 6), 
                                round(start_vertex.z, 6)
                            ])
                            vertex_index += 1
                        
                        if end_key not in vertex_map:
                            vertex_map[end_key] = vertex_index
                            vertices.append([
                                round(end_vertex.x, 6),
                                round(end_vertex.y, 6),
                                round(end_vertex.z, 6)
                            ])
                            vertex_index += 1
                        
                        # Edge oluştur
                        edge_info = {
                            'start_index': vertex_map[start_key],
                            'end_index': vertex_map[end_key],
                            'length': edge.Length(),
                            'type': 'visible'  # Default
                        }
                        
                        # Edge classification
                        if edge_classification:
                            try:
                                # Basit edge type detection
                                if hasattr(edge, 'geomType'):
                                    geom_type = edge.geomType()
                                    if 'LINE' in geom_type.upper():
                                        edge_info['geometry_type'] = 'linear'
                                    elif 'CIRCLE' in geom_type.upper():
                                        edge_info['geometry_type'] = 'circular'
                                    else:
                                        edge_info['geometry_type'] = 'curve'
                                else:
                                    edge_info['geometry_type'] = 'unknown'
                            except:
                                edge_info['geometry_type'] = 'unknown'
                        
                        edges.append(edge_info)
                        edge_classifications['visible'].append([vertex_map[start_key], vertex_map[end_key]])
                        
                except Exception as e:
                    continue
            
            # Face analizi
            shape_faces = main_shape.Faces()
            for face in shape_faces:
                try:
                    face_info = {
                        'area': face.Area(),
                        'type': 'unknown'
                    }
                    
                    # Face type detection
                    try:
                        if hasattr(face, 'geomType'):
                            geom_type = face.geomType()
                            if 'PLANE' in geom_type.upper():
                                face_info['type'] = 'planar'
                            elif 'CYLINDER' in geom_type.upper():
                                face_info['type'] = 'cylindrical'
                            elif 'SPHERE' in geom_type.upper():
                                face_info['type'] = 'spherical'
                            else:
                                face_info['type'] = 'freeform'
                    except:
                        pass
                    
                    faces.append(face_info)
                    
                except Exception:
                    continue
            
            # Bounding box hesapla
            bbox = main_shape.BoundingBox()
            bounding_box = {
                'min': [round(bbox.xmin, 3), round(bbox.ymin, 3), round(bbox.zmin, 3)],
                'max': [round(bbox.xmax, 3), round(bbox.ymax, 3), round(bbox.zmax, 3)],
                'center': [
                    round((bbox.xmin + bbox.xmax) / 2, 3),
                    round((bbox.ymin + bbox.ymax) / 2, 3),
                    round((bbox.zmin + bbox.zmax) / 2, 3)
                ],
                'dimensions': [round(bbox.xlen, 3), round(bbox.ylen, 3), round(bbox.zlen, 3)]
            }
            
            # Komplekslik analizi
            total_elements = len(vertices) + len(edges) + len(faces)
            if total_elements > 1000:
                complexity = 'high'
            elif total_elements > 200:
                complexity = 'medium'
            else:
                complexity = 'low'
            
            processing_time = time.time() - start_time
            
            wireframe_data = {
                'vertices': vertices,
                'edges': [{'start': e['start_index'], 'end': e['end_index'], 
                          'type': e['type'], 'length': round(e['length'], 3)} for e in edges],
                'faces': faces,
                'vertex_count': len(vertices),
                'edge_count': len(edges),
                'face_count': len(faces),
                'bounding_box': bounding_box,
                'complexity': complexity,
                'edge_classifications': edge_classifications if edge_classification else None,
                'total_surface_area': round(main_shape.Area(), 3),
                'total_volume': round(main_shape.Volume(), 3),
                'processing_time': round(processing_time, 3),
                'precision_level': 'high' if high_precision else 'standard',
                'includes_hidden_lines': include_hidden_lines,
                'metadata': {
                    'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_elements': total_elements,
                    'edge_types': self._count_edge_types(edges),
                    'face_types': self._count_face_types(faces)
                }
            }
            
            return {
                "success": True,
                "wireframe_data": wireframe_data,
                "processing_time": processing_time,
                "message": f"Detaylı wireframe oluşturuldu: {len(vertices)} vertex, {len(edges)} edge"
            }
            
        except Exception as e:
            print(f"[ERROR] Detaylı wireframe oluşturma hatası: {e}")
            return {"success": False, "message": str(e)}

    def _count_edge_types(self, edges: List[Dict]) -> Dict[str, int]:
        """Edge tiplerini say"""
        counts = {}
        for edge in edges:
            edge_type = edge.get('geometry_type', 'unknown')
            counts[edge_type] = counts.get(edge_type, 0) + 1
        return counts

    def _count_face_types(self, faces: List[Dict]) -> Dict[str, int]:
        """Face tiplerini say"""
        counts = {}
        for face in faces:
            face_type = face.get('type', 'unknown')
            counts[face_type] = counts.get(face_type, 0) + 1
        return counts

    def analyze_step_quality(self, step_path: str) -> Dict[str, Any]:
        """STEP dosyası kalite analizi"""
        try:
            assembly = cq.importers.importStep(step_path)
            if not assembly.objects:
                return {"error": "STEP dosyasında obje bulunamadı"}
            
            main_shape = max(assembly.objects, key=lambda s: s.Volume())
            
            # Geometrik analiz
            geometry = self._analyze_geometry(main_shape)
            
            # Kalite metrikleri
            quality_metrics = {
                'geometric_accuracy': self._assess_geometric_accuracy(main_shape),
                'model_completeness': self._assess_model_completeness(main_shape),
                'surface_quality': self._assess_surface_quality(main_shape),
                'edge_continuity': self._assess_edge_continuity(main_shape)
            }
            
            # Overall score hesapla
            scores = list(quality_metrics.values())
            overall_score = sum(scores) / len(scores) if scores else 0
            
            # Öneriler
            recommendations = self._generate_quality_recommendations(quality_metrics, geometry)
            
            return {
                'complexity_analysis': {
                    'geometric_complexity': geometry.get('complexity', 'medium'),
                    'edge_density': geometry.get('edge_count', 0) / max(geometry.get('volume_mm3', 1), 1) * 1000,
                    'surface_complexity': len(geometry.get('face_types', {}))
                },
                'precision_analysis': {
                    'coordinate_precision': 'high' if geometry.get('edge_count', 0) > 50 else 'medium',
                    'curve_accuracy': 'good',  # Simplified assessment
                    'tolerance_compliance': 'acceptable'
                },
                'quality_metrics': quality_metrics,
                'overall_score': round(overall_score, 2),
                'recommendations': recommendations,
                'processing_notes': [
                    f"Analiz edilen şekil sayısı: {len(assembly.objects)}",
                    f"Ana şekil hacmi: {main_shape.Volume():.0f} mm³",
                    f"Toplam yüzey alanı: {main_shape.Area():.0f} mm²"
                ],
                'wireframe_quality': {
                    'edge_count': geometry.get('edge_count', 0),
                    'vertex_count': len(main_shape.Vertices()),
                    'face_count': len(main_shape.Faces()),
                    'renderable': True
                }
            }
            
        except Exception as e:
            return {"error": f"Kalite analizi hatası: {str(e)}"}

    def _assess_geometric_accuracy(self, shape) -> float:
        """Geometrik doğruluk değerlendirmesi"""
        try:
            # Basit metrikler
            volume = shape.Volume()
            surface_area = shape.Area()
            
            # Volume/surface ratio kontrolü
            if surface_area > 0:
                ratio = volume / surface_area
                # Normalize score (0-100)
                score = min(100, max(0, ratio * 10))
            else:
                score = 0
                
            return round(score, 2)
            
        except Exception:
            return 50.0  # Default score

    def _assess_model_completeness(self, shape) -> float:
        """Model tamlık değerlendirmesi"""
        try:
            # Kapalı solid kontrolü
            if hasattr(shape, 'isValid') and shape.isValid():
                base_score = 80
            else:
                base_score = 40
            
            # Face sayısı kontrolü
            faces = shape.Faces()
            if len(faces) > 6:  # Kompleks model
                base_score += 15
            elif len(faces) > 3:  # Orta model
                base_score += 10
            
            return min(100, base_score)
            
        except Exception:
            return 60.0

    def _assess_surface_quality(self, shape) -> float:
        """Yüzey kalitesi değerlendirmesi"""
        try:
            faces = shape.Faces()
            
            # Face area distribution
            areas = [face.Area() for face in faces]
            if areas:
                area_variance = np.var(areas)
                mean_area = np.mean(areas)
                
                # Normalize variance
                if mean_area > 0:
                    cv = area_variance / (mean_area ** 2)  # Coefficient of variation
                    score = max(0, 100 - cv * 50)
                else:
                    score = 50
            else:
                score = 0
                
            return round(min(100, score), 2)
            
        except Exception:
            return 70.0

    def _assess_edge_continuity(self, shape) -> float:
        """Kenar sürekliliği değerlendirmesi"""
        try:
            edges = shape.Edges()
            
            # Edge length distribution
            lengths = [edge.Length() for edge in edges]
            if lengths:
                length_variance = np.var(lengths)
                mean_length = np.mean(lengths)
                
                if mean_length > 0:
                    cv = length_variance / (mean_length ** 2)
                    score = max(0, 100 - cv * 30)
                else:
                    score = 50
            else:
                score = 0
                
            return round(min(100, score), 2)
            
        except Exception:
            return 75.0

    def _generate_quality_recommendations(self, metrics: Dict, geometry: Dict) -> List[str]:
        """Kalite önerileri oluştur"""
        recommendations = []
        
        # Geometric accuracy
        if metrics.get('geometric_accuracy', 0) < 60:
            recommendations.append("Geometrik doğruluğu artırmak için model toleranslarını kontrol edin")
        
        # Model completeness
        if metrics.get('model_completeness', 0) < 70:
            recommendations.append("Model eksik yüzeyler içeriyor, tamamlayıcı geometri ekleyin")
        
        # Surface quality
        if metrics.get('surface_quality', 0) < 65:
            recommendations.append("Yüzey kalitesini iyileştirmek için mesh yoğunluğunu artırın")
        
        # Edge continuity
        if metrics.get('edge_continuity', 0) < 70:
            recommendations.append("Kenar sürekliliği için G1/G2 süreklilik kontrolü yapın")
        
        # Complexity-based recommendations
        complexity = geometry.get('complexity', 'medium')
        if complexity == 'high':
            recommendations.append("Yüksek komplekslik nedeniyle render süresi uzun olabilir")
        elif complexity == 'low':
            recommendations.append("Model basit, daha detaylı geometri eklenebilir")
        
        if not recommendations:
            recommendations.append("Model kalitesi genel olarak iyi durumda")
        
        return recommendations

    def cleanup_old_renders(self, days_old: int = 7):
        """Eski render dosyalarını temizle"""
        try:
            import glob
            current_time = time.time()
            cleanup_count = 0
            
            # Render klasörlerini tara
            for directory in [self.output_dir, self.wireframe_dir]:
                if os.path.exists(directory):
                    pattern = os.path.join(directory, "*.png")
                    files = glob.glob(pattern)
                    
                    for file_path in files:
                        try:
                            file_age = current_time - os.path.getmtime(file_path)
                            if file_age > (days_old * 24 * 3600):  # Convert to seconds
                                os.remove(file_path)
                                cleanup_count += 1
                        except Exception:
                            continue
            
            print(f"[INFO] 🧹 {cleanup_count} eski render dosyası temizlendi")
            return cleanup_count
            
        except Exception as e:
            print(f"[ERROR] Render temizleme hatası: {e}")
            return 0

    def get_render_stats(self) -> Dict[str, Any]:
        """Render istatistikleri"""
        try:
            import glob
            
            stats = {
                'render_count': 0,
                'wireframe_count': 0,
                'total_size_mb': 0,
                'oldest_file': None,
                'newest_file': None
            }
            
            file_times = []
            
            for directory in [self.output_dir, self.wireframe_dir]:
                if os.path.exists(directory):
                    pattern = os.path.join(directory, "*.png")
                    files = glob.glob(pattern)
                    
                    for file_path in files:
                        try:
                            file_size = os.path.getsize(file_path)
                            stats['total_size_mb'] += file_size / (1024 * 1024)
                            
                            file_time = os.path.getmtime(file_path)
                            file_times.append(file_time)
                            
                            if 'wireframe' in directory:
                                stats['wireframe_count'] += 1
                            else:
                                stats['render_count'] += 1
                                
                        except Exception:
                            continue
            
            if file_times:
                stats['oldest_file'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(min(file_times)))
                stats['newest_file'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(max(file_times)))
            
            stats['total_size_mb'] = round(stats['total_size_mb'], 2)
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}

# Utility functions

def create_step_wireframe_data_enhanced(step_path: str) -> Optional[Dict]:
    """Enhanced wireframe data oluştur - backward compatibility"""
    renderer = StepRendererEnhanced()
    result = renderer.create_detailed_wireframe(step_path)
    return result.get('wireframe_data') if result['success'] else None

def create_wireframe_from_step_analysis(step_analysis: Dict) -> Optional[Dict]:
    """STEP analizi verilerinden wireframe oluştur - PNG uyumlu"""
    try:
        if not step_analysis or step_analysis.get('error'):
            return None
        
        x = step_analysis.get("X (mm)", 50.0)
        y = step_analysis.get("Y (mm)", 30.0)
        z = step_analysis.get("Z (mm)", 20.0)
        
        # Silindirik geometri kontrolü
        cyl_diameter = step_analysis.get("Silindirik Çap (mm)")
        cyl_height = step_analysis.get("Silindirik Yükseklik (mm)")
        
        if cyl_diameter and cyl_height:
            return create_enhanced_cylinder_wireframe(cyl_diameter, cyl_height)
        else:
            return create_enhanced_box_wireframe(x, y, z)
            
    except Exception as e:
        print(f"[ERROR] Analysis wireframe oluşturma hatası: {e}")
        return None

def create_enhanced_box_wireframe(x: float, y: float, z: float) -> Dict:
    """Gelişmiş dikdörtgen prizma wireframe"""
    vertices = [
        [0, 0, 0], [x, 0, 0], [x, y, 0], [0, y, 0],  # alt
        [0, 0, z], [x, 0, z], [x, y, z], [0, y, z]   # üst
    ]
    
    edges = [
        {'start': 0, 'end': 1, 'type': 'visible', 'length': x},  # alt yüz
        {'start': 1, 'end': 2, 'type': 'visible', 'length': y},
        {'start': 2, 'end': 3, 'type': 'visible', 'length': x},
        {'start': 3, 'end': 0, 'type': 'visible', 'length': y},
        {'start': 4, 'end': 5, 'type': 'visible', 'length': x},  # üst yüz
        {'start': 5, 'end': 6, 'type': 'visible', 'length': y},
        {'start': 6, 'end': 7, 'type': 'visible', 'length': x},
        {'start': 7, 'end': 4, 'type': 'visible', 'length': y},
        {'start': 0, 'end': 4, 'type': 'visible', 'length': z},  # dikey kenarlar
        {'start': 1, 'end': 5, 'type': 'visible', 'length': z},
        {'start': 2, 'end': 6, 'type': 'visible', 'length': z},
        {'start': 3, 'end': 7, 'type': 'visible', 'length': z}
    ]
    
    return {
        'vertices': vertices,
        'edges': edges,
        'vertex_count': len(vertices),
        'edge_count': len(edges),
        'face_count': 6,
        'bounding_box': {
            'min': [0, 0, 0],
            'max': [x, y, z],
            'center': [x/2, y/2, z/2],
            'dimensions': [x, y, z]
        },
        'total_volume': x * y * z,
        'total_surface_area': 2 * (x*y + y*z + x*z),
        'complexity': 'low',
        'geometry_type': 'prismatic',
        'source_type': 'analysis_enhanced'
    }

def create_enhanced_cylinder_wireframe(diameter: float, height: float) -> Dict:
    """Gelişmiş silindir wireframe"""
    radius = diameter / 2
    segments = 16  # Daha yüksek çözünürlük
    vertices = []
    edges = []
    
    # Alt ve üst çember vertices
    for i in range(segments):
        angle = (i / segments) * 2 * math.pi
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        
        vertices.append([x, y, 0])        # Alt çember
        vertices.append([x, y, height])   # Üst çember
    
    # Edges with enhanced info
    for i in range(segments):
        next_i = (i + 1) % segments
        
        # Alt çember kenarları
        edges.append({
            'start': i * 2, 
            'end': next_i * 2, 
            'type': 'visible',
            'length': 2 * math.pi * radius / segments
        })
        
        # Üst çember kenarları
        edges.append({
            'start': i * 2 + 1, 
            'end': next_i * 2 + 1, 
            'type': 'visible',
            'length': 2 * math.pi * radius / segments
        })
        
        # Dikey kenarlar
        edges.append({
            'start': i * 2, 
            'end': i * 2 + 1, 
            'type': 'visible',
            'length': height
        })
    
    return {
        'vertices': vertices,
        'edges': edges,
        'vertex_count': len(vertices),
        'edge_count': len(edges),
        'face_count': segments + 2,  # yan yüzeyler + alt + üst
        'bounding_box': {
            'min': [-radius, -radius, 0],
            'max': [radius, radius, height],
            'center': [0, 0, height/2],
            'dimensions': [diameter, diameter, height]
        },
        'total_volume': math.pi * radius * radius * height,
        'total_surface_area': 2 * math.pi * radius * (radius + height),
        'complexity': 'medium',
        'geometry_type': 'cylindrical',
        'source_type': 'analysis_enhanced'
    }