# services/pdf_renderer.py - PDF Visual Analysis and Rendering Service
import os
import uuid
import tempfile
from typing import Dict, List, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import re


class PDFRendererEnhanced:
    """Enhanced PDF renderer with visual analysis and annotations"""
    
    def __init__(self, output_dir="static/pdfviews"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.base_dir, "..", output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # PDF rendering settings
        self.dpi_high = 300
        self.dpi_standard = 150
        self.max_pages = 5  # Maximum pages to process
    
    def generate_comprehensive_views(
        self, 
        pdf_path: str, 
        analysis_id: str = None, 
        include_annotations: bool = True,
        include_material_overlay: bool = True,
        high_quality: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive visual analysis of PDF
        
        Args:
            pdf_path: Path to PDF file
            analysis_id: Analysis ID for organizing outputs
            include_annotations: Add text recognition annotations
            include_material_overlay: Highlight material text areas
            high_quality: Generate high quality renders
            
        Returns:
            Dict with render results
        """
        try:
            # Create session directory
            session_id = analysis_id or str(uuid.uuid4())
            session_output_dir = os.path.join(self.output_dir, session_id)
            os.makedirs(session_output_dir, exist_ok=True)
            
            print(f"[PDF-RENDER] 📄 Starting comprehensive PDF rendering: {pdf_path}")
            print(f"[PDF-RENDER] 📁 Output directory: {session_output_dir}")
            
            # Convert PDF to images
            try:
                dpi = self.dpi_high if high_quality else self.dpi_standard
                pages = convert_from_path(
                    pdf_path, 
                    dpi=dpi, 
                    first_page=1, 
                    last_page=self.max_pages
                )
                print(f"[PDF-RENDER] ✅ PDF converted to {len(pages)} images")
            except Exception as e:
                print(f"[PDF-RENDER] ❌ Failed to convert PDF: {e}")
                return {"success": False, "message": f"PDF conversion failed: {str(e)}"}
            
            if not pages:
                return {"success": False, "message": "No pages found in PDF"}
            
            # Generate multiple view types
            renders = {}
            
            # 1. Original pages (clean view)
            original_result = self._generate_original_pages(
                pages, session_output_dir, high_quality
            )
            if original_result['success']:
                renders['original'] = original_result
                print(f"[PDF-RENDER] ✅ Original pages generated")
            
            # 2. OCR annotated view
            if include_annotations:
                ocr_result = self._generate_ocr_annotated_view(
                    pages, session_output_dir, high_quality
                )
                if ocr_result['success']:
                    renders['ocr_annotated'] = ocr_result
                    print(f"[PDF-RENDER] ✅ OCR annotated view generated")
            
            # 3. Material detection overlay
            if include_material_overlay:
                material_result = self._generate_material_detection_view(
                    pages, session_output_dir, high_quality
                )
                if material_result['success']:
                    renders['material_detection'] = material_result
                    print(f"[PDF-RENDER] ✅ Material detection view generated")
            
            # 4. Technical drawing analysis
            technical_result = self._generate_technical_analysis_view(
                pages, session_output_dir, high_quality
            )
            if technical_result['success']:
                renders['technical_analysis'] = technical_result
                print(f"[PDF-RENDER] ✅ Technical analysis view generated")
            
            # 5. Enhanced readability view
            enhanced_result = self._generate_enhanced_readability_view(
                pages, session_output_dir, high_quality
            )
            if enhanced_result['success']:
                renders['enhanced_readability'] = enhanced_result
                print(f"[PDF-RENDER] ✅ Enhanced readability view generated")
            
            # 6. Multi-page summary view
            if len(pages) > 1:
                summary_result = self._generate_summary_view(
                    pages, session_output_dir, high_quality
                )
                if summary_result['success']:
                    renders['summary'] = summary_result
                    print(f"[PDF-RENDER] ✅ Summary view generated")
            
            print(f"[PDF-RENDER] 🎉 PDF rendering complete! Generated {len(renders)} views")
            
            return {
                "success": True,
                "renders": renders,
                "session_id": session_id,
                "total_pages": len(pages),
                "total_views": len(renders)
            }
            
        except Exception as e:
            import traceback
            print(f"[PDF-RENDER] ❌ Comprehensive rendering failed: {str(e)}")
            print(f"[PDF-RENDER] 📋 Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"PDF rendering failed: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    def _generate_original_pages(self, pages: List[Image.Image], output_dir: str, high_quality: bool) -> Dict[str, Any]:
        """Generate clean original page views"""
        try:
            page_files = []
            
            for i, page in enumerate(pages):
                # Save each page
                page_filename = f"page_{i+1}.png"
                page_path = os.path.join(output_dir, page_filename)
                
                # Optimize image quality
                if high_quality:
                    page.save(page_path, "PNG", quality=95, optimize=True)
                else:
                    # Compress for standard quality
                    page.thumbnail((1200, 1600), Image.LANCZOS)
                    page.save(page_path, "PNG", quality=85, optimize=True)
                
                # Create Excel-friendly version
                excel_path = page_path.replace(".png", "_excel.png")
                self._create_excel_version(page_path, excel_path)
                
                page_files.append({
                    "page": i + 1,
                    "file_path": page_path.replace(self.base_dir, "").lstrip("/\\"),
                    "excel_path": excel_path.replace(self.base_dir, "").lstrip("/\\")
                })
            
            return {
                "success": True,
                "view_type": "original",
                "pages": page_files,
                "main_page": page_files[0]["file_path"] if page_files else None,
                "quality": "high" if high_quality else "standard"
            }
            
        except Exception as e:
            print(f"[PDF-RENDER] ❌ Original pages generation failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _generate_ocr_annotated_view(self, pages: List[Image.Image], output_dir: str, high_quality: bool) -> Dict[str, Any]:
        """Generate OCR annotated view with text boxes"""
        try:
            annotated_files = []
            
            for i, page in enumerate(pages):
                # Perform OCR with bounding boxes
                page_np = np.array(page)
                
                # Get OCR data with bounding boxes
                ocr_data = pytesseract.image_to_data(
                    page, 
                    lang='tur+eng',
                    output_type=pytesseract.Output.DICT
                )
                
                # Create annotated image
                annotated_img = page.copy()
                draw = ImageDraw.Draw(annotated_img)
                
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except:
                    font = ImageFont.load_default()
                
                # Draw bounding boxes around detected text
                n_boxes = len(ocr_data['level'])
                for j in range(n_boxes):
                    confidence = int(ocr_data['conf'][j])
                    if confidence > 30:  # Only show confident detections
                        x = ocr_data['left'][j]
                        y = ocr_data['top'][j]
                        w = ocr_data['width'][j]
                        h = ocr_data['height'][j]
                        
                        # Color code by confidence
                        if confidence > 80:
                            color = "green"
                        elif confidence > 60:
                            color = "orange"
                        else:
                            color = "red"
                        
                        # Draw bounding box
                        draw.rectangle([x, y, x + w, y + h], outline=color, width=2)
                        
                        # Add confidence score
                        draw.text((x, y - 15), f"{confidence}%", fill=color, font=font)
                
                # Save annotated page
                annotated_filename = f"ocr_page_{i+1}.png"
                annotated_path = os.path.join(output_dir, annotated_filename)
                annotated_img.save(annotated_path, "PNG", quality=95)
                
                # Create Excel version
                excel_path = annotated_path.replace(".png", "_excel.png")
                self._create_excel_version(annotated_path, excel_path)
                
                annotated_files.append({
                    "page": i + 1,
                    "file_path": annotated_path.replace(self.base_dir, "").lstrip("/\\"),
                    "excel_path": excel_path.replace(self.base_dir, "").lstrip("/\\"),
                    "text_boxes": n_boxes
                })
            
            return {
                "success": True,
                "view_type": "ocr_annotated",
                "pages": annotated_files,
                "main_page": annotated_files[0]["file_path"] if annotated_files else None
            }
            
        except Exception as e:
            print(f"[PDF-RENDER] ❌ OCR annotation failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _generate_material_detection_view(self, pages: List[Image.Image], output_dir: str, high_quality: bool) -> Dict[str, Any]:
        """Generate view with material keywords highlighted"""
        try:
            material_files = []
            
            # Common material keywords
            material_keywords = [
                "6061", "7075", "2024", "304", "316", "st37", "s235", "c45",
                "alüminyum", "aluminum", "çelik", "steel", "paslanmaz", "stainless",
                "pirinç", "brass", "titanyum", "titanium", "malzeme", "material"
            ]
            
            for i, page in enumerate(pages):
                # Perform OCR to get text and positions
                ocr_data = pytesseract.image_to_data(
                    page, 
                    lang='tur+eng',
                    output_type=pytesseract.Output.DICT
                )
                
                # Create highlighted image
                highlighted_img = page.copy()
                draw = ImageDraw.Draw(highlighted_img)
                
                try:
                    font = ImageFont.truetype("arial.ttf", 14)
                except:
                    font = ImageFont.load_default()
                
                material_found = []
                
                # Look for material keywords
                n_boxes = len(ocr_data['level'])
                for j in range(n_boxes):
                    text = ocr_data['text'][j].lower().strip()
                    confidence = int(ocr_data['conf'][j])
                    
                    if confidence > 30 and text:
                        # Check if text contains material keywords
                        for keyword in material_keywords:
                            if keyword in text:
                                x = ocr_data['left'][j]
                                y = ocr_data['top'][j]
                                w = ocr_data['width'][j]
                                h = ocr_data['height'][j]
                                
                                # Highlight material text
                                draw.rectangle([x-2, y-2, x + w + 2, y + h + 2], 
                                             outline="red", fill="yellow", width=3)
                                draw.text((x, y + h + 5), f"MATERIAL: {keyword.upper()}", 
                                        fill="red", font=font)
                                
                                material_found.append({
                                    "keyword": keyword,
                                    "text": text,
                                    "confidence": confidence,
                                    "position": (x, y, w, h)
                                })
                                break
                
                # Add summary of found materials
                if material_found:
                    summary_y = 30
                    draw.rectangle([10, 10, 400, summary_y + len(material_found) * 25 + 10], 
                                 fill="white", outline="red", width=2)
                    draw.text((15, 15), "DETECTED MATERIALS:", fill="red", font=font)
                    
                    for idx, mat in enumerate(material_found):
                        draw.text((15, summary_y + idx * 25), 
                                f"• {mat['keyword'].upper()} ({mat['confidence']}%)", 
                                fill="darkred", font=font)
                
                # Save highlighted page
                material_filename = f"material_page_{i+1}.png"
                material_path = os.path.join(output_dir, material_filename)
                highlighted_img.save(material_path, "PNG", quality=95)
                
                # Create Excel version
                excel_path = material_path.replace(".png", "_excel.png")
                self._create_excel_version(material_path, excel_path)
                
                material_files.append({
                    "page": i + 1,
                    "file_path": material_path.replace(self.base_dir, "").lstrip("/\\"),
                    "excel_path": excel_path.replace(self.base_dir, "").lstrip("/\\"),
                    "materials_found": len(material_found),
                    "materials": material_found
                })
            
            return {
                "success": True,
                "view_type": "material_detection",
                "pages": material_files,
                "main_page": material_files[0]["file_path"] if material_files else None
            }
            
        except Exception as e:
            print(f"[PDF-RENDER] ❌ Material detection failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_excel_version(self, input_path: str, output_path: str):
        """Create Excel-friendly smaller version"""
        try:
            img = Image.open(input_path)
            # Resize to 50% for Excel compatibility
            width, height = img.size
            new_size = (int(width * 0.5), int(height * 0.5))
            resized = img.resize(new_size, Image.LANCZOS)
            resized.save(output_path, "PNG", optimize=True)
        except Exception as e:
            print(f"[PDF-RENDER] ⚠️ Excel version creation failed: {str(e)}")
    
    def _generate_technical_analysis_view(self, pages: List[Image.Image], output_dir: str, high_quality: bool) -> Dict[str, Any]:
        """Placeholder for technical analysis view"""
        # Bu fonksiyonu sonraki adımda implement edeceğiz
        return {"success": False, "message": "Technical analysis view not implemented yet"}
    
    def _generate_enhanced_readability_view(self, pages: List[Image.Image], output_dir: str, high_quality: bool) -> Dict[str, Any]:
        """Placeholder for enhanced readability view"""
        # Bu fonksiyonu sonraki adımda implement edeceğiz
        return {"success": False, "message": "Enhanced readability view not implemented yet"}
    
    def _generate_summary_view(self, pages: List[Image.Image], output_dir: str, high_quality: bool) -> Dict[str, Any]:
        """Placeholder for summary view"""
        # Bu fonksiyonu sonraki adımda implement edeceğiz
        return {"success": False, "message": "Summary view not implemented yet"}


# Legacy function for backward compatibility
def generate_pdf_views(pdf_path, output_dir="static/pdfviews", views=None):
    """
    Legacy function for backward compatibility
    """
    renderer = PDFRendererEnhanced(output_dir)
    result = renderer.generate_comprehensive_views(
        pdf_path, 
        include_annotations=True, 
        include_material_overlay=True, 
        high_quality=True
    )
    
    if result['success']:
        # Return list of file paths for compatibility
        file_paths = []
        for view_name, view_data in result['renders'].items():
            if view_data.get('success') and view_data.get('main_page'):
                file_paths.append(view_data['main_page'])
        return file_paths
    else:
        return []