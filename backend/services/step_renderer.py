import os
import uuid
import cadquery as cq
from cadquery import exporters
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

class StepRendererEnhanced:
    """Enhanced STEP renderer with detailed views and annotations"""
    
    def __init__(self, output_dir="static/stepviews"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.base_dir, "..", output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_comprehensive_views(self, step_path, analysis_id=None, include_dimensions=True, include_materials=True, high_quality=True):
        """
        Generate comprehensive views of STEP file
        
        Args:
            step_path: Path to STEP file
            analysis_id: Analysis ID for organizing outputs
            include_dimensions: Add dimension annotations
            include_materials: Add material information
            high_quality: Generate high quality renders
            
        Returns:
            Dict with render results
        """
        try:
            # Create session directory
            session_id = analysis_id or str(uuid.uuid4())
            session_output_dir = os.path.join(self.output_dir, session_id)
            os.makedirs(session_output_dir, exist_ok=True)
            
            print(f"[STEP-RENDER] 🎨 Starting comprehensive rendering for: {step_path}")
            print(f"[STEP-RENDER] 📁 Output directory: {session_output_dir}")
            
            # Import STEP file
            try:
                assembly = cq.importers.importStep(step_path)
                print(f"[STEP-RENDER] ✅ STEP file imported successfully")
            except Exception as e:
                print(f"[STEP-RENDER] ❌ Failed to import STEP file: {e}")
                return {"success": False, "message": f"STEP import failed: {str(e)}"}
            
            # Calculate bounding box and dimensions
            bbox = assembly.val().BoundingBox()
            dimensions = {
                "width": bbox.xlen,
                "height": bbox.ylen,
                "depth": bbox.zlen
            }
            
            print(f"[STEP-RENDER] 📏 Dimensions: W={dimensions['width']:.2f}, H={dimensions['height']:.2f}, D={dimensions['depth']:.2f}")
            
            # Generate multiple views
            renders = {}
            
            # 1. Isometric view (main view)
            isometric_result = self._generate_isometric_view(
                assembly, session_output_dir, dimensions, 
                include_dimensions, high_quality
            )
            if isometric_result['success']:
                renders['isometric'] = isometric_result
                print(f"[STEP-RENDER] ✅ Isometric view generated")
            
            # 2. Wireframe view
            wireframe_result = self._generate_wireframe_view(
                assembly, session_output_dir, dimensions, high_quality
            )
            if wireframe_result['success']:
                renders['wireframe'] = wireframe_result
                print(f"[STEP-RENDER] ✅ Wireframe view generated")
            
            # 3. Dimensioned technical drawing
            if include_dimensions:
                technical_result = self._generate_technical_drawing(
                    assembly, session_output_dir, dimensions
                )
                if technical_result['success']:
                    renders['technical'] = technical_result
                    print(f"[STEP-RENDER] ✅ Technical drawing generated")
            
            # 4. Material-annotated view
            if include_materials:
                material_result = self._generate_material_view(
                    assembly, session_output_dir, dimensions
                )
                if material_result['success']:
                    renders['material'] = material_result
                    print(f"[STEP-RENDER] ✅ Material view generated")
            
            # 5. Standard orthographic views
            ortho_result = self._generate_orthographic_views(
                assembly, session_output_dir, high_quality
            )
            if ortho_result['success']:
                renders.update(ortho_result['views'])
                print(f"[STEP-RENDER] ✅ Orthographic views generated")
            
            print(f"[STEP-RENDER] 🎉 Rendering complete! Generated {len(renders)} views")
            
            return {
                "success": True,
                "renders": renders,
                "session_id": session_id,
                "dimensions": dimensions,
                "total_views": len(renders)
            }
            
        except Exception as e:
            import traceback
            print(f"[STEP-RENDER] ❌ Comprehensive rendering failed: {str(e)}")
            print(f"[STEP-RENDER] 📋 Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Rendering failed: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
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
            print(f"[STEP-RENDER] ❌ Isometric view failed: {str(e)}")
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
            # Note: This is a basic wireframe - for production, you'd want more sophisticated edge extraction
            x_range = [bbox.xmin, bbox.xmax]
            y_range = [bbox.ymin, bbox.ymax]
            z_range = [bbox.zmin, bbox.zmax]
            
            # Draw bounding box as wireframe
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
            print(f"[STEP-RENDER] ❌ Wireframe view failed: {str(e)}")
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
            print(f"[STEP-RENDER] ❌ Technical drawing failed: {str(e)}")
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
            print(f"[STEP-RENDER] ❌ Material view failed: {str(e)}")
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
                    print(f"[STEP-RENDER] ⚠️ {name} view failed: {str(e)}")
                    views[name] = {"success": False, "error": str(e)}
            
            return {
                "success": True,
                "views": views
            }
            
        except Exception as e:
            print(f"[STEP-RENDER] ❌ Orthographic views failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
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
            volume_text = f"Volume: {volume:.0f} mm³"
            draw.text((margin, y_offset), volume_text, fill="blue", font=font)
            
            # Save annotated image
            annotated_path = image_path.replace(".png", "_annotated.png")
            img.save(annotated_path)
            
            return annotated_path
            
        except Exception as e:
            print(f"[STEP-RENDER] ⚠️ Annotation failed: {str(e)}")
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
                "Material: 6061-T6 Aluminum",
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
            print(f"[STEP-RENDER] ⚠️ Material annotation failed: {str(e)}")
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
            print(f"[STEP-RENDER] ⚠️ Excel version creation failed: {str(e)}")
    
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
            print(f"[STEP-RENDER] ⚠️ Dimension lines failed: {str(e)}")
    
    def _estimate_mass(self, dimensions, density=2.7):
        """Estimate mass assuming aluminum"""
        volume_mm3 = dimensions['width'] * dimensions['height'] * dimensions['depth']
        volume_cm3 = volume_mm3 / 1000
        mass_g = volume_cm3 * density
        return mass_g / 1000  # kg


# Legacy function for backward compatibility
def generate_step_views(step_path, output_dir="static/stepviews", views=None):
    """
    Legacy function for backward compatibility
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
        # Return list of file paths for compatibility
        file_paths = []
        for view_name, view_data in result['renders'].items():
            if view_data.get('success') and view_data.get('file_path'):
                file_paths.append(view_data['file_path'])
        return file_paths
    else:
        return []