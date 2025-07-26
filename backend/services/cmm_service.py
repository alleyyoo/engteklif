# backend/services/cmm_service.py
"""
CMM (Coordinate Measuring Machine) veri işleme servisi
RTF dosyalarından ölçüm verilerini parse eder ve Excel raporları oluşturur
"""

import os
import re
import json
import tempfile
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import traceback

try:
    from striprtf.striprtf import rtf_to_text
    STRIPRTF_AVAILABLE = True
except ImportError:
    STRIPRTF_AVAILABLE = False
    print("⚠️ striprtf paketi yüklü değil. RTF desteği sınırlı olacak.")

@dataclass
class CMMOlcum:
    """CMM ölçüm verisi için data class"""
    operasyon: str
    sira_no: str  # String olarak sakla (10-18 formatı için)
    boyut_adi: str
    aciklama: str
    eksen: str
    nominal: float
    olculen: Any  # String veya float (min/max formatı için)
    pos_tolerans: Optional[float]
    neg_tolerans: Optional[float]
    sapma: float
    tolerans_disi: float
    bonus: Optional[float] = None
    durum: str = "✓"
    exclude_from_fai: bool = False  # FAI formunda gösterilmeyecek satırlar için

class CMMService:
    """CMM veri işleme servisi"""
    
    def __init__(self):
        self.parser = CMMParser()
        self.exporter = CMMExcelExporter()
    
    def process_files(self, file_paths: List[str], output_excel_path: str = None) -> Dict[str, Any]:
        """
        CMM dosyalarını işle ve Excel raporu oluştur
        
        Args:
            file_paths: İşlenecek RTF dosya yolları
            output_excel_path: Çıktı Excel dosya yolu (opsiyonel)
            
        Returns:
            İşlem sonucu dictionary
        """
        try:
            # Dosyaları parse et
            print(f"📄 CMM dosyaları işleniyor: {len(file_paths)} dosya")
            measurements = self.parser.parse_multiple_files(file_paths)
            
            if not measurements:
                return {
                    'success': False,
                    'error': 'Hiçbir ölçüm verisi bulunamadı',
                    'count': 0
                }
            
            # JSON'a dönüştür ve temizle
            cleaned_data = self._clean_and_prepare_data(measurements)
            
            # Operations listesini al
            operations = list(set(item['operasyon'] for item in cleaned_data))
            
            # Excel path oluştur
            if not output_excel_path:
                output_excel_path = self._generate_excel_filename(file_paths, operations)
            
            # Excel oluştur
            success = self.exporter.export_cleaned_data_to_excel(cleaned_data, output_excel_path)
            
            if success:
                return {
                    'success': True,
                    'count': len(cleaned_data),
                    'operations': operations,
                    'excel_path': output_excel_path,
                    'filename': os.path.basename(output_excel_path),
                    'summary': self._generate_summary(cleaned_data)
                }
            else:
                return {
                    'success': False,
                    'error': 'Excel dosyası oluşturulamadı',
                    'count': len(cleaned_data)
                }
                
        except Exception as e:
            print(f"❌ CMM işleme hatası: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    def _clean_and_prepare_data(self, measurements: List[CMMOlcum]) -> List[Dict]:
        """Ölçümleri temizle ve dictionary listesine dönüştür"""
        measurements_data = []
        
        for m in measurements:
            measurements_data.append({
                'operasyon': m.operasyon,
                'sira_no': m.sira_no,
                'boyut_adi': m.boyut_adi,
                'aciklama': m.aciklama,
                'eksen': m.eksen,
                'nominal': m.nominal,
                'olculen': m.olculen,
                'pos_tolerans': m.pos_tolerans,
                'neg_tolerans': m.neg_tolerans,
                'sapma': m.sapma,
                'tolerans_disi': m.tolerans_disi,
                'bonus': m.bonus,
                'durum': m.durum,
                'exclude_from_fai': m.exclude_from_fai
            })
        
        # Duplikatları kaldır
        seen = set()
        cleaned = []
        
        for item in measurements_data:
            key = (
                item['operasyon'],
                item['sira_no'], 
                item['boyut_adi'],
                item['aciklama'],
                item['eksen'],
                item['nominal'],
                str(item['olculen'])
            )
            
            if key not in seen:
                seen.add(key)
                cleaned.append(item)
        
        # Sırala
        def get_sort_key(item):
            sira_no_str = str(item['sira_no'])
            if '-' in sira_no_str:
                return int(sira_no_str.split('-')[0])
            else:
                return int(sira_no_str)
        
        cleaned.sort(key=get_sort_key)
        
        print(f"✅ Veri temizlendi: {len(measurements_data)} → {len(cleaned)} kayıt")
        
        return cleaned
    
    def _generate_excel_filename(self, file_paths: List[str], operations: List[str]) -> str:
        """Excel dosya adı oluştur"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_count = len(file_paths)
        ops_str = "_".join(sorted(operations)) if operations else "mixed"
        return f"cmm_raporu_{file_count}dosya_{ops_str}_{timestamp}.xlsx"
    
    def _generate_summary(self, cleaned_data: List[Dict]) -> Dict[str, Any]:
        """Özet bilgileri oluştur"""
        # Operasyon bazlı istatistikler
        op_stats = {}
        for item in cleaned_data:
            op = item['operasyon']
            if op not in op_stats:
                op_stats[op] = 0
            op_stats[op] += 1
        
        # Durum istatistikleri
        successful = sum(1 for item in cleaned_data if item['durum'] == '✓')
        warnings = sum(1 for item in cleaned_data if item['durum'] == '⚠')
        
        # Benzersiz ölçüm numaraları
        unique_measurements = len(set(item['sira_no'] for item in cleaned_data))
        
        # FAI hariç tutulan sayısı
        fai_excluded = sum(1 for item in cleaned_data if item.get('exclude_from_fai', False))
        
        return {
            'total_measurements': len(cleaned_data),
            'successful_measurements': successful,
            'warning_measurements': warnings,
            'operation_breakdown': op_stats,
            'unique_measurement_numbers': unique_measurements,
            'fai_excluded_count': fai_excluded,
            'success_rate': round((successful / len(cleaned_data)) * 100, 2) if cleaned_data else 0
        }

class CMMParser:
    """CMM RTF dosyalarını parse eden sınıf"""
    
    def __init__(self):
        self.pattern_line = re.compile(
            r'\*+\s*(\d+)\s*\*+'  # Sıra numarası
        )
        self.pattern_dim = re.compile(
            r'DIM\s+(\w+)=\s*(.+?)\s+UNITS=MM'  # Boyut tanımı
        )
        self.pattern_data = re.compile(
            r'(\w+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)'
        )
    
    def extract_rtf_text(self, file_path: str) -> str:
        """RTF dosyasından metin çıkarır"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if STRIPRTF_AVAILABLE:
                return rtf_to_text(content)
            else:
                # Basit RTF temizleme
                content = re.sub(r'\\[a-z]+\d*', '', content)
                content = re.sub(r'[{}]', '', content)
                return content
        except Exception as e:
            print(f"RTF okuma hatası: {e}")
            return ""
    
    def parse_file(self, file_path: str) -> List[CMMOlcum]:
        """Tek bir CMM dosyasını parse eder"""
        measurements = []
        
        # Dosya adından operasyon belirle
        filename = Path(file_path).stem
        operasyon = self._detect_operation(filename)
        
        print(f"📂 İşlenen dosya: {filename}, Operasyon: {operasyon}")
        
        # RTF text'i çıkar
        text = self.extract_rtf_text(file_path)
        if not text:
            return measurements
        
        # Sıra numaralarını bul
        sira_matches = self._find_measurement_numbers(text)
        
        print(f"🔍 Bulunan ölçüm sayısı: {len(sira_matches)}")
        
        # Her sıra numarası için bloğu işle
        for i, match in enumerate(sira_matches):
            sira_no_str = self._process_measurement_number(match.group(1).strip())
            
            # Blok sınırlarını belirle
            start_pos = match.end()
            end_pos = sira_matches[i + 1].start() if i + 1 < len(sira_matches) else len(text)
            
            # Blok metnini çıkar ve işle
            block_text = text[start_pos:end_pos].strip()
            if block_text:
                block_measurements = self.parse_measurement_block(block_text, operasyon, sira_no_str)
                measurements.extend(block_measurements)
        
        print(f"✅ Toplam ölçüm sayısı: {len(measurements)}")
        return measurements
    
    def _detect_operation(self, filename: str) -> str:
        """Dosya adından operasyon tespit et"""
        filename_upper = filename.upper()
        
        if '1OP' in filename_upper:
            return '1OP'
        elif '2OP' in filename_upper:
            return '2OP'
        elif '3OP' in filename_upper:
            return '3OP'
        else:
            return '1OP'  # Varsayılan
    
    def _find_measurement_numbers(self, text: str) -> List[re.Match]:
        """Metinde ölçüm numaralarını bul"""
        # Üç farklı pattern dene
        patterns = [
            r'\*+\s+([0-9]+(?:-[A-Za-z0-9\s]+)?)\s+\*+',  # Boşluklu
            r'\*+([0-9]+(?:-[A-Za-z0-9\s]+)?)\*+',        # Boşluksuz
            r'\*+\s*([0-9]+)\s*\*+'                        # Esnek
        ]
        
        all_matches = []
        seen_positions = set()
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.start() not in seen_positions:
                    all_matches.append(match)
                    seen_positions.add(match.start())
        
        # Pozisyona göre sırala
        return sorted(all_matches, key=lambda x: x.start())
    
    def _process_measurement_number(self, sira_no_raw: str) -> str:
        """Sıra numarasını işle"""
        if '-' in sira_no_raw:
            parts = sira_no_raw.split('-', 1)
            first_part = parts[0].strip()
            second_part = parts[1].strip()
            
            try:
                int(second_part)
                # Aralık formatı (10-18)
                return sira_no_raw.replace(' ', '')
            except ValueError:
                # Metin etiketi (16-WEB SURFACE)
                return first_part
        else:
            return sira_no_raw
    
    def parse_measurement_block(self, block: str, operasyon: str, sira_no_str: str) -> List[CMMOlcum]:
        """Ölçüm bloğunu parse et"""
        measurements = []
        lines = block.split('\n')
        
        current_dim = None
        current_desc = None
        surface_profiles = []
        has_surface = False
        position_measurements = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # DIM tanımını yakala
            dim_match = re.search(r'DIM\s+(\w+)=\s*(.+?)\s+UNITS=MM', line)
            if dim_match:
                current_dim = dim_match.group(1)
                current_desc = dim_match.group(2).strip()
                
                # SURFACE veya POSITION kontrolü
                if 'SURFACE' in current_desc.upper() or 'PROFILE' in current_desc.upper():
                    has_surface = True
                
                if 'POSITION' in current_desc.upper() and position_measurements:
                    self._process_position_group(position_measurements, measurements)
                    position_measurements = []
                
                continue
            
            # Veri satırlarını işle
            if re.match(r'^[DRMTPZYXAF]+\s+', line):
                measurement = self._parse_data_line(line, operasyon, sira_no_str, current_dim, current_desc)
                if measurement:
                    if current_desc and 'POSITION' in current_desc.upper():
                        position_measurements.append(measurement)
                    elif current_desc and ('SURFACE' in current_desc.upper() or 'PROFILE' in current_desc.upper()):
                        surface_profiles.append(measurement)
                    else:
                        measurements.append(measurement)
        
        # Son position grubunu işle
        if position_measurements:
            self._process_position_group(position_measurements, measurements)
        
        # SURFACE profilleri birleştir
        if surface_profiles and has_surface:
            m_surface_profiles = [p for p in surface_profiles if p.eksen == 'M']
            other_profiles = [p for p in surface_profiles if p.eksen != 'M']
            
            if m_surface_profiles:
                combined = self._combine_surface_profiles(m_surface_profiles, sira_no_str, operasyon)
                if combined:
                    measurements.append(combined)
            
            measurements.extend(other_profiles)
        elif surface_profiles:
            measurements.extend(surface_profiles)
        
        return measurements
    
    def _process_position_group(self, position_measurements: List[CMMOlcum], measurements: List[CMMOlcum]):
        """POSITION ölçüm grubunu işle"""
        for m in position_measurements:
            if m.eksen in ['X', 'Y', 'Z']:
                m.exclude_from_fai = True
            measurements.append(m)
    
    def _combine_surface_profiles(self, profiles: List[CMMOlcum], sira_no_str: str, operasyon: str) -> Optional[CMMOlcum]:
        """SURFACE profil ölçümlerini birleştir"""
        if not profiles:
            return None
        
        measured_values = [float(p.olculen) for p in profiles]
        min_val = min(measured_values)
        max_val = max(measured_values)
        
        if abs(min_val - max_val) < 0.001:
            combined_result = str(min_val).rstrip('0').rstrip('.')
        else:
            min_str = str(min_val).rstrip('0').rstrip('.')
            max_str = str(max_val).rstrip('0').rstrip('.')
            combined_result = f"{min_str} / {max_str}"
        
        base_profile = profiles[0]
        
        return CMMOlcum(
            operasyon=operasyon,
            sira_no=sira_no_str,
            boyut_adi="PROF_SURFACE",
            aciklama="PROFILE OF SURFACE (Combined)",
            eksen="M",
            nominal=base_profile.nominal,
            olculen=combined_result,
            pos_tolerans=base_profile.pos_tolerans,
            neg_tolerans=base_profile.neg_tolerans,
            sapma=base_profile.sapma,
            tolerans_disi=base_profile.tolerans_disi,
            bonus=base_profile.bonus,
            durum=base_profile.durum
        )
    
    def _parse_data_line(self, line: str, operasyon: str, sira_no_str: str, dim_name: str, description: str) -> Optional[CMMOlcum]:
        """Veri satırını parse et"""
        parts = line.split()
        if len(parts) < 3:
            return None
        
        try:
            eksen = parts[0]
            
            # Nominal değer
            nominal_str = parts[1]
            if nominal_str in ["RFS", "MMC", "LMC"]:
                nominal = 0.0
            else:
                nominal = float(nominal_str)
            
            # Ölçülen değer
            olculen = float(parts[2])
            
            # Toleranslar ve diğer değerler
            pos_tol = None
            neg_tol = None
            bonus = None
            sapma = 0.0
            tolerans_disi = 0.0
            
            # TP satırı için özel parsing
            if eksen == "TP":
                if len(parts) >= 6:
                    pos_tol = float(parts[3]) if parts[3] != '' else None
                    bonus = float(parts[5]) if parts[5] != '' else None
                    sapma = float(parts[6]) if parts[6] != '' else 0.0
                    tolerans_disi = float(parts[7]) if len(parts) >= 8 and parts[7] != '' else 0.0
            else:
                # Normal satırlar
                if len(parts) >= 5:
                    try:
                        pos_tol = float(parts[3]) if parts[3] != '' else None
                        neg_tol = float(parts[4]) if parts[4] != '' else None
                    except ValueError:
                        pass
                
                # Sapma ve tolerans dışı değerleri bul
                for i, part in enumerate(parts):
                    try:
                        val = float(part)
                        if i >= 5 and abs(val) < 1.0 and val != nominal and val != olculen:
                            sapma = val
                        if i >= 6 and val == 0.0:
                            tolerans_disi = val
                            break
                    except ValueError:
                        continue
            
            # Durum
            durum = "✓" if tolerans_disi == 0.0 else "⚠"
            
            # Boyut adını oluştur
            if dim_name:
                if eksen in ['TP', 'DF']:
                    boyut_adi = f"{dim_name}_{eksen}"
                    aciklama = f"{description} ({eksen})"
                else:
                    boyut_adi = dim_name
                    aciklama = description
            else:
                boyut_adi = f"DIM{sira_no_str}"
                aciklama = "Bilinmeyen ölçüm"
            
            return CMMOlcum(
                operasyon=operasyon,
                sira_no=sira_no_str,
                boyut_adi=boyut_adi,
                aciklama=aciklama,
                eksen=eksen,
                nominal=nominal,
                olculen=olculen,
                pos_tolerans=pos_tol,
                neg_tolerans=neg_tol,
                sapma=sapma,
                tolerans_disi=tolerans_disi,
                bonus=bonus,
                durum=durum
            )
        
        except (ValueError, IndexError) as e:
            print(f"⚠️ Veri satırı parse hatası: {e} - {line}")
            return None
    
    def parse_multiple_files(self, file_paths: List[str]) -> List[CMMOlcum]:
        """Birden fazla CMM dosyasını parse eder"""
        all_measurements = []
        
        for file_path in file_paths:
            try:
                measurements = self.parse_file(file_path)
                all_measurements.extend(measurements)
                print(f"✅ {os.path.basename(file_path)}: {len(measurements)} ölçüm işlendi")
            except Exception as e:
                print(f"❌ {file_path}: Hata - {e}")
                traceback.print_exc()
        
        print(f"📊 TOPLAM: {len(all_measurements)} ölçüm")
        return all_measurements

class CMMExcelExporter:
    """CMM verilerini Excel'e dönüştüren sınıf"""
    
    def export_cleaned_data_to_excel(self, cleaned_data: List[Dict], output_path: str) -> bool:
        """Temizlenmiş veriyi Excel'e dönüştür"""
        import numpy as np
        
        try:
            # DataFrame oluştur
            df = pd.DataFrame(cleaned_data)
            
            # NaN değerleri temizle
            def clean_value(val):
                if pd.isna(val) or val is None:
                    return ''
                elif isinstance(val, float) and (not np.isfinite(val)):
                    return ''
                else:
                    return val
            
            for col in df.columns:
                df[col] = df[col].apply(clean_value)
            
            # Sütun isimlerini düzenle
            df = df.rename(columns={
                'operasyon': 'Operasyon',
                'sira_no': 'Ölçüm No',
                'boyut_adi': 'Boyut Adı',
                'aciklama': 'Açıklama',
                'eksen': 'Eksen',
                'nominal': 'Nominal',
                'olculen': 'Ölçülen',
                'pos_tolerans': '+Tolerans',
                'neg_tolerans': '-Tolerans',
                'sapma': 'Sapma',
                'tolerans_disi': 'Tolerans Dışı',
                'bonus': 'Bonus',
                'durum': 'Durum',
                'exclude_from_fai': 'FAI Hariç'
            })
            
            # Excel yazıcı oluştur
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                # Ana veri sayfası
                df.to_excel(writer, sheet_name='CMM_Verileri', index=False)
                
                # Formatları uygula
                workbook = writer.book
                worksheet = writer.sheets['CMM_Verileri']
                
                # Header formatı
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # TP satır formatı
                tp_format = workbook.add_format({
                    'bg_color': '#E1D5E7',
                    'font_color': '#5B2C6F'
                })
                
                # Sütun genişlikleri
                worksheet.set_column('A:A', 12)  # Operasyon
                worksheet.set_column('B:B', 10)  # Ölçüm No
                worksheet.set_column('C:C', 15)  # Boyut Adı
                worksheet.set_column('D:D', 35)  # Açıklama
                worksheet.set_column('E:E', 8)   # Eksen
                worksheet.set_column('F:N', 12)  # Sayısal değerler
                
                # Header formatını uygula
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # TP satırlarını renklendir
                for row_num in range(1, len(df) + 1):
                    eksen = df.iloc[row_num-1]['Eksen']
                    if eksen == 'TP':
                        for col_num in range(len(df.columns)):
                            cell_value = df.iloc[row_num-1, col_num]
                            try:
                                worksheet.write(row_num, col_num, cell_value, tp_format)
                            except:
                                worksheet.write(row_num, col_num, '', tp_format)
                
                # Özet sayfa ekle
                self._add_summary_sheet(writer, df, workbook)
                
                # FAI Form 3 sayfası ekle
                self._add_fai_form3_sheet(writer, df, workbook)
            
            print(f"💾 Excel dosyası oluşturuldu: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Excel export hatası: {e}")
            traceback.print_exc()
            return False
    
    def _add_summary_sheet(self, writer, df: pd.DataFrame, workbook):
        """Özet sayfası ekle"""
        summary_data = {
            'Metrik': [
                'Toplam Ölçüm',
                'Başarılı Ölçüm',
                'Uyarı Gerekli',
                'Operasyon 1OP',
                'Operasyon 2OP',
                'Farklı Ölçüm Numarası',
                'FAI Hariç Tutulan'
            ],
            'Değer': [
                len(df),
                len(df[df['Durum'] == '✓']),
                len(df[df['Durum'] == '⚠']),
                len(df[df['Operasyon'] == '1OP']),
                len(df[df['Operasyon'] == '2OP']),
                len(df['Ölçüm No'].unique()),
                len(df[df['FAI Hariç'] == True])
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Özet', index=False)
        
        summary_ws = writer.sheets['Özet']
        summary_ws.set_column('A:A', 20)
        summary_ws.set_column('B:B', 15)
    
    def _add_fai_form3_sheet(self, writer, df: pd.DataFrame, workbook):
        """FAI Form 3 sayfası ekle"""
        # FAI'dan hariç tutulan satırları filtrele
        df_fai = df[df['FAI Hariç'] != True].copy()
        
        # Yeni sayfa oluştur
        fai_ws = workbook.add_worksheet('FAI_Form3')
        
        # Format tanımları
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        doc_format = workbook.add_format({
            'font_size': 10,
            'align': 'right',
            'valign': 'vcenter',
            'text_wrap': True
        })
        
        section_header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'fg_color': '#E7E6E6',
            'border': 1
        })
        
        part_header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })
        
        part_data_format = workbook.add_format({
            'font_size': 10,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        
        column_header_format = workbook.add_format({
            'bold': True,
            'font_size': 9,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'fg_color': '#D9E1F2',
            'border': 1
        })
        
        data_format = workbook.add_format({
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Sütun genişlikleri
        fai_ws.set_column('A:A', 6)   # Krk No
        fai_ws.set_column('B:B', 10)  # Ek Bilgi
        fai_ws.set_column('C:C', 12)  # Ref Bölge
        fai_ws.set_column('D:D', 18)  # Karakter Özelliği
        fai_ws.set_column('E:E', 12)  # Gerek/Ölçü
        fai_ws.set_column('F:F', 10)  # Requirement
        fai_ws.set_column('G:G', 15)  # Sonuç
        fai_ws.set_column('H:H', 2)   # Boş
        fai_ws.set_column('I:I', 2)   # Boş
        fai_ws.set_column('J:J', 15)  # Aletler
        fai_ws.set_column('K:K', 12)  # Uygunsuzluk
        fai_ws.set_column('L:L', 2)   # Boş
        fai_ws.set_column('M:M', 15)  # Ek Veriler
        fai_ws.set_column('N:N', 15)  # Ek Veriler devam
        
        # Başlık
        fai_ws.merge_range('D1:N1', 'İLK ÜRÜN MUAYENESİ\nFIRST ARTICLE INSPECTION (FAI)', title_format)
        fai_ws.write('N1', 'Doküman No:ENG-KT-FR-44\nİlk Yayın Tarihi: 26.06.2024\nRevizyon No: 01\nRevizyon Tarihi:06.09.2024', doc_format)
        
        # Alt başlık
        fai_ws.merge_range('A3:N3', 'Karakteristik Nitelikler, Doğrulama ve Uygunluk Değerlendirmesi Formu\nCharacteristic Accountability, Verification and Compatibility Evaluation\nSAE AS9102 Revision C', section_header_format)
        
        # Parça bilgileri başlıkları
        fai_ws.merge_range('A4:C4', '1. Parça Numarası\n     Part Number', part_header_format)
        fai_ws.merge_range('D4:J4', '2. Parça Tanımı\n     Part Name', part_header_format)
        fai_ws.merge_range('K4:L4', '3. Seri No.\n     Serial Number', part_header_format)
        fai_ws.merge_range('M4:N4', '4. FAI Rapor No.\n     FAIR Identifier', part_header_format)
        
        # Parça bilgileri verileri
        fai_ws.merge_range('A5:C5', 'MM-7570-1828', part_data_format)
        fai_ws.merge_range('D5:J5', 'KILAVUZ CL/KFY ORTA MAYON CIKIS ESB SOL', part_data_format)
        fai_ws.merge_range('K5:L5', 'FAI', part_data_format)
        fai_ws.merge_range('M5:N5', 'MM-7570-1828;241122', part_data_format)
        
        # Ana bölüm başlıkları
        fai_ws.merge_range('A6:F6', 'Karakteristik Nitelikler\nCharacteristic Accountability', section_header_format)
        fai_ws.merge_range('G6:L6', 'Muayene / Test Sonuçları\nInspection / Test Results', section_header_format)
        fai_ws.merge_range('M6:N6', '12. Ek Veriler / Yorumlar\n Additional Data / Comments', section_header_format)
        
        # Sütun başlıkları
        fai_ws.write('A7', '5. Krk. No.\n    Char No.', column_header_format)
        fai_ws.write('B7', '6. Ek Bilgi\nExtra Info', column_header_format)
        fai_ws.write('C7', '7.Dokümandaki Ref.Bölge\nReference Location', column_header_format)
        fai_ws.write('D7', '8. Karakter Özelliği\nCharacteristic Designator', column_header_format)
        fai_ws.merge_range('E7:F7', '9. Gerek/Ölçü\n     Requirement', column_header_format)
        fai_ws.merge_range('G7:I7', '10. Sonuç\n     Results', column_header_format)
        fai_ws.write('J7', '11.  Tasarlanmış / Nitelikli Aletler\nDesigned / Qualified Tooling', column_header_format)
        fai_ws.merge_range('K7:L7', '12. Uygunsuzluk Bildirim No.\nNon-Conformance Number', column_header_format)
        fai_ws.merge_range('M7:N7', '13. Ek Veriler / Yorumlar\n Additional Data / Comments', column_header_format)
        
        # Veri satırlarını yaz
        start_row = 8
        
        # Alt numaralama hesaplamaları
        measurement_counts = {}
        for idx, row in df_fai.iterrows():
            olcum_no = row['Ölçüm No']
            if olcum_no in measurement_counts:
                measurement_counts[olcum_no] += 1
            else:
                measurement_counts[olcum_no] = 1
        
        current_counts = {}
        position_values = {}
        
        # Position değerlerini topla
        for idx, row in df_fai.iterrows():
            olcum_no = row['Ölçüm No']
            boyut_adi = row['Boyut Adı']
            eksen = row['Eksen']
            
            if 'LOC' in str(boyut_adi) and eksen in ['DF', 'TP']:
                loc_name = str(boyut_adi).split('_')[0] if '_' in str(boyut_adi) else str(boyut_adi)
                key = (olcum_no, loc_name, eksen)
                if key not in position_values:
                    position_values[key] = []
                position_values[key].append(float(row['Ölçülen']))
        
        # FAI satırlarını yaz
        fai_row_index = 0
        for idx, row in df_fai.iterrows():
            current_row = start_row + fai_row_index
            
            # Format ve değerleri hazırla
            krk_no_formatted = self._format_krk_no(row, measurement_counts, current_counts)
            ek_bilgi = self._extract_ek_bilgi(row['Boyut Adı'])
            ozellik = self._determine_karakter_ozellik(row)
            gerek_olcu = self._format_gerek_olcu(row)
            requirement = self._format_requirement(row, ozellik)
            sonuc_str = self._format_sonuc(row, position_values)
            
            # Satırı yaz
            fai_ws.write(current_row, 0, krk_no_formatted, data_format)
            fai_ws.write(current_row, 1, ek_bilgi, data_format)
            fai_ws.write(current_row, 2, 'N/A', data_format)
            fai_ws.write(current_row, 3, ozellik, data_format)
            fai_ws.write(current_row, 4, gerek_olcu, data_format)
            fai_ws.write(current_row, 5, requirement, data_format)
            fai_ws.write(current_row, 6, sonuc_str, data_format)
            fai_ws.write(current_row, 7, '', data_format)
            fai_ws.write(current_row, 8, '', data_format)
            fai_ws.write(current_row, 9, 'CMM-001', data_format)
            fai_ws.write(current_row, 10, '', data_format)
            fai_ws.write(current_row, 11, '', data_format)
            fai_ws.write(current_row, 12, '', data_format)
            fai_ws.write(current_row, 13, '', data_format)
            
            fai_row_index += 1
        
        print(f"📋 FAI Form 3 sayfası eklendi: {fai_row_index} karakteristik")
    
    def _format_krk_no(self, row, measurement_counts, current_counts):
        """Krk No formatla"""
        olcum_no = row['Ölçüm No']
        
        if olcum_no in current_counts:
            current_counts[olcum_no] += 1
        else:
            current_counts[olcum_no] = 1
        
        if measurement_counts[olcum_no] > 1:
            return f"{olcum_no}.{current_counts[olcum_no]}"
        else:
            return str(olcum_no)
    
    def _extract_ek_bilgi(self, boyut_adi):
        """Ek bilgi çıkar"""
        boyut_adi_str = str(boyut_adi)
        
        if '_' in boyut_adi_str:
            base_dim = boyut_adi_str.split('_')[0]
            if base_dim.startswith(('LOC', 'CIR', 'DIM', 'PROF', 'ANGL')):
                return base_dim
        elif boyut_adi_str.startswith(('LOC', 'CIR', 'DIM', 'PROF', 'ANGL')):
            return boyut_adi_str
        
        return ""
    
    def _determine_karakter_ozellik(self, row):
        """Karakter özelliğini belirle"""
        eksen = row['Eksen']
        aciklama = str(row['Açıklama']).upper()
        
        if 'SURFACE' in aciklama or 'PROFILE' in aciklama:
            return 'PROFİL'
        elif 'POSITION' in aciklama or eksen == 'TP':
            return 'KONUM'
        elif 'FLATNESS' in aciklama:
            return 'DÜZLEMSELLİK'
        elif 'PARALLELISM' in aciklama:
            return 'PARALELLİK'
        elif 'PERPENDICULARITY' in aciklama:
            return 'DİKLİK'
        elif 'DISTANCE' in aciklama:
            return 'MESAFE'
        elif 'ANGLE' in aciklama or eksen == 'A':
            return 'AÇI'
        elif 'LOCATION' in aciklama:
            if eksen == 'D':
                return 'ÇAP'
            elif eksen == 'R':
                return 'YARIÇAP'
            else:
                return 'KONUM'
        else:
            return str(row['Boyut Adı'])
    
    def _format_gerek_olcu(self, row):
        """Gerek/Ölçü formatla"""
        nominal = row['Nominal']
        eksen = row['Eksen']
        
        if nominal != 0 and eksen != 'TP':
            if eksen == 'R':
                return f"R{int(abs(nominal))}"
            elif eksen == 'A':
                return str(abs(nominal)).rstrip('0').rstrip('.')
            elif 'M6' in str(nominal):
                return "M6"
            else:
                return str(abs(nominal)).rstrip('0').rstrip('.')
        elif eksen == 'TP':
            return "KONUM"
        else:
            return str(abs(nominal)).rstrip('0').rstrip('.') if nominal != 0 else ""
    
    def _format_requirement(self, row, ozellik):
        """Requirement formatla"""
        pos_tol = row['+Tolerans']
        neg_tol = row['-Tolerans']
        eksen = row['Eksen']
        
        if pos_tol and neg_tol and pos_tol == neg_tol:
            if ozellik in ['KONUM', 'DÜZLEMSELLİK', 'PARALELLİK', 'DİKLİK', 'PROFİL']:
                return str(pos_tol).replace('.', ',')
            else:
                return f"±{str(pos_tol)}".replace('.', ',')
        elif pos_tol and neg_tol:
            return f"+{str(pos_tol)}/-{str(neg_tol)}".replace('.', ',')
        elif pos_tol:
            if ozellik in ['KONUM', 'DÜZLEMSELLİK', 'PARALELLİK', 'DİKLİK', 'PROFİL']:
                return str(pos_tol).replace('.', ',')
            else:
                return f"+{str(pos_tol)}".replace('.', ',')
        elif eksen == 'TP':
            return str(row['Ölçülen']).replace('.', ',')
        else:
            return ""
    
    def _format_sonuc(self, row, position_values):
        """Sonuç formatla"""
        sonuc = row['Ölçülen']
        olcum_no = row['Ölçüm No']
        boyut_adi = str(row['Boyut Adı'])
        eksen = row['Eksen']
        
        # Position ölçümleri için min/max kontrolü
        if 'LOC' in boyut_adi and eksen in ['DF', 'TP']:
            loc_name = boyut_adi.split('_')[0] if '_' in boyut_adi else boyut_adi
            key = (olcum_no, loc_name, eksen)
            if key in position_values and len(position_values[key]) > 1:
                values = position_values[key]
                min_val = min(values)
                max_val = max(values)
                if abs(min_val - max_val) < 0.001:
                    return str(min_val).replace('.', ',')
                else:
                    return f"{str(min_val).replace('.', ',')} - {str(max_val).replace('.', ',')}"
        
        if isinstance(sonuc, (int, float)):
            if 'M6' in str(row.get('Nominal', '')):
                return "OK"
            else:
                return str(sonuc).replace('.', ',')
        else:
            return str(sonuc).replace('.', ',')
