# services/step_renderer.py - COMPLETE ENHANCED WITH 3D MODEL GENERATION

import os
import uuid
import cadquery as cq
from cadquery import exporters
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches
import trimesh
import hashlib
from mpl_toolkits.mplot3d import Axes3D


class StepRendererEnhanced:
    """Enhanced STEP renderer with 3D model generation and STL export"""
    
    def __init__(self, output_dir="static/stepviews"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.base_dir, "..", output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_comprehensive_views(self, step_path, analysis_id=None, include_dimensions=True, include_materials=True, high_quality=True):
        """
        Generate comprehensive views + 3D model export
        
        Args:
            step_path: Path to STEP file
            analysis_id: Analysis ID for organizing outputs
            include_dimensions: Add dimension annotations
            include_materials: Add material information
            high_quality: Generate high quality renders
            
        Returns:
            Dict with render results + 3D model paths
        """
        try:
            # Create session directory
            session_id = analysis_id or str(uuid.uuid4())
            session_output_dir = os.path.join(self.output_dir, session_id)
            os.makedirs(session_output_dir, exist_ok=True)
            
            print(f"[STEP-RENDER-3D] 🎨 Starting comprehensive 3D rendering for: {step_path}")
            print(f"[STEP-RENDER-3D] 📁 Output directory: {session_output_dir}")
            
            # Import STEP file
            try:
                assembly = cq.importers.importStep(step_path)
                print(f"[STEP-RENDER-3D] ✅ STEP file imported successfully")
            except Exception as e:
                print(f"[STEP-RENDER-3D] ❌ Failed to import STEP file: {e}")
                return {"success": False, "message": f"STEP import failed: {str(e)}"}
            
            # Calculate bounding box and dimensions
            bbox = assembly.val().BoundingBox()
            dimensions = {
                "width": bbox.xlen,
                "height": bbox.ylen,
                "depth": bbox.zlen
            }
            
            print(f"[STEP-RENDER-3D] 📏 Dimensions: W={dimensions['width']:.2f}, H={dimensions['height']:.2f}, D={dimensions['depth']:.2f}")
            
            # ✅ GENERATE 3D MODEL FILES
            model_result = self._generate_3d_model_files(assembly, session_output_dir, session_id)
            
            # Generate multiple 2D views
            renders = {}
            
            # 1. Isometric view (main view)
            isometric_result = self._generate_isometric_view(
                assembly, session_output_dir, dimensions, 
                include_dimensions, high_quality
            )
            if isometric_result['success']:
                renders['isometric'] = isometric_result
                print(f"[STEP-RENDER-3D] ✅ Isometric view generated")
            
            # 2. Wireframe view
            wireframe_result = self._generate_wireframe_view(
                assembly, session_output_dir, dimensions, high_quality
            )
            if wireframe_result['success']:
                renders['wireframe'] = wireframe_result
                print(f"[STEP-RENDER-3D] ✅ Wireframe view generated")
            
            # 3. Dimensioned technical drawing
            if include_dimensions:
                technical_result = self._generate_technical_drawing(
                    assembly, session_output_dir, dimensions
                )
                if technical_result['success']:
                    renders['technical'] = technical_result
                    print(f"[STEP-RENDER-3D] ✅ Technical drawing generated")
            
            # 4. Material-annotated view
            if include_materials:
                material_result = self._generate_material_view(
                    assembly, session_output_dir, dimensions
                )
                if material_result['success']:
                    renders['material'] = material_result
                    print(f"[STEP-RENDER-3D] ✅ Material view generated")
            
            # 5. Standard orthographic views
            ortho_result = self._generate_orthographic_views(
                assembly, session_output_dir, high_quality
            )
            if ortho_result['success']:
                renders.update(ortho_result['views'])
                print(f"[STEP-RENDER-3D] ✅ Orthographic views generated")
            
            # ✅ GENERATE 3D VIEWER HTML
            viewer_result = self._generate_3d_viewer_html(session_id, session_output_dir, dimensions)
            
            print(f"[STEP-RENDER-3D] 🎉 Rendering complete! Generated {len(renders)} 2D views + 3D model")
            
            return {
                "success": True,
                "renders": renders,
                "session_id": session_id,
                "dimensions": dimensions,
                "total_views": len(renders),
                # ✅ 3D MODEL DATA
                "model_3d": model_result,
                "viewer_html": viewer_result.get("viewer_path"),
                "stl_path": model_result.get("stl_path"),
                "obj_path": model_result.get("obj_path"),
                "ply_path": model_result.get("ply_path")
            }
            
        except Exception as e:
            import traceback
            print(f"[STEP-RENDER-3D] ❌ Comprehensive rendering failed: {str(e)}")
            print(f"[STEP-RENDER-3D] 📋 Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Rendering failed: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def _generate_3d_model_files(self, assembly, output_dir, session_id):
        """✅ Generate 3D model files (STL, OBJ, PLY) from STEP"""
        try:
            print(f"[3D-MODEL] 🔧 Generating 3D model files...")
            
            # Get the main shape
            shape = assembly.val()
            
            # 1. Generate STL file (for 3D viewer)
            stl_path = os.path.join(output_dir, f"model_{session_id}.stl")
            try:
                # Export to STL using CadQuery
                exporters.export(shape, stl_path)
                stl_relative = f"static/stepviews/{session_id}/model_{session_id}.stl"
                print(f"[3D-MODEL] ✅ STL generated: {stl_path}")
            except Exception as stl_error:
                print(f"[3D-MODEL] ⚠️ STL generation failed: {stl_error}")
                stl_path = None
                stl_relative = None
            
            # 2. Generate OBJ file (alternative format)
            obj_path = os.path.join(output_dir, f"model_{session_id}.obj")
            try:
                # Convert to mesh using trimesh (simplified approach)
                mesh = self._cadquery_to_trimesh(shape)
                if mesh:
                    mesh.export(obj_path)
                    obj_relative = f"static/stepviews/{session_id}/model_{session_id}.obj"
                    print(f"[3D-MODEL] ✅ OBJ generated: {obj_path}")
                else:
                    obj_path = None
                    obj_relative = None
            except Exception as obj_error:
                print(f"[3D-MODEL] ⚠️ OBJ generation failed: {obj_error}")
                obj_path = None
                obj_relative = None
            
            # 3. Generate PLY file (point cloud format)
            ply_path = os.path.join(output_dir, f"model_{session_id}.ply")
            try:
                if mesh:
                    mesh.export(ply_path)
                    ply_relative = f"static/stepviews/{session_id}/model_{session_id}.ply"
                    print(f"[3D-MODEL] ✅ PLY generated: {ply_path}")
                else:
                    ply_path = None
                    ply_relative = None
            except Exception as ply_error:
                print(f"[3D-MODEL] ⚠️ PLY generation failed: {ply_error}")
                ply_path = None
                ply_relative = None
            
            # 4. Generate model statistics
            stats = self._calculate_model_statistics(shape)
            
            return {
                "success": True,
                "stl_path": stl_relative,
                "obj_path": obj_relative,
                "ply_path": ply_relative,
                "stl_file_path": stl_path,
                "obj_file_path": obj_path,
                "ply_file_path": ply_path,
                "statistics": stats,
                "formats": {
                    "stl": bool(stl_path),
                    "obj": bool(obj_path),
                    "ply": bool(ply_path)
                }
            }
            
        except Exception as e:
            print(f"[3D-MODEL] ❌ 3D model generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _cadquery_to_trimesh(self, shape):
        """Convert CadQuery shape to trimesh - simplified bounding box approach"""
        try:
            print(f"[TRIMESH] 🔄 Converting CadQuery shape to trimesh...")
            
            # Get bounding box from CadQuery shape
            bbox = shape.BoundingBox()
            
            # Create bounding box vertices
            vertices = np.array([
                [bbox.xmin, bbox.ymin, bbox.zmin],  # 0: min corner
                [bbox.xmax, bbox.ymin, bbox.zmin],  # 1: max x
                [bbox.xmax, bbox.ymax, bbox.zmin],  # 2: max x,y
                [bbox.xmin, bbox.ymax, bbox.zmin],  # 3: max y
                [bbox.xmin, bbox.ymin, bbox.zmax],  # 4: max z
                [bbox.xmax, bbox.ymin, bbox.zmax],  # 5: max x,z
                [bbox.xmax, bbox.ymax, bbox.zmax],  # 6: max corner
                [bbox.xmin, bbox.ymax, bbox.zmax],  # 7: max y,z
            ])
            
            # Create bounding box faces (triangulated)
            faces = np.array([
                # Bottom face (z = zmin)
                [0, 1, 2], [0, 2, 3],
                # Top face (z = zmax)
                [4, 7, 6], [4, 6, 5],
                # Front face (y = ymin)
                [0, 4, 5], [0, 5, 1],
                # Back face (y = ymax)
                [2, 6, 7], [2, 7, 3],
                # Left face (x = xmin)
                [0, 3, 7], [0, 7, 4],
                # Right face (x = xmax)
                [1, 5, 6], [1, 6, 2],
            ])
            
            # Create trimesh
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
            
            # Validate mesh
            if mesh.is_valid:
                print(f"[TRIMESH] ✅ Valid mesh created: {len(vertices)} vertices, {len(faces)} faces")
                return mesh
            else:
                print(f"[TRIMESH] ⚠️ Invalid mesh created, attempting repair...")
                mesh.fix_normals()
                return mesh
            
        except Exception as e:
            print(f"[TRIMESH] ❌ CadQuery to trimesh conversion failed: {e}")
            return None
    
    def _calculate_model_statistics(self, shape):
        """Calculate 3D model statistics"""
        try:
            bbox = shape.BoundingBox()
            volume = shape.Volume()
            surface_area = shape.Area()
            
            return {
                "volume": round(volume, 3),
                "surface_area": round(surface_area, 3),
                "bounding_box": {
                    "width": round(bbox.xlen, 3),
                    "height": round(bbox.ylen, 3),
                    "depth": round(bbox.zlen, 3),
                    "min": [round(bbox.xmin, 3), round(bbox.ymin, 3), round(bbox.zmin, 3)],
                    "max": [round(bbox.xmax, 3), round(bbox.ymax, 3), round(bbox.zmax, 3)]
                },
                "center_of_mass": [
                    round((bbox.xmin + bbox.xmax) / 2, 3),
                    round((bbox.ymin + bbox.ymax) / 2, 3),
                    round((bbox.zmin + bbox.zmax) / 2, 3)
                ]
            }
        except Exception as e:
            print(f"[STATS] ⚠️ Statistics calculation failed: {e}")
            return {}
    
    def _generate_3d_viewer_html(self, session_id, output_dir, dimensions):
        """✅ Generate custom 3D viewer HTML file"""
        try:
            viewer_html_path = os.path.join(output_dir, "viewer.html")
            
            # Create basic 3D viewer HTML content
            html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EngTeklif 3D Model Viewer - {session_id}</title>
    <style>
        body {{
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            color: #2c3e50;
            overflow: hidden;
        }}
        
        #viewer-container {{
            width: 100vw;
            height: 100vh;
            position: relative;
        }}
        
        canvas {{ display: block; }}
        
        #controls {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            min-width: 250px;
            z-index: 100;
        }}
        
        .control-section {{
            margin-bottom: 15px;
        }}
        
        .section-title {{
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 14px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 4px;
        }}
        
        .control-row {{
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }}
        
        .btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
            font-family: inherit;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
        }}
        
        .btn.active {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        }}
        
        #info-panel {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            min-width: 200px;
            z-index: 100;
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            padding: 4px 0;
            border-bottom: 1px solid rgba(52, 152, 219, 0.2);
        }}
        
        .info-label {{ font-weight: 500; color: #34495e; }}
        .info-value {{ color: #2980b9; font-weight: 600; }}
    </style>
</head>
<body>
    <div id="viewer-container"></div>
    
    <div id="controls">
        <div class="control-section">
            <div class="section-title">🎮 Görünüm</div>
            <div class="control-row">
                <button id="reset-view" class="btn">🔄 Sıfırla</button>
                <button id="fit-view" class="btn">📐 Sığdır</button>
            </div>
            <div class="control-row">
                <button id="wireframe-toggle" class="btn">🕸 Wireframe</button>
                <button id="material-toggle" class="btn">🎨 Materyal</button>
            </div>
        </div>
    </div>
    
    <div id="info-panel">
        <div class="section-title">📊 Model Bilgileri</div>
        <div class="info-row">
            <span class="info-label">Genişlik:</span>
            <span class="info-value">{dimensions['width']:.1f} mm</span>
        </div>
        <div class="info-row">
            <span class="info-label">Yükseklik:</span>
            <span class="info-value">{dimensions['height']:.1f} mm</span>
        </div>
        <div class="info-row">
            <span class="info-label">Derinlik:</span>
            <span class="info-value">{dimensions['depth']:.1f} mm</span>
        </div>
    </div>
    
    <script type="module">
        import * as THREE from 'https://esm.sh/three@0.160.0';
        import {{ OrbitControls }} from 'https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js';
        import {{ STLLoader }} from 'https://esm.sh/three@0.160.0/examples/jsm/loaders/STLLoader.js';
        
        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf0f0f0);
        
        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 10000);
        camera.position.set(100, 100, 100);
        
        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.getElementById('viewer-container').appendChild(renderer.domElement);
        
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        
        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
        directionalLight.position.set(100, 100, 50);
        directionalLight.castShadow = true;
        scene.add(directionalLight);
        
        // Load model
        let model = null;
        const loader = new STLLoader();
        const modelPath = '/static/stepviews/{session_id}/model_{session_id}.stl';
        
        loader.load(modelPath, function(geometry) {{
            geometry.computeVertexNormals();
            geometry.computeBoundingBox();
            
            const center = new THREE.Vector3();
            geometry.boundingBox.getCenter(center);
            geometry.translate(-center.x, -center.y, -center.z);
            
            const material = new THREE.MeshPhongMaterial({{
                color: 0x888888,
                shininess: 100,
                side: THREE.DoubleSide
            }});
            
            model = new THREE.Mesh(geometry, material);
            model.castShadow = true;
            model.receiveShadow = true;
            scene.add(model);
            
            // Fit camera
            const box = geometry.boundingBox;
            const size = new THREE.Vector3();
            box.getSize(size);
            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            const cameraDistance = Math.abs(maxDim / (2 * Math.tan(fov / 2)));
            
            camera.position.set(cameraDistance * 0.8, cameraDistance * 0.6, cameraDistance * 0.8);
            camera.lookAt(0, 0, 0);
            controls.target.set(0, 0, 0);
            controls.update();
        }}, undefined, function(error) {{
            console.error('STL loading failed:', error);
        }});
        
        // Controls
        document.getElementById('reset-view').addEventListener('click', () => {{
            camera.position.set(100, 100, 100);
            camera.lookAt(0, 0, 0);
            controls.target.set(0, 0, 0);
            controls.update();
        }});
        
        document.getElementById('wireframe-toggle').addEventListener('click', (e) => {{
            if (model) {{
                model.material.wireframe = !model.material.wireframe;
                e.target.classList.toggle('active');
            }}
        }});
        
        document.getElementById('material-toggle').addEventListener('click', (e) => {{
            if (model) {{
                const colors = [0x888888, 0x4a90e2, 0xe74c3c, 0x2ecc71, 0xf39c12];
                const currentColor = model.material.color.getHex();
                const currentIndex = colors.indexOf(currentColor);
                const nextIndex = (currentIndex + 1) % colors.length;
                model.material.color.setHex(colors[nextIndex]);
            }}
        }});
        
        // Resize handler
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
        
        // Animation loop
        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();
    </script>
</body>
</html>"""
            
            # Write HTML file
            with open(viewer_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            viewer_relative = f"static/stepviews/{session_id}/viewer.html"
            
            print(f"[3D-VIEWER] ✅ Custom viewer generated: {viewer_html_path}")
            
            return {
                "success": True,
                "viewer_path": viewer_relative,
                "viewer_file_path": viewer_html_path
            }
                
        except Exception as e:
            print(f"[3D-VIEWER] ❌ Viewer generation failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ===== 2D RENDERING METHODS =====
    
    def _generate_isometric_view(self, assembly, output_dir, dimensions, include_dimensions=True, high_quality=True):
        """Generate isometric view with optional dimensions"""
        try:
            # Export as SVG first
            svg_path = os.path.join(output_dir, "isometric.svg")
            exporters.export(
                assembly, 
                svg_path, 
                opt={
                    "projectionDir": (1, 1, 1),
                    "width": 1200 if high_quality else 800,
                    "height": 900 if high_quality else 600
                }
            )
            
            # Convert SVG to PNG
            png_path = svg_path.replace(".svg", ".png")
            cairosvg.svg2png(url=svg_path, write_to=png_path)
            
            # Add dimension annotations if requested
            if include_dimensions:
                annotated_path = self._add_dimension_annotations(
                    png_path, dimensions, "isometric"
                )
                png_path = annotated_path
            
            # Create Excel-friendly version
            excel_path = png_path.replace(".png", "_excel.png")
            self._create_excel_version(png_path, excel_path)
            
            return {
                "success": True,
                "view_type": "isometric",
                "file_path": png_path.replace(self.base_dir, "").lstrip("/\\"),
                "excel_path": excel_path.replace(self.base_dir, "").lstrip("/\\"),
                "svg_path": svg_path.replace(self.base_dir, "").lstrip("/\\"),
                "dimensions": dimensions,
                "quality": "high" if high_quality else "standard"
            }
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ❌ Isometric view failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _generate_wireframe_view(self, assembly, output_dir, dimensions, high_quality=True):
        """Generate wireframe view using matplotlib"""
        try:
            # Extract vertices and edges from CadQuery object
            shape = assembly.val()
            
            # Create matplotlib 3D plot
            fig = plt.figure(figsize=(12, 9) if high_quality else (8, 6))
            ax = fig.add_subplot(111, projection='3d')
            
            # Get bounding box for scaling
            bbox = shape.BoundingBox()
            
            # Draw wireframe (simplified approach)
            self._draw_bounding_box_wireframe(ax, bbox)
            
            # Set equal aspect ratio and labels
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Y (mm)')
            ax.set_zlabel('Z (mm)')
            ax.set_title('Wireframe View')
            
            # Set view angle
            ax.view_init(elev=20, azim=45)
            
            # Save wireframe
            wireframe_path = os.path.join(output_dir, "wireframe.png")
            plt.savefig(wireframe_path, dpi=300 if high_quality else 150, bbox_inches='tight')
            plt.close()
            
            return {
                "success": True,
                "view_type": "wireframe",
                "file_path": wireframe_path.replace(self.base_dir, "").lstrip("/\\"),
                "dimensions": dimensions
            }
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ❌ Wireframe view failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _generate_technical_drawing(self, assembly, output_dir, dimensions):
        """Generate technical drawing with dimensions"""
        try:
            # Create front view with dimensions
            fig, ax = plt.subplots(figsize=(12, 8))
            
            bbox = assembly.val().BoundingBox()
            
            # Draw rectangle representing front view
            rect = Rectangle(
                (bbox.xmin, bbox.zmin), 
                bbox.xlen, 
                bbox.zlen, 
                linewidth=2, 
                edgecolor='black', 
                facecolor='lightblue', 
                alpha=0.3
            )
            ax.add_patch(rect)
            
            # Add dimension lines and text
            self._add_dimension_lines(ax, bbox, dimensions)
            
            ax.set_xlim(bbox.xmin - bbox.xlen * 0.2, bbox.xmax + bbox.xlen * 0.2)
            ax.set_ylim(bbox.zmin - bbox.zlen * 0.2, bbox.zmax + bbox.zlen * 0.2)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Z (mm)')
            ax.set_title('Technical Drawing - Front View')
            
            # Save technical drawing
            technical_path = os.path.join(output_dir, "technical.png")
            plt.savefig(technical_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return {
                "success": True,
                "view_type": "technical",
                "file_path": technical_path.replace(self.base_dir, "").lstrip("/\\"),
                "dimensions": dimensions
            }
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ❌ Technical drawing failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _generate_material_view(self, assembly, output_dir, dimensions):
        """Generate view with material annotations"""
        try:
            # Start with isometric SVG
            svg_path = os.path.join(output_dir, "material.svg")
            exporters.export(
                assembly, 
                svg_path, 
                opt={
                    "projectionDir": (1, 1, 1),
                    "width": 1200,
                    "height": 900
                }
            )
            
            # Convert to PNG
            png_path = svg_path.replace(".svg", ".png")
            cairosvg.svg2png(url=svg_path, write_to=png_path)
            
            # Add material annotations
            annotated_path = self._add_material_annotations(png_path, dimensions)
            
            return {
                "success": True,
                "view_type": "material",
                "file_path": annotated_path.replace(self.base_dir, "").lstrip("/\\"),
                "dimensions": dimensions
            }
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ❌ Material view failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _generate_orthographic_views(self, assembly, output_dir, high_quality=True):
        """Generate standard orthographic views"""
        try:
            views = {}
            view_directions = {
                "front": (0, 0, 1),
                "back": (0, 0, -1),
                "left": (-1, 0, 0),
                "right": (1, 0, 0),
                "top": (0, 1, 0),
                "bottom": (0, -1, 0)
            }
            
            size = (1200, 900) if high_quality else (800, 600)
            
            for name, direction in view_directions.items():
                try:
                    # Export SVG
                    svg_path = os.path.join(output_dir, f"{name}.svg")
                    exporters.export(
                        assembly, 
                        svg_path, 
                        opt={
                            "projectionDir": direction,
                            "width": size[0],
                            "height": size[1]
                        }
                    )
                    
                    # Convert to PNG
                    png_path = svg_path.replace(".svg", ".png")
                    cairosvg.svg2png(url=svg_path, write_to=png_path)
                    
                    views[name] = {
                        "success": True,
                        "view_type": name,
                        "file_path": png_path.replace(self.base_dir, "").lstrip("/\\"),
                        "svg_path": svg_path.replace(self.base_dir, "").lstrip("/\\")
                    }
                    
                except Exception as e:
                    print(f"[STEP-RENDER-3D] ⚠️ {name} view failed: {str(e)}")
                    views[name] = {"success": False, "error": str(e)}
            
            return {
                "success": True,
                "views": views
            }
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ❌ Orthographic views failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # ===== HELPER METHODS =====
    
    def _add_dimension_annotations(self, image_path, dimensions, view_type="isometric"):
        """Add dimension annotations to image"""
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            # Try to use a better font
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # Add dimension text
            width, height = img.size
            margin = 20
            
            # Dimension text
            dim_text = [
                f"Width: {dimensions['width']:.1f} mm",
                f"Height: {dimensions['height']:.1f} mm", 
                f"Depth: {dimensions['depth']:.1f} mm"
            ]
            
            # Position text in corner
            y_offset = margin
            for text in dim_text:
                draw.text((margin, y_offset), text, fill="red", font=font)
                y_offset += 30
            
            # Volume calculation
            volume = dimensions['width'] * dimensions['height'] * dimensions['depth']
            volume_text = f"Volume: {volume:.0f} mm"
            draw.text((margin, y_offset), volume_text, fill="blue", font=font)
            
            # Save annotated image
            annotated_path = image_path.replace(".png", "_annotated.png")
            img.save(annotated_path)
            
            return annotated_path
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ⚠️ Annotation failed: {str(e)}")
            return image_path
    
    def _add_material_annotations(self, image_path, dimensions):
        """Add material information to image"""
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 18)
            except:
                font = ImageFont.load_default()
            
            # Material info (example)
            material_info = [
                "Material: 6061 Aluminum",
                "Density: 2.70 g/cm³",
                f"Est. Mass: {self._estimate_mass(dimensions):.2f} kg",
                "Machinability: Excellent"
            ]
            
            # Position in bottom right
            width, height = img.size
            y_start = height - len(material_info) * 25 - 20
            
            for i, text in enumerate(material_info):
                y_pos = y_start + i * 25
                draw.text((width - 300, y_pos), text, fill="green", font=font)
            
            annotated_path = image_path.replace(".png", "_material.png")
            img.save(annotated_path)
            
            return annotated_path
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ⚠️ Material annotation failed: {str(e)}")
            return image_path
    
    def _create_excel_version(self, input_path, output_path):
        """Create Excel-friendly smaller version"""
        try:
            img = Image.open(input_path)
            # Resize to 33% for Excel compatibility
            width, height = img.size
            new_size = (int(width * 0.33), int(height * 0.33))
            resized = img.resize(new_size, Image.LANCZOS)
            resized.save(output_path)
        except Exception as e:
            print(f"[STEP-RENDER-3D] ⚠️ Excel version creation failed: {str(e)}")
    
    def _draw_bounding_box_wireframe(self, ax, bbox):
        """Draw wireframe bounding box"""
        # Define the 8 vertices of the bounding box
        x = [bbox.xmin, bbox.xmax]
        y = [bbox.ymin, bbox.ymax] 
        z = [bbox.zmin, bbox.zmax]
        
        # Draw the 12 edges of the bounding box
        # Bottom face
        ax.plot([x[0], x[1]], [y[0], y[0]], [z[0], z[0]], 'b-', linewidth=2)
        ax.plot([x[1], x[1]], [y[0], y[1]], [z[0], z[0]], 'b-', linewidth=2)
        ax.plot([x[1], x[0]], [y[1], y[1]], [z[0], z[0]], 'b-', linewidth=2)
        ax.plot([x[0], x[0]], [y[1], y[0]], [z[0], z[0]], 'b-', linewidth=2)
        
        # Top face
        ax.plot([x[0], x[1]], [y[0], y[0]], [z[1], z[1]], 'b-', linewidth=2)
        ax.plot([x[1], x[1]], [y[0], y[1]], [z[1], z[1]], 'b-', linewidth=2)
        ax.plot([x[1], x[0]], [y[1], y[1]], [z[1], z[1]], 'b-', linewidth=2)
        ax.plot([x[0], x[0]], [y[1], y[0]], [z[1], z[1]], 'b-', linewidth=2)
        
        # Vertical edges
        ax.plot([x[0], x[0]], [y[0], y[0]], [z[0], z[1]], 'b-', linewidth=2)
        ax.plot([x[1], x[1]], [y[0], y[0]], [z[0], z[1]], 'b-', linewidth=2)
        ax.plot([x[1], x[1]], [y[1], y[1]], [z[0], z[1]], 'b-', linewidth=2)
        ax.plot([x[0], x[0]], [y[1], y[1]], [z[0], z[1]], 'b-', linewidth=2)
    
    def _add_dimension_lines(self, ax, bbox, dimensions):
        """Add dimension lines to technical drawing"""
        try:
            # Horizontal dimension
            y_dim = bbox.zmin - bbox.zlen * 0.1
            ax.annotate('', xy=(bbox.xmax, y_dim), xytext=(bbox.xmin, y_dim),
                       arrowprops=dict(arrowstyle='<->', color='red', lw=2))
            ax.text((bbox.xmin + bbox.xmax) / 2, y_dim - bbox.zlen * 0.05, 
                   f"{dimensions['width']:.1f}mm", ha='center', va='top', 
                   fontsize=12, color='red', weight='bold')
            
            # Vertical dimension
            x_dim = bbox.xmax + bbox.xlen * 0.1
            ax.annotate('', xy=(x_dim, bbox.zmax), xytext=(x_dim, bbox.zmin),
                       arrowprops=dict(arrowstyle='<->', color='red', lw=2))
            ax.text(x_dim + bbox.xlen * 0.05, (bbox.zmin + bbox.zmax) / 2, 
                   f"{dimensions['depth']:.1f}mm", ha='left', va='center', 
                   fontsize=12, color='red', weight='bold', rotation=90)
            
        except Exception as e:
            print(f"[STEP-RENDER-3D] ⚠️ Dimension lines failed: {str(e)}")
    
    def _estimate_mass(self, dimensions, density=2.7):
        """Estimate mass assuming aluminum"""
        volume_mm3 = dimensions['width'] * dimensions['height'] * dimensions['depth']
        volume_cm3 = volume_mm3 / 1000
        mass_g = volume_cm3 * density
        return mass_g / 1000  # kg


# ✅ 3D Model Utilities
class ModelExporter:
    """Utility class for 3D model export operations"""
    
    @staticmethod
    def export_step_to_stl(step_path, stl_path):
        """Export STEP file to STL format"""
        try:
            print(f"[MODEL-EXPORT] 🔄 Converting STEP to STL: {step_path}")
            
            # Import STEP
            assembly = cq.importers.importStep(step_path)
            shape = assembly.val()
            
            # Export to STL
            exporters.export(shape, stl_path)
            
            print(f"[MODEL-EXPORT] ✅ STL exported: {stl_path}")
            return True
            
        except Exception as e:
            print(f"[MODEL-EXPORT] ❌ STEP to STL conversion failed: {e}")
            return False
    
    @staticmethod
    def create_3d_viewer_data(step_path, session_id):
        """Create comprehensive 3D viewer data package"""
        try:
            print(f"[3D-DATA] 📦 Creating 3D viewer data package...")
            
            # Import STEP
            assembly = cq.importers.importStep(step_path)
            shape = assembly.val()
            
            # Calculate comprehensive model data
            bbox = shape.BoundingBox()
            volume = shape.Volume()
            surface_area = shape.Area()
            
            # Center of mass (simplified)
            center = [
                (bbox.xmin + bbox.xmax) / 2,
                (bbox.ymin + bbox.ymax) / 2,
                (bbox.zmin + bbox.zmax) / 2
            ]
            
            # Bounding box data
            bounding_box = {
                "min": [bbox.xmin, bbox.ymin, bbox.zmin],
                "max": [bbox.xmax, bbox.ymax, bbox.zmax],
                "size": [bbox.xlen, bbox.ylen, bbox.zlen],
                "center": center
            }
            
            return {
                "success": True,
                "session_id": session_id,
                "model_info": {
                    "volume": volume,
                    "surface_area": surface_area,
                    "bounding_box": bounding_box,
                    "center_of_mass": center
                },
                "viewer_config": {
                    "camera_position": [
                        center[0] + bbox.xlen * 1.5,
                        center[1] + bbox.ylen * 1.5,
                        center[2] + bbox.zlen * 1.5
                    ],
                    "camera_target": center,
                    "bounds": bounding_box
                }
            }
            
        except Exception as e:
            print(f"[3D-DATA] ❌ 3D viewer data creation failed: {e}")
            return {"success": False, "error": str(e)}


# Legacy function for backward compatibility (updated)
def generate_step_views(step_path, output_dir="static/stepviews", views=None):
    """
    Legacy function for backward compatibility - now with 3D support
    """
    if views is None:
        views = ["front", "back", "left", "right", "top", "bottom", "isometric"]
    
    renderer = StepRendererEnhanced(output_dir)
    result = renderer.generate_comprehensive_views(
        step_path, 
        include_dimensions=True, 
        include_materials=True, 
        high_quality=True
    )
    
    if result['success']:
        # Return enhanced file paths including 3D models
        file_paths = []
        
        # 2D renders
        for view_name, view_data in result['renders'].items():
            if view_data.get('success') and view_data.get('file_path'):
                file_paths.append(view_data['file_path'])
        
        # 3D model files
        if result.get('model_3d', {}).get('success'):
            model_data = result['model_3d']
            if model_data.get('stl_path'):
                file_paths.append(model_data['stl_path'])
            if model_data.get('obj_path'):
                file_paths.append(model_data['obj_path'])
        
        # 3D viewer
        if result.get('viewer_html'):
            file_paths.append(result['viewer_html'])
        
        return file_paths
    else:
        return []