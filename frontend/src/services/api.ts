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
  render_status?: "none" | "pending" | "processing" | "completed" | "failed";
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
      original_text?: string;
      category?: string;
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
    stl_generated?: boolean;
    stl_path?: string;
    stl_file_size?: number;
    render_status?: "none" | "pending" | "processing" | "completed" | "failed";
    render_task_id?: string;
    processing_time: number;
    created_at: string;
    // ✅ YENİ - Grup bilgileri
    group_info?: {
      group_id: string;
      group_name: string;
      total_files: number;
      file_types: string[];
      has_step: boolean;
      has_pdf: boolean;
    };
  };
  processing_time: number;
  analysis_details: {
    material_matches_count: number;
    step_analysis_available: boolean;
    cost_estimation_available: boolean;
    enhanced_renders_count?: number;
    render_types?: string[];
    processing_steps?: number;
    all_material_calculations_count?: number;
    material_options_count?: number;
    "3d_render_available"?: boolean;
    render_in_progress?: boolean;
    // ✅ YENİ - Grup analizi bilgileri
    grouped_analysis?: boolean;
    source_files?: number;
    primary_source?: string;
  };
}

export interface RenderStatusResponse {
  success: boolean;
  render_status: "none" | "pending" | "processing" | "completed" | "failed";
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

export interface MultipleExcelExportResponse {
  success: boolean;
  message?: string;
  blob: Blob;
  filename?: string;
}

// ✅ YENİ - Grup analizi için endpoint'ler
export interface GroupAnalysisRequest {
  analysis_ids: string[];
  group_name: string;
  primary_analysis_id?: string;
}

export interface GroupAnalysisResponse {
  success: boolean;
  message?: string;
  group_analysis: AnalysisResult;
  merged_data: {
    best_step_analysis: any;
    best_material_matches: string[];
    best_renders: any;
    source_breakdown: {
      [key: string]: string; // analysis_id -> source_type
    };
  };
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

  // ✅ YENİ - Grup analizi oluşturma
  async createGroupAnalysis(
    groupRequest: GroupAnalysisRequest
  ): Promise<GroupAnalysisResponse> {
    try {
      console.log("📁 Creating group analysis...", groupRequest);

      const response = await fetch(
        `${API_BASE_URL}/api/analysis/create-group`,
        {
          method: "POST",
          headers: this.getAuthHeaders(),
          body: JSON.stringify(groupRequest),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.message || `HTTP ${response.status}`);
      }

      console.log("✅ Group analysis created successfully:", result);
      return result;
    } catch (error: any) {
      console.error("❌ Group analysis creation failed:", error);
      return {
        success: false,
        message: error.message || "Grup analizi oluşturulamadı",
        group_analysis: {} as AnalysisResult,
        merged_data: {
          best_step_analysis: {},
          best_material_matches: [],
          best_renders: {},
          source_breakdown: {},
        },
      };
    }
  }

  // ✅ YENİ - Benzer dosyaları otomatik gruplama
  async autoGroupSimilarFiles(analysisIds: string[]): Promise<{
    success: boolean;
    groups: Array<{
      group_name: string;
      analysis_ids: string[];
      similarity_score: number;
    }>;
  }> {
    try {
      console.log("🤖 Auto-grouping similar files...", { analysisIds });

      const response = await fetch(`${API_BASE_URL}/api/analysis/auto-group`, {
        method: "POST",
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ analysis_ids: analysisIds }),
      });

      return response.json();
    } catch (error: any) {
      console.error("❌ Auto-grouping failed:", error);
      return {
        success: false,
        groups: [],
      };
    }
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
        const errorData = await response.json();
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const blob = await response.blob();

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
        blob: new Blob(),
      };
    }
  }

  // ✅ YENİ - Grup Excel export
  async exportGroupAnalysisExcel(
    groupAnalysisId: string,
    groupName: string
  ): Promise<MultipleExcelExportResponse> {
    try {
      console.log("📁 Group Excel export başlıyor...", {
        groupAnalysisId,
        groupName,
      });

      const response = await fetch(
        `${API_BASE_URL}/api/upload/export-excel/${groupAnalysisId}`,
        {
          method: "GET",
          headers: this.getMultipartHeaders(),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const blob = await response.blob();

      const contentDisposition = response.headers.get("content-disposition");
      let filename = `grup_analizi_${groupName}_${Date.now()}.xlsx`;

      if (contentDisposition) {
        const matches = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        );
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, "");
        }
      }

      console.log("✅ Group Excel export başarılı:", {
        blobSize: blob.size,
        filename: filename,
      });

      return {
        success: true,
        blob: blob,
        filename: filename,
      };
    } catch (error: any) {
      console.error("❌ Group Excel export hatası:", error);

      return {
        success: false,
        message: error.message || "Grup Excel export başarısız",
        blob: new Blob(),
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
        const errorData = await response.json();
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const blob = await response.blob();

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
        blob: new Blob(),
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

  // ✅ YENİ - Benzer dosya önerisi
  async getSimilarFilesSuggestions(currentAnalysisIds: string[]): Promise<{
    success: boolean;
    suggestions: Array<{
      group_name: string;
      files: Array<{
        analysis_id: string;
        filename: string;
        similarity_score: number;
      }>;
    }>;
  }> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/analysis/similar-suggestions`,
        {
          method: "POST",
          headers: this.getAuthHeaders(),
          body: JSON.stringify({ analysis_ids: currentAnalysisIds }),
        }
      );

      return response.json();
    } catch (error: any) {
      console.error("❌ Similar files suggestions failed:", error);
      return {
        success: false,
        suggestions: [],
      };
    }
  }
}

export const apiService = new ApiService();
