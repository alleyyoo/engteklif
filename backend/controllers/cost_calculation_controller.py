from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional
from services.cost_calculation_service import CostCalculationService
from models.user import User

cost_bp = Blueprint('cost', __name__, url_prefix='/api/cost-calculation')

def get_current_user():
    """Mevcut kullanıcıyı getir"""
    current_user_id = get_jwt_identity()
    return User.find_by_id(current_user_id)

# Pydantic modelleri
class BasicCostRequest(BaseModel):
    volume_mm3: float = Field(..., gt=0, description="Hacim (mm³)")
    material_name: str = Field(..., min_length=1, description="Malzeme adı")
    main_duration_min: float = Field(..., gt=0, description="Ana işleme süresi (dakika)")
    machine_hourly_rate: float = Field(..., ge=0, description="Makine saatlik ücreti")

class ToleranceRequirement(BaseModel):
    type: str = Field(..., min_length=1, description="Tolerans türü")
    value: float = Field(..., description="Tolerans değeri")

class ComprehensiveCostRequest(BaseModel):
    volume_mm3: float = Field(..., gt=0, description="Hacim (mm³)")
    material_name: str = Field(..., min_length=1, description="Malzeme adı")
    main_duration_min: float = Field(..., gt=0, description="Ana işleme süresi (dakika)")
    tolerance_requirements: List[ToleranceRequirement] = Field(default=[], description="Tolerans gereksinimleri")
    machine_hourly_rate: float = Field(..., ge=0, description="Makine saatlik ücreti")
    additional_costs: Optional[List[float]] = Field(default=[], description="Ek maliyetler")
    profit_margin: float = Field(default=0.0, ge=0, le=1, description="Kar marjı (0-1 arası)")

class PartData(BaseModel):
    name: str = Field(..., min_length=1, description="Parça adı")
    volume_mm3: float = Field(..., gt=0, description="Hacim (mm³)")
    material_name: str = Field(..., min_length=1, description="Malzeme adı")
    main_duration_min: float = Field(..., gt=0, description="Ana işleme süresi (dakika)")
    tolerance_requirements: List[ToleranceRequirement] = Field(default=[], description="Tolerans gereksinimleri")

class BatchCostRequest(BaseModel):
    parts_data: List[PartData] = Field(..., min_items=1, description="Parça verileri")
    machine_hourly_rate: float = Field(..., ge=0, description="Makine saatlik ücreti")
    additional_costs: Optional[List[float]] = Field(default=[], description="Ek maliyetler")
    profit_margin: float = Field(default=0.0, ge=0, le=1, description="Kar marjı")

class MachiningTimeRequest(BaseModel):
    material_type: str = Field(..., min_length=1, description="Malzeme türü")
    volume_to_remove_mm3: float = Field(..., gt=0, description="Çıkarılacak hacim (mm³)")
    surface_area_mm2: float = Field(..., gt=0, description="Yüzey alanı (mm²)")
    complexity_factor: float = Field(default=1.0, gt=0, le=5, description="Karmaşıklık faktörü")

@cost_bp.route('/basic', methods=['POST'])
@jwt_required()
def calculate_basic_cost():
    """Temel maliyet hesaplama"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        cost_request = BasicCostRequest(**data)
        
        # Basit hesaplama - sadece malzeme ve makine maliyeti
        result = CostCalculationService.calculate_comprehensive_cost(
            volume_mm3=cost_request.volume_mm3,
            material_name=cost_request.material_name,
            main_duration_min=cost_request.main_duration_min,
            tolerance_requirements=[],
            machine_hourly_rate=cost_request.machine_hourly_rate,
            additional_costs=[],
            profit_margin=0.0
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except ValidationError as e:
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/comprehensive', methods=['POST'])
@jwt_required()
def calculate_comprehensive_cost():
    """Kapsamlı maliyet hesaplama"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        cost_request = ComprehensiveCostRequest(**data)
        
        # Tolerans gereksinimlerini dönüştür
        tolerance_requirements = [
            {"type": tol.type, "value": tol.value} 
            for tol in cost_request.tolerance_requirements
        ]
        
        result = CostCalculationService.calculate_comprehensive_cost(
            volume_mm3=cost_request.volume_mm3,
            material_name=cost_request.material_name,
            main_duration_min=cost_request.main_duration_min,
            tolerance_requirements=tolerance_requirements,
            machine_hourly_rate=cost_request.machine_hourly_rate,
            additional_costs=cost_request.additional_costs,
            profit_margin=cost_request.profit_margin
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except ValidationError as e:
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/batch', methods=['POST'])
@jwt_required()
def calculate_batch_costs():
    """Toplu maliyet hesaplama"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        batch_request = BatchCostRequest(**data)
        
        # Parça verilerini dönüştür
        parts_data = []
        for part in batch_request.parts_data:
            tolerance_requirements = [
                {"type": tol.type, "value": tol.value} 
                for tol in part.tolerance_requirements
            ]
            
            parts_data.append({
                "name": part.name,
                "volume_mm3": part.volume_mm3,
                "material_name": part.material_name,
                "main_duration_min": part.main_duration_min,
                "tolerance_requirements": tolerance_requirements
            })
        
        global_settings = {
            "machine_hourly_rate": batch_request.machine_hourly_rate,
            "additional_costs": batch_request.additional_costs,
            "profit_margin": batch_request.profit_margin
        }
        
        result = CostCalculationService.calculate_batch_costs(parts_data, global_settings)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except ValidationError as e:
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/estimate-machining-time', methods=['POST'])
@jwt_required()
def estimate_machining_time():
    """İşleme süresi tahmini"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        time_request = MachiningTimeRequest(**data)
        
        result = CostCalculationService.estimate_machining_time(
            material_type=time_request.material_type,
            volume_to_remove_mm3=time_request.volume_to_remove_mm3,
            surface_area_mm2=time_request.surface_area_mm2,
            complexity_factor=time_request.complexity_factor
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except ValidationError as e:
        return jsonify({
            "success": False,
            "message": "Veri doğrulama hatası",
            "errors": [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/quick-estimate', methods=['POST'])
@jwt_required()
def quick_cost_estimate():
    """Hızlı maliyet tahmini"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        # Gerekli parametreler
        required_fields = ['volume_mm3', 'material_name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Gerekli alan eksik: {field}"
                }), 400
        
        volume_mm3 = float(data['volume_mm3'])
        material_name = data['material_name']
        
        # Varsayılan değerler
        machine_hourly_rate = data.get('machine_hourly_rate', 65.0)  # USD/saat
        complexity_factor = data.get('complexity_factor', 1.0)
        
        # İşleme süresi tahmini
        time_estimate = CostCalculationService.estimate_machining_time(
            material_type=material_name,
            volume_to_remove_mm3=volume_mm3 * 0.6,  # %60'ı çıkarılacak varsayımı
            surface_area_mm2=volume_mm3 ** (2/3) * 6,  # Yaklaşık yüzey alanı
            complexity_factor=complexity_factor
        )
        
        if not time_estimate['success']:
            return jsonify(time_estimate), 400
        
        estimated_time = time_estimate['time_breakdown']['total_time_min']
        
        # Maliyet hesaplama
        cost_result = CostCalculationService.calculate_comprehensive_cost(
            volume_mm3=volume_mm3,
            material_name=material_name,
            main_duration_min=estimated_time,
            tolerance_requirements=[],
            machine_hourly_rate=machine_hourly_rate,
            additional_costs=[],
            profit_margin=0.2  # %20 kar marjı
        )
        
        if cost_result['success']:
            # Hızlı özet
            quick_summary = {
                "success": True,
                "quick_estimate": {
                    "total_cost": cost_result['calculations']['final_total'],
                    "material_cost": cost_result['calculations']['material_cost'],
                    "machine_cost": cost_result['calculations']['machine_cost'],
                    "estimated_time_hours": round(estimated_time / 60, 2),
                    "material_name": material_name,
                    "volume_mm3": volume_mm3
                },
                "detailed_breakdown": cost_result,
                "time_estimation": time_estimate
            }
            return jsonify(quick_summary), 200
        else:
            return jsonify(cost_result), 400
            
    except ValueError as e:
        return jsonify({
            "success": False,
            "message": f"Değer hatası: {str(e)}"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/supported-materials', methods=['GET'])
@jwt_required()
def get_supported_materials():
    """Desteklenen malzemeleri getir"""
    try:
        from services.material_service import MaterialService
        
        result = MaterialService.get_all_materials(limit=1000)
        
        if result['success']:
            # Sadece yoğunluk ve fiyat bilgisi olan malzemeleri filtrele
            materials_with_cost_data = [
                {
                    "name": material['name'],
                    "density": material.get('density'),
                    "price_per_kg": material.get('price_per_kg'),
                    "category": material.get('category', 'Genel')
                }
                for material in result['materials']
                if material.get('density') and material.get('price_per_kg')
            ]
            
            return jsonify({
                "success": True,
                "materials": materials_with_cost_data,
                "total_count": len(materials_with_cost_data)
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/material-info/<material_name>', methods=['GET'])
@jwt_required()
def get_material_cost_info(material_name):
    """Belirli malzeme için maliyet bilgisi"""
    try:
        from services.material_service import MaterialService
        
        result = MaterialService.get_material_by_name(material_name)
        
        if result['success']:
            material = result['material']
            
            cost_info = {
                "success": True,
                "material": {
                    "name": material['name'],
                    "density": material.get('density'),
                    "price_per_kg": material.get('price_per_kg'),
                    "category": material.get('category'),
                    "description": material.get('description'),
                    "aliases": material.get('aliases', [])
                },
                "cost_ready": bool(material.get('density') and material.get('price_per_kg'))
            }
            
            return jsonify(cost_info), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/calculation-presets', methods=['GET'])
@jwt_required()
def get_calculation_presets():
    """Hesaplama ön ayarları"""
    try:
        presets = {
            "machine_rates": {
                "cnc_milling_3_axis": 65.0,
                "cnc_milling_5_axis": 120.0,
                "cnc_turning": 55.0,
                "wire_edm": 95.0,
                "sinker_edm": 110.0
            },
            "complexity_factors": {
                "simple": 1.0,
                "moderate": 1.5,
                "complex": 2.5,
                "very_complex": 4.0
            },
            "profit_margins": {
                "competitive": 0.15,
                "standard": 0.25,
                "premium": 0.40
            },
            "material_categories": {
                "aluminum": ["6061", "7075", "2024"],
                "steel": ["1018", "4140", "4340"],
                "stainless": ["304", "316", "17-4PH"],
                "titanium": ["Ti-6Al-4V", "Ti-6Al-2Sn"]
            }
        }
        
        return jsonify({
            "success": True,
            "presets": presets
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/cost-history', methods=['GET'])
@jwt_required()
def get_cost_calculation_history():
    """Kullanıcının maliyet hesaplama geçmişi"""
    try:
        current_user = get_current_user()
        
        # Bu özellik için ayrı bir model gerekebilir
        # Şimdilik basit bir response döndürelim
        
        return jsonify({
            "success": True,
            "message": "Maliyet geçmişi özelliği yakında eklenecek",
            "user_id": current_user['id']
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Beklenmeyen hata: {str(e)}"
        }), 500

@cost_bp.route('/validate-inputs', methods=['POST'])
@jwt_required()
def validate_cost_inputs():
    """Maliyet hesaplama girdilerini doğrula"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "Veri gönderilmedi"
            }), 400
        
        validation_errors = []
        warnings = []
        
        # Hacim kontrolü
        volume = data.get('volume_mm3')
        if volume is not None:
            if volume <= 0:
                validation_errors.append("Hacim pozitif olmalı")
            elif volume > 1_000_000_000:  # 1m³
                warnings.append("Çok büyük hacim değeri")
        
        # Süre kontrolü
        duration = data.get('main_duration_min')
        if duration is not None:
            if duration <= 0:
                validation_errors.append("İşleme süresi pozitif olmalı")
            elif duration > 2880:  # 48 saat
                warnings.append("Çok uzun işleme süresi")
        
        # Makine ücreti kontrolü
        hourly_rate = data.get('machine_hourly_rate')
        if hourly_rate is not None:
            if hourly_rate < 0:
                validation_errors.append("Makine ücreti negatif olamaz")
            elif hourly_rate > 500:
                warnings.append("Çok yüksek makine ücreti")
        
        # Kar marjı kontrolü
        profit_margin = data.get('profit_margin')
        if profit_margin is not None:
            if profit_margin < 0 or profit_margin > 1:
                validation_errors.append("Kar marjı 0-1 arasında olmalı")
        
        return jsonify({
            "success": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "warnings": warnings,
            "inputs_valid": len(validation_errors) == 0
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Doğrulama hatası: {str(e)}"
        }), 500