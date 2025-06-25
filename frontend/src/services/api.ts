const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://188.132.220.35:5051";

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
  render_status?: 'none' | 'pending' | 'processing' | 'completed' | 'failed'; // ✅ YENİ
  analysis: {
    id: string;
    user_id: string;
    filename: string;
    original_filename: string;
    file_type: string;
    analysis_status: string;
    material_matches: string[];
    step_analysis: {
      "X (mm)": number;
      "Y (mm)": number;
      "Z (mm)": number;
      "Prizma Hacmi (mm³)": number;
      "Ürün Hacmi (mm³)": number;
      "Talaş Hacmi (mm³)": number;
      "Talaş Oranı (%)": number;
      "Toplam Yüzey Alanı (mm²)": number;
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
    stl_generated?: boolean;  // ✅ YENİ
    stl_path?: string;        // ✅ YENİ
    stl_file_size?: number;   // ✅ YENİ
    render_status?: 'none' | 'pending' | 'processing' | 'completed' | 'failed'; // ✅ YENİ
    render_task_id?: string;  // ✅ YENİ
    processing_time: number;
    created_at: string;
  };
  processing_time: number;
  analysis_details: {
    material_matches_count: number;
    step_analysis_available: boolean;
    cost_estimation_available: boolean;
    enhanced_renders_count?: number;  // ✅ optional yap
    render_types?: string[];          // ✅ optional yap
    processing_steps?: number;        // ✅ YENİ
    all_material_calculations_count?: number; // ✅ YENİ
    material_options_count?: number;  // ✅ YENİ
    "3d_render_available"?: boolean;  // ✅ YENİ
    render_in_progress?: boolean;     // ✅ YENİ
  };
}

// ✅ Render Status Response type'ı da ekleyelim
export interface RenderStatusResponse {
  success: boolean;
  render_status: 'none' | 'pending' | 'processing' | 'completed' | 'failed';
  has_renders: boolean;
  render_count: number;
  stl_generated?: boolean;
  stl_path?: string;
  task_status?: {
    status: string;
    [key: string]: any;
  };
  renders?: {
    [key: string]: {
      file_path: string;
      excel_path?: string;
    };
  };
}

export interface ExcelMergeResponse {
  success: boolean;
  message?: string;
  blob: Blob;
  filename?: string;
}

export interface ExcelMergePreviewResponse {
  success: boolean;
  preview: {
    excel_info: {
      filename: string;
      total_rows: number;
      total_columns: number;
      headers: string[];
    };
    sample_rows: Array<{
      row: number;
      product_code: string;
      will_match: boolean;
    }>;
    analyses: Array<{
      id: string;
      filename: string;
      product_code: string;
      has_step_analysis: boolean;
      has_material: boolean;
    }>;
    estimated_matches: number;
  };
}

// ✅ YENİ - Multiple Excel Export Response
export interface MultipleExcelExportResponse {
  success: boolean;
  message?: string;
  blob: Blob;
  filename?: string;
}

class ApiService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem("accessToken");
    return {
      Authorization: token ? `Bearer ${token}` : "",
      "Content-Type": "application/json",
    };
  }

  private getMultipartHeaders(): HeadersInit {
    const token = localStorage.getItem("accessToken");
    return {
      Authorization: token ? `Bearer ${token}` : "",
    };
  }

  async uploadSingleFile(file: File): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/upload/single`, {
      method: "POST",
      headers: this.getMultipartHeaders(),
      body: formData,
    });

    return response.json();
  }

  async uploadMultipleFiles(files: File[]): Promise<ApiResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${API_BASE_URL}/api/upload/multiple`, {
      method: "POST",
      headers: this.getMultipartHeaders(),
      body: formData,
    });

    return response.json();
  }

  async analyzeFile(analysisId: string): Promise<AnalysisResult> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/analyze/${analysisId}`,
      {
        method: "POST",
        headers: this.getAuthHeaders(),
      }
    );

    return response.json();
  }

  async getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/status/${analysisId}`,
      {
        method: "GET",
        headers: this.getAuthHeaders(),
      }
    );

    return response.json();
  }

  async getMyUploads(page = 1, limit = 20): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/my-uploads?page=${page}&limit=${limit}`,
      {
        method: "GET",
        headers: this.getAuthHeaders(),
      }
    );

    return response.json();
  }

  async deleteAnalysis(analysisId: string): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/delete/${analysisId}`,
      {
        method: "DELETE",
        headers: this.getAuthHeaders(),
      }
    );

    return response.json();
  }

  // ✅ ESKİ - Tek analiz Excel export (şimdi deprecated)
  async exportAnalysisExcel(analysisId: string): Promise<Blob> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/export-excel/${analysisId}`,
      {
        method: "GET",
        headers: this.getMultipartHeaders(),
      }
    );

    return response.blob();
  }

  // ✅ YENİ - Birden fazla analizi Excel'e export
  async exportMultipleAnalysesExcel(
    analysisIds: string[]
  ): Promise<MultipleExcelExportResponse> {
    try {
      console.log("📊 Multiple Excel export başlıyor...", {
        analysisCount: analysisIds.length,
        analysisIds: analysisIds,
      });

      const response = await fetch(
        `${API_BASE_URL}/api/upload/export-excel-multiple`,
        {
          method: "POST",
          headers: this.getAuthHeaders(),
          body: JSON.stringify({
            analysis_ids: analysisIds,
          }),
        }
      );

      if (!response.ok) {
        // Hata durumunda JSON response'u oku
        const errorData = await response.json();
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      // Başarılı durumda blob'u al
      const blob = await response.blob();

      // Response header'ından dosya adını al (eğer varsa)
      const contentDisposition = response.headers.get("content-disposition");
      let filename = `coklu_analiz_${
        analysisIds.length
      }_dosya_${Date.now()}.xlsx`;

      if (contentDisposition) {
        const matches = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        );
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, "");
        }
      }

      console.log("✅ Multiple Excel export başarılı:", {
        blobSize: blob.size,
        filename: filename,
        analysisCount: analysisIds.length,
      });

      return {
        success: true,
        blob: blob,
        filename: filename,
      };
    } catch (error: any) {
      console.error("❌ Multiple Excel export hatası:", error);

      return {
        success: false,
        message: error.message || "Çoklu Excel export başarısız",
        blob: new Blob(), // Boş blob
      };
    }
  }

  async mergeWithExcel(
    excelFile: File,
    analysisIds: string[]
  ): Promise<ExcelMergeResponse> {
    try {
      console.log("📊 Excel merge API çağrısı başlıyor...", {
        excelFile: excelFile.name,
        analysisCount: analysisIds.length,
      });

      const formData = new FormData();
      formData.append("excel_file", excelFile);

      // Analysis ID'lerini array olarak ekle
      analysisIds.forEach((id) => {
        formData.append("analysis_ids", id);
      });

      const response = await fetch(
        `${API_BASE_URL}/api/upload/merge-with-excel`,
        {
          method: "POST",
          headers: this.getMultipartHeaders(),
          body: formData,
        }
      );

      if (!response.ok) {
        // Hata durumunda JSON response'u oku
        const errorData = await response.json();
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      // Başarılı durumda blob'u al
      const blob = await response.blob();

      // Response header'ından dosya adını al (eğer varsa)
      const contentDisposition = response.headers.get("content-disposition");
      let filename = `merged_excel_${Date.now()}.xlsx`;

      if (contentDisposition) {
        const matches = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        );
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, "");
        }
      }

      console.log("✅ Excel merge başarılı:", {
        blobSize: blob.size,
        filename: filename,
      });

      return {
        success: true,
        blob: blob,
        filename: filename,
      };
    } catch (error: any) {
      console.error("❌ Excel merge hatası:", error);

      return {
        success: false,
        message: error.message || "Excel birleştirme başarısız",
        blob: new Blob(), // Boş blob
      };
    }
  }

  async previewExcelMerge(
    excelFile: File,
    analysisIds: string[]
  ): Promise<ExcelMergePreviewResponse> {
    try {
      const formData = new FormData();
      formData.append("excel_file", excelFile);

      analysisIds.forEach((id) => {
        formData.append("analysis_ids", id);
      });

      const response = await fetch(`${API_BASE_URL}/api/upload/merge-preview`, {
        method: "POST",
        headers: this.getMultipartHeaders(),
        body: formData,
      });

      return response.json();
    } catch (error: any) {
      console.error("❌ Excel preview hatası:", error);

      return {
        success: false,
        preview: {
          excel_info: {
            filename: "",
            total_rows: 0,
            total_columns: 0,
            headers: [],
          },
          sample_rows: [],
          analyses: [],
          estimated_matches: 0,
        },
      };
    }
  }

  async getSupportedFormats(): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/supported-formats`,
      {
        method: "GET",
      }
    );

    return response.json();
  }

  async generateStepRender(
    analysisId: string,
    options = {}
  ): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/render/${analysisId}`,
      {
        method: "POST",
        headers: this.getAuthHeaders(),
        body: JSON.stringify(options),
      }
    );

    return response.json();
  }

  async login(username: string, password: string): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    return response.json();
  }

  async getCurrentUser(): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: "GET",
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }

  async getRenderStatus(analysisId: string): Promise<RenderStatusResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/render-status/${analysisId}`,
      {
        method: "GET",
        headers: this.getAuthHeaders(),
      }
    );

    return response.json();
  }
}


export const apiService = new ApiService();
