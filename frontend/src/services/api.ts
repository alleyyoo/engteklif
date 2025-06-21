// src/services/api.ts
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5050';

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  [key: string]: any;
}

export interface FileUploadResponse {
  success: boolean;
  message: string;
  file_info?: {
    analysis_id: string;
    filename: string;
    original_filename: string;
    file_type: string;
    file_size: number;
    upload_time: string;
  };
}

export interface AnalysisStatus {
  success: boolean;
  analysis: {
    id: string;
    status: string;
    filename: string;
    original_filename: string;
    file_type: string;
    processing_time?: number;
    error_message?: string;
    created_at: string;
    updated_at: string;
    has_step_analysis: boolean;
    has_renders: boolean;
    material_matches_count: number;
    render_count: number;
  };
}

export interface AnalysisResult {
  success: boolean;
  message: string;
  analysis: {
    id: string;
    user_id: string;
    filename: string;
    original_filename: string;
    file_type: string;
    analysis_status: string;
    material_matches: string[];
    step_analysis: {
      'X (mm)': number;
      'Y (mm)': number;
      'Z (mm)': number;
      'Prizma Hacmi (mm³)': number;
      'Ürün Hacmi (mm³)': number;
      'Talaş Hacmi (mm³)': number;
      'Talaş Oranı (%)': number;
      'Toplam Yüzey Alanı (mm²)': number;
      [key: string]: any;
    };
    all_material_calculations: Array<{
      material: string;
      density: number;
      mass_kg: number;
      price_per_kg: number;
      material_cost: number;
      volume_mm3: number;
    }>;
    material_options: Array<{
      name: string;
      category: string;
      density: number;
      mass_kg: number;
      price_per_kg: number;
      material_cost: number;
    }>;
    enhanced_renders?: {
      [key: string]: {
        success: boolean;
        view_type: string;
        file_path: string;
        excel_path?: string;
        svg_path?: string;
      };
    };
    processing_time: number;
    created_at: string;
  };
  processing_time: number;
  analysis_details: {
    material_matches_count: number;
    step_analysis_available: boolean;
    cost_estimation_available: boolean;
    enhanced_renders_count: number;
    render_types: string[];
  };
}

class ApiService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('accessToken');
    return {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
    };
  }

  private getMultipartHeaders(): HeadersInit {
    const token = localStorage.getItem('accessToken');
    return {
      'Authorization': token ? `Bearer ${token}` : '',
    };
  }

  async uploadSingleFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/upload/single`, {
      method: 'POST',
      headers: this.getMultipartHeaders(),
      body: formData,
    });

    return response.json();
  }

  async uploadMultipleFiles(files: File[]): Promise<ApiResponse> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await fetch(`${API_BASE_URL}/api/upload/multiple`, {
      method: 'POST',
      headers: this.getMultipartHeaders(),
      body: formData,
    });

    return response.json();
  }

  async analyzeFile(analysisId: string): Promise<AnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/api/upload/analyze/${analysisId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }

  async getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
    const response = await fetch(`${API_BASE_URL}/api/upload/status/${analysisId}`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }

  async getMyUploads(page = 1, limit = 20): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/upload/my-uploads?page=${page}&limit=${limit}`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }

  async deleteAnalysis(analysisId: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/upload/delete/${analysisId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }

  async exportAnalysisExcel(analysisId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/api/upload/export-excel/${analysisId}`, {
      method: 'GET',
      headers: this.getMultipartHeaders(),
    });

    return response.blob();
  }

  async getSupportedFormats(): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/upload/supported-formats`, {
      method: 'GET',
    });

    return response.json();
  }

  async generateStepRender(analysisId: string, options = {}): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/upload/render/${analysisId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(options),
    });

    return response.json();
  }

  async login(username: string, password: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    return response.json();
  }

  async getCurrentUser(): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }
}

export const apiService = new ApiService();