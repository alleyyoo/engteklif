from typing import List, Dict, Any
from models.geometric_measurement import GeometricMeasurement, GeometricMeasurementCreate, GeometricMeasurementUpdate
from bson import ObjectId

class GeometricMeasurementService:
    
    @staticmethod
    def create_measurement(measurement_data: GeometricMeasurementCreate) -> Dict[str, Any]:
        """Yeni geometrik ölçüm oluştur"""
        try:
            measurement = GeometricMeasurement.create_measurement(measurement_data.dict())
            return {
                "success": True,
                "message": "Ölçüm başarıyla oluşturuldu",
                "measurement": measurement
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ölçüm oluşturulurken hata: {str(e)}"
            }
    
    @staticmethod
    def get_all_measurements(page: int = 1, limit: int = 50, search: str = None) -> Dict[str, Any]:
        """Tüm ölçümleri getir"""
        try:
            skip = (page - 1) * limit
            
            if search:
                measurements = GeometricMeasurement.search_measurements(search)
                # Manuel pagination for search results
                total = len(measurements)
                measurements = measurements[skip:skip + limit]
            else:
                measurements = GeometricMeasurement.get_all_measurements(limit, skip)
                total = GeometricMeasurement.get_count()
            
            return {
                "success": True,
                "measurements": measurements,
                "pagination": {
                    "current_page": page,
                    "total_pages": (total + limit - 1) // limit,
                    "total_items": total,
                    "items_per_page": limit
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ölçümler getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def get_measurement_by_id(measurement_id: str) -> Dict[str, Any]:
        """ID ile ölçüm getir"""
        try:
            if not ObjectId.is_valid(measurement_id):
                return {
                    "success": False,
                    "message": "Geçersiz ölçüm ID'si"
                }
            
            measurement = GeometricMeasurement.find_by_id(measurement_id)
            if not measurement:
                return {
                    "success": False,
                    "message": "Ölçüm bulunamadı"
                }
            
            return {
                "success": True,
                "measurement": measurement
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Ölçüm getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def update_measurement(measurement_id: str, update_data: GeometricMeasurementUpdate) -> Dict[str, Any]:
        """Ölçüm güncelle"""
        try:
            if not ObjectId.is_valid(measurement_id):
                return {
                    "success": False,
                    "message": "Geçersiz ölçüm ID'si"
                }
            
            # Sadece None olmayan değerleri güncelle
            filtered_data = {k: v for k, v in update_data.dict().items() if v is not None}
            
            if not filtered_data:
                return {
                    "success": False,
                    "message": "Güncellenecek veri bulunamadı"
                }
            
            success = GeometricMeasurement.update_measurement(measurement_id, filtered_data)
            if success:
                measurement = GeometricMeasurement.find_by_id(measurement_id)
                return {
                    "success": True,
                    "message": "Ölçüm başarıyla güncellendi",
                    "measurement": measurement
                }
            else:
                return {
                    "success": False,
                    "message": "Güncelleme başarısız"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Güncelleme sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def delete_measurement(measurement_id: str) -> Dict[str, Any]:
        """Ölçüm sil"""
        try:
            if not ObjectId.is_valid(measurement_id):
                return {
                    "success": False,
                    "message": "Geçersiz ölçüm ID'si"
                }
            
            success = GeometricMeasurement.delete_measurement(measurement_id)
            if success:
                return {
                    "success": True,
                    "message": "Ölçüm başarıyla silindi"
                }
            else:
                return {
                    "success": False,
                    "message": "Silme işlemi başarısız"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Silme sırasında hata: {str(e)}"
            }
    
    @staticmethod
    def get_measurement_types() -> Dict[str, Any]:
        """Ölçüm türlerini getir"""
        try:
            types = GeometricMeasurement.get_measurement_types()
            return {
                "success": True,
                "types": types
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Türler getirilirken hata: {str(e)}"
            }
    
    @staticmethod
    def find_matching_measurement(measurement_type: str, value: float) -> Dict[str, Any]:
        """Değere uygun ölçüm bul"""
        try:
            measurement = GeometricMeasurement.find_matching_measurement(measurement_type, value)
            if measurement:
                return {
                    "success": True,
                    "measurement": measurement,
                    "multiplier": measurement.get('multiplier', 1.0)
                }
            else:
                return {
                    "success": False,
                    "message": "Uygun ölçüm bulunamadı",
                    "multiplier": 1.0  # Default multiplier
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Arama sırasında hata: {str(e)}",
                "multiplier": 1.0
            }