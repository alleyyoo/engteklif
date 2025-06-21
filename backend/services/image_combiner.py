import os
from PIL import Image, ImageDraw, ImageFont
import math
from typing import List, Dict, Tuple, Optional

class ImageCombiner:
    """STEP render görünümlerini tek resimde birleştiren servis"""
    
    def __init__(self):
        self.default_font_size = 24
        self.title_font_size = 32
        self.margin = 20
        self.label_height = 40
        
    def combine_step_renders(
        self, 
        renders: Dict[str, Dict], 
        output_path: str,
        layout: str = "grid",
        background_color: str = "white",
        include_labels: bool = True,
        include_title: bool = True,
        title: str = "STEP File Analysis"
    ) -> Dict[str, any]:
        """
        STEP render'larını birleştir
        
        Args:
            renders: Enhanced renders dictionary
            output_path: Çıktı dosya yolu
            layout: "grid", "horizontal", "vertical", "showcase"
            background_color: Arkaplan rengi
            include_labels: Görünüm etiketleri ekle
            include_title: Başlık ekle
            title: Ana başlık
            
        Returns:
            Dict with combination result
        """
        try:
            # Geçerli render'ları filtrele
            valid_renders = self._filter_valid_renders(renders)
            
            if not valid_renders:
                return {
                    "success": False,
                    "message": "Birleştirilebilir geçerli render bulunamadı"
                }
            
            print(f"[IMAGE-COMBINER] 🎨 {len(valid_renders)} render birleştiriliyor...")
            
            # Layout'a göre birleştir
            if layout == "grid":
                result = self._combine_grid_layout(
                    valid_renders, output_path, background_color, 
                    include_labels, include_title, title
                )
            elif layout == "horizontal":
                result = self._combine_horizontal_layout(
                    valid_renders, output_path, background_color,
                    include_labels, include_title, title
                )
            elif layout == "vertical":
                result = self._combine_vertical_layout(
                    valid_renders, output_path, background_color,
                    include_labels, include_title, title
                )
            elif layout == "showcase":
                result = self._combine_showcase_layout(
                    valid_renders, output_path, background_color,
                    include_labels, include_title, title
                )
            else:
                return {
                    "success": False,
                    "message": f"Desteklenmeyen layout: {layout}"
                }
            
            if result["success"]:
                print(f"[IMAGE-COMBINER] ✅ Birleştirme tamamlandı: {output_path}")
            
            return result
            
        except Exception as e:
            print(f"[IMAGE-COMBINER] ❌ Birleştirme hatası: {str(e)}")
            return {
                "success": False,
                "message": f"Birleştirme hatası: {str(e)}"
            }
    
    def _filter_valid_renders(self, renders: Dict[str, Dict]) -> List[Tuple[str, str]]:
        """Geçerli render'ları filtrele ve sırala"""
        valid_renders = []
        
        # Öncelik sırası
        priority_order = [
            "isometric",    # Ana görünüm
            "front",        # Ön görünüm
            "wireframe",    # Tel kafes
            "technical",    # Teknik çizim
            "material",     # Malzeme görünümü
            "top",          # Üst görünüm
            "right",        # Sağ görünüm
            "back",         # Arka görünüm
            "left",         # Sol görünüm
            "bottom"        # Alt görünüm
        ]
        
        # Öncelik sırasına göre ekle
        for view_name in priority_order:
            if view_name in renders:
                render_data = renders[view_name]
                if render_data.get("success") and render_data.get("file_path"):
                    file_path = self._get_full_path(render_data["file_path"])
                    if os.path.exists(file_path):
                        valid_renders.append((view_name, file_path))
        
        # Öncelik listesinde olmayan diğer render'ları ekle
        for view_name, render_data in renders.items():
            if view_name not in priority_order:
                if render_data.get("success") and render_data.get("file_path"):
                    file_path = self._get_full_path(render_data["file_path"])
                    if os.path.exists(file_path):
                        valid_renders.append((view_name, file_path))
        
        return valid_renders
    
    def _get_full_path(self, file_path: str) -> str:
        """Tam dosya yolunu al"""
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(os.getcwd(), file_path)
    
    def _combine_grid_layout(
        self, 
        valid_renders: List[Tuple[str, str]], 
        output_path: str,
        background_color: str,
        include_labels: bool,
        include_title: bool,
        title: str
    ) -> Dict[str, any]:
        """Grid layout - 2x2, 3x2, vs."""
        try:
            # Grid boyutunu hesapla
            total_images = len(valid_renders)
            if total_images <= 4:
                cols, rows = 2, 2
            elif total_images <= 6:
                cols, rows = 3, 2
            elif total_images <= 9:
                cols, rows = 3, 3
            else:
                cols, rows = 4, math.ceil(total_images / 4)
            
            # Resimleri yükle ve boyutları hesapla
            images = []
            max_width = max_height = 0
            
            for view_name, file_path in valid_renders[:cols * rows]:
                try:
                    img = Image.open(file_path)
                    images.append((view_name, img))
                    max_width = max(max_width, img.width)
                    max_height = max(max_height, img.height)
                except Exception as e:
                    print(f"[WARN] Resim yüklenemedi {file_path}: {e}")
                    continue
            
            if not images:
                return {"success": False, "message": "Hiç resim yüklenemedi"}
            
            # Standart boyut belirle (en büyük boyutların %80'i)
            target_width = int(max_width * 0.8)
            target_height = int(max_height * 0.8)
            
            # Canvas boyutunu hesapla
            title_space = 60 if include_title else 0
            label_space = self.label_height if include_labels else 0
            
            canvas_width = cols * target_width + (cols + 1) * self.margin
            canvas_height = (rows * (target_height + label_space) + 
                           (rows + 1) * self.margin + title_space)
            
            # Canvas oluştur
            canvas = Image.new("RGB", (canvas_width, canvas_height), background_color)
            draw = ImageDraw.Draw(canvas)
            
            # Font yükle
            try:
                title_font = ImageFont.truetype("arial.ttf", self.title_font_size)
                label_font = ImageFont.truetype("arial.ttf", self.default_font_size)
            except:
                title_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
            
            # Başlık ekle
            if include_title:
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (canvas_width - title_width) // 2
                draw.text((title_x, 10), title, fill="black", font=title_font)
            
            # Resimleri yerleştir
            for idx, (view_name, img) in enumerate(images):
                row = idx // cols
                col = idx % cols
                
                # Resmi yeniden boyutlandır
                img_resized = img.resize((target_width, target_height), Image.LANCZOS)
                
                # Pozisyonu hesapla
                x = col * (target_width + self.margin) + self.margin
                y = (row * (target_height + label_space + self.margin) + 
                     self.margin + title_space)
                
                # Resmi yapıştır
                canvas.paste(img_resized, (x, y))
                
                # Etiket ekle
                if include_labels:
                    label_y = y + target_height + 5
                    label_text = self._format_view_name(view_name)
                    
                    # Etiket arka planı
                    label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
                    label_width = label_bbox[2] - label_bbox[0]
                    label_x = x + (target_width - label_width) // 2
                    
                    draw.rectangle(
                        [label_x - 5, label_y - 2, 
                         label_x + label_width + 5, label_y + self.label_height - 8],
                        fill="lightgray", outline="gray"
                    )
                    draw.text((label_x, label_y), label_text, fill="black", font=label_font)
            
            # Kaydet
            canvas.save(output_path, "PNG", quality=95)
            
            return {
                "success": True,
                "output_path": output_path,
                "layout": "grid",
                "dimensions": {
                    "width": canvas_width,
                    "height": canvas_height,
                    "grid_size": f"{cols}x{rows}",
                    "images_included": len(images)
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Grid layout hatası: {str(e)}"}
    
    def _combine_horizontal_layout(
        self, 
        valid_renders: List[Tuple[str, str]], 
        output_path: str,
        background_color: str,
        include_labels: bool,
        include_title: bool,
        title: str
    ) -> Dict[str, any]:
        """Yatay layout - tüm resimler yan yana"""
        try:
            # Resimleri yükle
            images = []
            total_width = 0
            max_height = 0
            
            for view_name, file_path in valid_renders:
                try:
                    img = Image.open(file_path)
                    # Yüksekliği standartlaştır (400px)
                    target_height = 400
                    aspect_ratio = img.width / img.height
                    target_width = int(target_height * aspect_ratio)
                    
                    img_resized = img.resize((target_width, target_height), Image.LANCZOS)
                    images.append((view_name, img_resized))
                    
                    total_width += target_width
                    max_height = max(max_height, target_height)
                except Exception as e:
                    print(f"[WARN] Resim yüklenemedi {file_path}: {e}")
                    continue
            
            if not images:
                return {"success": False, "message": "Hiç resim yüklenemedi"}
            
            # Canvas boyutu
            title_space = 60 if include_title else 0
            label_space = self.label_height if include_labels else 0
            margins = self.margin * (len(images) + 1)
            
            canvas_width = total_width + margins
            canvas_height = max_height + label_space + title_space + 2 * self.margin
            
            # Canvas oluştur
            canvas = Image.new("RGB", (canvas_width, canvas_height), background_color)
            draw = ImageDraw.Draw(canvas)
            
            # Font
            try:
                title_font = ImageFont.truetype("arial.ttf", self.title_font_size)
                label_font = ImageFont.truetype("arial.ttf", self.default_font_size)
            except:
                title_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
            
            # Başlık
            if include_title:
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (canvas_width - title_width) // 2
                draw.text((title_x, 10), title, fill="black", font=title_font)
            
            # Resimleri yerleştir
            current_x = self.margin
            for view_name, img in images:
                y = title_space + self.margin
                
                # Resmi yapıştır
                canvas.paste(img, (current_x, y))
                
                # Etiket
                if include_labels:
                    label_y = y + img.height + 5
                    label_text = self._format_view_name(view_name)
                    
                    label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
                    label_width = label_bbox[2] - label_bbox[0]
                    label_x = current_x + (img.width - label_width) // 2
                    
                    draw.text((label_x, label_y), label_text, fill="black", font=label_font)
                
                current_x += img.width + self.margin
            
            canvas.save(output_path, "PNG", quality=95)
            
            return {
                "success": True,
                "output_path": output_path,
                "layout": "horizontal",
                "dimensions": {
                    "width": canvas_width,
                    "height": canvas_height,
                    "images_included": len(images)
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Horizontal layout hatası: {str(e)}"}
    
    def _combine_vertical_layout(
        self, 
        valid_renders: List[Tuple[str, str]], 
        output_path: str,
        background_color: str,
        include_labels: bool,
        include_title: bool,
        title: str
    ) -> Dict[str, any]:
        """Dikey layout - tüm resimler alt alta"""
        try:
            # Resimleri yükle
            images = []
            max_width = 0
            total_height = 0
            
            for view_name, file_path in valid_renders:
                try:
                    img = Image.open(file_path)
                    # Genişliği standartlaştır (600px)
                    target_width = 600
                    aspect_ratio = img.height / img.width
                    target_height = int(target_width * aspect_ratio)
                    
                    img_resized = img.resize((target_width, target_height), Image.LANCZOS)
                    images.append((view_name, img_resized))
                    
                    max_width = max(max_width, target_width)
                    total_height += target_height
                except Exception as e:
                    print(f"[WARN] Resim yüklenemedi {file_path}: {e}")
                    continue
            
            if not images:
                return {"success": False, "message": "Hiç resim yüklenemedi"}
            
            # Canvas boyutu
            title_space = 60 if include_title else 0
            label_space = self.label_height * len(images) if include_labels else 0
            margins = self.margin * (len(images) + 1)
            
            canvas_width = max_width + 2 * self.margin
            canvas_height = total_height + label_space + title_space + margins
            
            # Canvas oluştur
            canvas = Image.new("RGB", (canvas_width, canvas_height), background_color)
            draw = ImageDraw.Draw(canvas)
            
            # Font
            try:
                title_font = ImageFont.truetype("arial.ttf", self.title_font_size)
                label_font = ImageFont.truetype("arial.ttf", self.default_font_size)
            except:
                title_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
            
            # Başlık
            if include_title:
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (canvas_width - title_width) // 2
                draw.text((title_x, 10), title, fill="black", font=title_font)
            
            # Resimleri yerleştir
            current_y = title_space + self.margin
            for view_name, img in images:
                x = (canvas_width - img.width) // 2
                
                # Resmi yapıştır
                canvas.paste(img, (x, current_y))
                
                # Etiket
                if include_labels:
                    label_y = current_y + img.height + 5
                    label_text = self._format_view_name(view_name)
                    
                    label_bbox = draw.textbbox((0, 0), label_text, font=label_font)
                    label_width = label_bbox[2] - label_bbox[0]
                    label_x = (canvas_width - label_width) // 2
                    
                    draw.text((label_x, label_y), label_text, fill="black", font=label_font)
                    current_y += img.height + self.label_height + self.margin
                else:
                    current_y += img.height + self.margin
            
            canvas.save(output_path, "PNG", quality=95)
            
            return {
                "success": True,
                "output_path": output_path,
                "layout": "vertical",
                "dimensions": {
                    "width": canvas_width,
                    "height": canvas_height,
                    "images_included": len(images)
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Vertical layout hatası: {str(e)}"}
    
    def _combine_showcase_layout(
        self, 
        valid_renders: List[Tuple[str, str]], 
        output_path: str,
        background_color: str,
        include_labels: bool,
        include_title: bool,
        title: str
    ) -> Dict[str, any]:
        """Showcase layout - ana görünüm büyük, diğerleri küçük"""
        try:
            if not valid_renders:
                return {"success": False, "message": "Render bulunamadı"}
            
            # Ana görünüm (ilk render - genellikle isometric)
            main_view_name, main_path = valid_renders[0]
            main_img = Image.open(main_path)
            
            # Ana görünümü büyük yap
            main_size = (800, 600)
            main_img_resized = main_img.resize(main_size, Image.LANCZOS)
            
            # Diğer görünümler
            other_renders = valid_renders[1:6]  # Maksimum 5 küçük görünüm
            small_images = []
            small_size = (200, 150)
            
            for view_name, file_path in other_renders:
                try:
                    img = Image.open(file_path)
                    img_resized = img.resize(small_size, Image.LANCZOS)
                    small_images.append((view_name, img_resized))
                except Exception as e:
                    print(f"[WARN] Küçük resim yüklenemedi {file_path}: {e}")
                    continue
            
            # Canvas boyutu hesapla
            title_space = 60 if include_title else 0
            label_space = self.label_height if include_labels else 0
            
            canvas_width = main_size[0] + small_size[0] + 3 * self.margin
            canvas_height = max(
                main_size[1] + label_space,
                len(small_images) * (small_size[1] + label_space + 10)
            ) + title_space + 2 * self.margin
            
            # Canvas oluştur
            canvas = Image.new("RGB", (canvas_width, canvas_height), background_color)
            draw = ImageDraw.Draw(canvas)
            
            # Font
            try:
                title_font = ImageFont.truetype("arial.ttf", self.title_font_size)
                label_font = ImageFont.truetype("arial.ttf", self.default_font_size)
            except:
                title_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
            
            # Başlık
            if include_title:
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = (canvas_width - title_width) // 2
                draw.text((title_x, 10), title, fill="black", font=title_font)
            
            # Ana görünümü yerleştir
            main_x = self.margin
            main_y = title_space + self.margin
            canvas.paste(main_img_resized, (main_x, main_y))
            
            # Ana görünüm etiketi
            if include_labels:
                main_label_y = main_y + main_size[1] + 5
                main_label_text = f"MAIN: {self._format_view_name(main_view_name)}"
                
                label_bbox = draw.textbbox((0, 0), main_label_text, font=label_font)
                label_width = label_bbox[2] - label_bbox[0]
                label_x = main_x + (main_size[0] - label_width) // 2
                
                draw.rectangle(
                    [label_x - 5, main_label_y - 2, 
                     label_x + label_width + 5, main_label_y + 30],
                    fill="darkblue", outline="navy"
                )
                draw.text((label_x, main_label_y), main_label_text, fill="white", font=label_font)
            
            # Küçük görünümleri yerleştir
            small_start_x = main_x + main_size[0] + self.margin
            current_small_y = main_y
            
            for view_name, small_img in small_images:
                canvas.paste(small_img, (small_start_x, current_small_y))
                
                # Küçük görünüm etiketi
                if include_labels:
                    small_label_y = current_small_y + small_size[1] + 2
                    small_label_text = self._format_view_name(view_name)
                    
                    label_bbox = draw.textbbox((0, 0), small_label_text, font=label_font)
                    label_width = label_bbox[2] - label_bbox[0]
                    label_x = small_start_x + (small_size[0] - label_width) // 2
                    
                    draw.text((label_x, small_label_y), small_label_text, fill="darkgreen", font=label_font)
                
                current_small_y += small_size[1] + label_space + 10
            
            canvas.save(output_path, "PNG", quality=95)
            
            return {
                "success": True,
                "output_path": output_path,
                "layout": "showcase",
                "dimensions": {
                    "width": canvas_width,
                    "height": canvas_height,
                    "main_view": main_view_name,
                    "small_views": [name for name, _ in small_images],
                    "images_included": 1 + len(small_images)
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Showcase layout hatası: {str(e)}"}
    
    def _format_view_name(self, view_name: str) -> str:
        """Görünüm ismini formatla"""
        name_map = {
            "isometric": "Isometric",
            "front": "Front View",
            "back": "Back View", 
            "left": "Left View",
            "right": "Right View",
            "top": "Top View",
            "bottom": "Bottom View",
            "wireframe": "Wireframe",
            "technical": "Technical",
            "material": "Material"
        }
        return name_map.get(view_name, view_name.title())
    
    def create_excel_friendly_version(self, input_path: str, output_path: str, max_size: int = 800) -> bool:
        """Excel için optimize edilmiş versiyon oluştur"""
        try:
            img = Image.open(input_path)
            
            # Boyutu küçült
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.LANCZOS)
            
            # Kaliteyi optimize et
            img.save(output_path, "PNG", optimize=True)
            return True
            
        except Exception as e:
            print(f"[WARN] Excel versiyonu oluşturulamadı: {e}")
            return False