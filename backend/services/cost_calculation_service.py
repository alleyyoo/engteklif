from typing import List, Dict, Any, Optional
from models.material import Material
from models.geometric_measurement import GeometricMeasurement
import logging

logger = logging.getLogger(__name__)

class CostCalculationService:
    
    @staticmethod
    def calculate_mass_kg(volume_mm3: float, density_g_cm3: float) -> float:
        """
        Hacim (mm³) ve özkütle (g/cm³) bilgisine göre kütleyi (kg) hesaplar.
        
        Args:
            volume_mm3: Hacim (mm³)
            density_g_cm3: Özkütle (g/cm³)
            
        Returns:
            float: Kütle (kg)
        """
        if volume_mm3 <= 0 or density_g_cm3 <= 0:
            raise ValueError("Hacim ve özkütle pozitif değerler olmalı")
        
        return (volume_mm3 * density_g_cm3) / 1_000_000

    @staticmethod
    def calculate_weight_newton(volume_mm3: float, density_g_cm3: float, gravity: float = 9.80665) -> float:
        """
        Hacim (mm³), özkütle (g/cm³) ve yerçekimi ivmesine göre ağırlığı (Newton) hesaplar.
        
        Args:
            volume_mm3: Hacim (mm³)
            density_g_cm3: Özkütle (g/cm³)
            gravity: Yerçekimi ivmesi (m/s²)
            
        Returns:
            float: Ağırlık (Newton)
        """
        mass_kg = CostCalculationService.calculate_mass_kg(volume_mm3, density_g_cm3)
        return mass_kg * gravity

    @staticmethod
    def calculate_material_cost(weight_kg: float, price_per_kg: float) -> float:
        """
        Ağırlık ve kg fiyatına göre hammadde maliyetini hesaplar.
        
        Args:
            weight_kg: Ağırlık (kg)
            price_per_kg: Kg başına fiyat (USD)
            
        Returns:
            float: Hammadde maliyeti (USD)
        """
        if weight_kg < 0 or price_per_kg < 0:
            raise ValueError("Ağırlık ve fiyat negatif olamaz")
        
        return weight_kg * price_per_kg

    @staticmethod
    def calculate_total_duration(main_duration_min: float, tolerance_entries: List[Dict[str, Any]]) -> float:
        """
        Tüm tolerans çarpanlarını birbiriyle çarp, süreyi hesapla.
        
        Args:
            main_duration_min: Ana işleme süresi (dakika)
            tolerance_entries: Tolerans listesi [{'name': 'Parallelik', 'value': 0.02, 'multiplier': 1.2}, ...]
            
        Returns:
            float: Toplam süre (dakika)
        """
        if main_duration_min <= 0:
            raise ValueError("Ana süre pozitif olmalı")
        
        total_multiplier = 1.0
        for tol in tolerance_entries:
            multiplier = tol.get('multiplier', 1.0)
            if multiplier <= 0:
                logger.warning(f"Geçersiz çarpan: {multiplier}, 1.0 kullanılıyor")
                multiplier = 1.0
            total_multiplier *= multiplier
        
        return main_duration_min * total_multiplier

    @staticmethod
    def calculate_machine_cost(duration_min: float, price_per_hour: float) -> float:
        """
        Dakika cinsinden süre ve saatlik fiyata göre işleme maliyetini hesaplar.
        
        Args:
            duration_min: İşleme süresi (dakika)
            price_per_hour: Saatlik işleme ücreti (USD)
            
        Returns:
            float: İşleme maliyeti (USD)
        """
        if duration_min < 0 or price_per_hour < 0:
            raise ValueError("Süre ve fiyat negatif olamaz")
        
        return (duration_min / 60.0) * price_per_hour

    @staticmethod
    def calculate_total_cost(material_cost: float, machine_cost: float, additional_costs: Optional[List[float]] = None) -> float:
        """
        Toplam maliyeti döndürür.
        
        Args:
            material_cost: Hammadde maliyeti (USD)
            machine_cost: İşleme maliyeti (USD)
            additional_costs: Ek maliyetler listesi (USD)
            
        Returns:
            float: Toplam maliyet (USD)
        """
        if material_cost < 0 or machine_cost < 0:
            raise ValueError("Maliyetler negatif olamaz")
        
        total = material_cost + machine_cost
        
        if additional_costs:
            for cost in additional_costs:
                if cost >= 0:
                    total += cost
                else:
                    logger.warning(f"Negatif ek maliyet göz ardı edildi: {cost}")
        
        return total

    @staticmethod
    def calculate_comprehensive_cost(
        volume_mm3: float,
        material_name: str,
        main_duration_min: float,
        tolerance_requirements: List[Dict[str, Any]],
        machine_hourly_rate: float,
        additional_costs: Optional[List[float]] = None,
        profit_margin: float = 0.0
    ) -> Dict[str, Any]:
        """
        Kapsamlı maliyet hesaplama
        
        Args:
            volume_mm3: Hacim (mm³)
            material_name: Malzeme adı
            main_duration_min: Ana işleme süresi (dakika)
            tolerance_requirements: Tolerans gereksinimleri
            machine_hourly_rate: Makine saatlik ücreti (USD)
            additional_costs: Ek maliyetler
            profit_margin: Kar marjı (0.2 = %20)
            
        Returns:
            Dict: Detaylı maliyet raporu
        """
        try:
            # Malzeme bilgilerini getir
            material = Material.find_by_name(material_name)
            if not material:
                return {
                    "success": False,
                    "message": f"Malzeme bulunamadı: {material_name}"
                }
            
            density = material.get('density')
            price_per_kg = material.get('price_per_kg')
            
            if not density:
                return {
                    "success": False,
                    "message": f"Malzeme yoğunluğu tanımlanmamış: {material_name}"
                }
            
            if not price_per_kg:
                return {
                    "success": False,
                    "message": f"Malzeme fiyatı tanımlanmamış: {material_name}"
                }
            
            # Tolerans çarpanlarını hesapla
            tolerance_entries = []
            for req in tolerance_requirements:
                tolerance_type = req.get('type')
                tolerance_value = req.get('value')
                
                if tolerance_type and tolerance_value is not None:
                    # MongoDB'den uygun tolerans çarpanını bul
                    matching_result = GeometricMeasurement.find_matching_measurement(tolerance_type, float(tolerance_value))
                    multiplier = matching_result.get('multiplier', 1.0) if matching_result else 1.0
                    
                    tolerance_entries.append({
                        'name': tolerance_type,
                        'value': tolerance_value,
                        'multiplier': multiplier
                    })
            
            # Hesaplamalar
            mass_kg = CostCalculationService.calculate_mass_kg(volume_mm3, density)
            material_cost = CostCalculationService.calculate_material_cost(mass_kg, price_per_kg)
            total_duration = CostCalculationService.calculate_total_duration(main_duration_min, tolerance_entries)
            machine_cost = CostCalculationService.calculate_machine_cost(total_duration, machine_hourly_rate)
            
            # Alt toplam
            subtotal = CostCalculationService.calculate_total_cost(material_cost, machine_cost, additional_costs)
            
            # Kar marjı
            profit_amount = subtotal * profit_margin
            final_total = subtotal + profit_amount
            
            return {
                "success": True,
                "material_info": {
                    "name": material_name,
                    "density": density,
                    "price_per_kg": price_per_kg
                },
                "calculations": {
                    "volume_mm3": volume_mm3,
                    "mass_kg": round(mass_kg, 4),
                    "material_cost": round(material_cost, 2),
                    "main_duration_min": main_duration_min,
                    "total_duration_min": round(total_duration, 2),
                    "machine_cost": round(machine_cost, 2),
                    "additional_costs": sum(additional_costs) if additional_costs else 0,
                    "subtotal": round(subtotal, 2),
                    "profit_margin_percent": round(profit_margin * 100, 1),
                    "profit_amount": round(profit_amount, 2),
                    "final_total": round(final_total, 2)
                },
                "tolerance_analysis": tolerance_entries,
                "breakdown": {
                    "material_percentage": round((material_cost / subtotal) * 100, 1) if subtotal > 0 else 0,
                    "machine_percentage": round((machine_cost / subtotal) * 100, 1) if subtotal > 0 else 0,
                    "additional_percentage": round((sum(additional_costs or []) / subtotal) * 100, 1) if subtotal > 0 else 0
                }
            }
            
        except ValueError as e:
            return {
                "success": False,
                "message": f"Hesaplama hatası: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Maliyet hesaplama hatası: {str(e)}")
            return {
                "success": False,
                "message": f"Beklenmeyen hata: {str(e)}"
            }

    @staticmethod
    def calculate_batch_costs(
        parts_data: List[Dict[str, Any]],
        global_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Çoklu parça maliyet hesaplama
        
        Args:
            parts_data: Parça verileri listesi
            global_settings: Genel ayarlar (kar marjı, ek maliyetler vs.)
            
        Returns:
            Dict: Toplu maliyet raporu
        """
        try:
            results = []
            total_cost = 0
            total_material_cost = 0
            total_machine_cost = 0
            
            profit_margin = global_settings.get('profit_margin', 0.0)
            machine_hourly_rate = global_settings.get('machine_hourly_rate', 0.0)
            additional_costs = global_settings.get('additional_costs', [])
            
            for part_data in parts_data:
                result = CostCalculationService.calculate_comprehensive_cost(
                    volume_mm3=part_data['volume_mm3'],
                    material_name=part_data['material_name'],
                    main_duration_min=part_data['main_duration_min'],
                    tolerance_requirements=part_data.get('tolerance_requirements', []),
                    machine_hourly_rate=machine_hourly_rate,
                    additional_costs=additional_costs,
                    profit_margin=profit_margin
                )
                
                if result['success']:
                    calc = result['calculations']
                    total_cost += calc['final_total']
                    total_material_cost += calc['material_cost']
                    total_machine_cost += calc['machine_cost']
                
                results.append({
                    "part_name": part_data.get('name', f"Part {len(results) + 1}"),
                    "result": result
                })
            
            return {
                "success": True,
                "individual_results": results,
                "summary": {
                    "total_parts": len(parts_data),
                    "successful_calculations": len([r for r in results if r['result']['success']]),
                    "total_cost": round(total_cost, 2),
                    "total_material_cost": round(total_material_cost, 2),
                    "total_machine_cost": round(total_machine_cost, 2),
                    "average_cost_per_part": round(total_cost / len(parts_data), 2) if parts_data else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Toplu maliyet hesaplama hatası: {str(e)}")
            return {
                "success": False,
                "message": f"Toplu hesaplama hatası: {str(e)}"
            }

    @staticmethod
    def estimate_machining_time(
        material_type: str,
        volume_to_remove_mm3: float,
        surface_area_mm2: float,
        complexity_factor: float = 1.0
    ) -> Dict[str, Any]:
        """
        İşleme süresi tahmini
        
        Args:
            material_type: Malzeme türü
            volume_to_remove_mm3: Çıkarılacak hacim (mm³)
            surface_area_mm2: Yüzey alanı (mm²)
            complexity_factor: Karmaşıklık faktörü (1.0 = normal)
            
        Returns:
            Dict: Tahmini işleme süreleri
        """
        try:
            # Malzeme türüne göre işleme parametreleri
            material_params = {
                "aluminum": {"roughing_mrr": 15000, "finishing_rate": 500},  # mm³/min ve mm²/min
                "steel": {"roughing_mrr": 8000, "finishing_rate": 300},
                "stainless": {"roughing_mrr": 6000, "finishing_rate": 250},
                "titanium": {"roughing_mrr": 3000, "finishing_rate": 150},
                "default": {"roughing_mrr": 10000, "finishing_rate": 400}
            }
            
            # Malzeme parametrelerini al
            params = material_params.get(material_type.lower(), material_params["default"])
            
            # Kaba işleme süresi
            roughing_time = (volume_to_remove_mm3 / params["roughing_mrr"]) * complexity_factor
            
            # Finishing süresi
            finishing_time = (surface_area_mm2 / params["finishing_rate"]) * complexity_factor
            
            # Setup ve diğer süreler
            setup_time = 15  # dakika
            tool_change_time = 5  # dakika
            
            total_time = roughing_time + finishing_time + setup_time + tool_change_time
            
            return {
                "success": True,
                "material_type": material_type,
                "time_breakdown": {
                    "roughing_time_min": round(roughing_time, 2),
                    "finishing_time_min": round(finishing_time, 2),
                    "setup_time_min": setup_time,
                    "tool_change_time_min": tool_change_time,
                    "total_time_min": round(total_time, 2),
                    "total_time_hours": round(total_time / 60, 2)
                },
                "parameters_used": {
                    "roughing_mrr": params["roughing_mrr"],
                    "finishing_rate": params["finishing_rate"],
                    "complexity_factor": complexity_factor
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"İşleme süresi tahmini hatası: {str(e)}"
            }