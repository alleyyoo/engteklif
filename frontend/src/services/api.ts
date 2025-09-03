const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://188.132.220.35:5051";

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  [key: string]: any;
}

export interface MultipleUploadResponse {
  success: boolean;
  message: string;
  upload_summary: {
    total_uploaded: number;
    pdf_files: number;
    step_files: number;
    other_files: number;
    failed_uploads: number;
    matched_pairs: number;
    unmatched_pdfs: number;
    unmatched_steps: number;
  };
  analyses: Array<{
    analysis_id: string;
    type: "pdf_with_step" | "pdf_only" | "step_only" | "document";
    primary_file: string;
    secondary_file?: string;
    match_score?: number;
    file_info: {
      id: string;
      filename: string;
      original_filename: string;
      file_type: string;
      file_size: number;
      analysis_status: string;
      matched_step_file?: string;
      matched_step_path?: string;
      match_score?: number;
      match_quality?: string;
      analysis_strategy?: string;
    };
  }>;
  matching_results: {
    pdf_step_matches: Array<{
      pdf_file: string;
      step_file: string;
      match_score: number;
      match_quality: string;
    }>;
    unmatched_files: {
      pdfs: string[];
      steps: string[];
    };
  };
  failed_uploads: Array<{
    filename: string;
    error: string;
  }>;
  next_steps: {
    analyze_all: string;
    analyze_individual: string;
  };
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

    // STEP Analysis Data
    step_analysis: {
      "X (mm)": number;
      "Y (mm)": number;
      "Z (mm)": number;
      "Prizma Hacmi (mm³)": number;
      "Ürün Hacmi (mm³)": number;
      "Talaş Hacmi (mm³)": number;
      "Talaş Oranı (%)": number;
      "Toplam Yüzey Alanı (mm²)": number;
      "Silindirik Çap (mm)"?: number;
      "Silindirik Yükseklik (mm)"?: number;
      [key: string]: any;
    };

    // Material Calculations
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

    // ✅ ENHANCED - Render Information
    enhanced_renders?: {
      [key: string]: {
        success: boolean;
        view_type: string;
        file_path: string;
        excel_path?: string;
        svg_path?: string;
        dimensions?: {
          width: number;
          height: number;
          depth: number;
        };
        quality?: string;
        file_exists?: boolean;
      };
    };

    // ✅ NEW - Quick access to isometric view
    isometric_view?: string;

    // ✅ ENHANCED - STL Model
    stl_generated?: boolean;
    stl_path?: string;
    stl_file_size?: number;

    // ✅ ENHANCED - Render Status & Details
    render_status?: "none" | "pending" | "processing" | "completed" | "failed";
    render_task_id?: string;
    render_count?: number;
    render_quality?: "high" | "medium" | "low";
    render_strategy?: string;
    render_error?: string;

    // ✅ NEW - PDF Enhancement Details
    pdf_step_extracted?: boolean;

    // ✅ NEW - Render Debug Information
    render_debug?: {
      analysis_id: string;
      file_type: string;
      original_filename: string;
      matched_step_path?: string;
      extracted_step_path?: string;
      step_analysis_available: boolean;
    };

    // ✅ NEW - Render Progress
    render_progress?: {
      renders: number;
      strategy: string;
      render_paths: string[];
    };

    // Processing & Timing
    processing_time: number;
    created_at: string;

    // ✅ YENİ - Grup bilgileri
    group_info?: {
      group_id: string;
      group_name: string;
      group_type: string;
      total_files: number;
      file_types: string[];
      file_names: string[];
      has_step: boolean;
      has_pdf: boolean;
      has_doc: boolean;
      primary_source: string;
      analysis_sources: number;
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
    group_composition?: string;
  };

  // ✅ NEW - Enhancement Details (PDF-STEP matching info)
  enhancement_details?: {
    analysis_strategy: string;
    step_source: string;
    match_score?: number;
    used_matched_step: boolean;
  };
}

export interface RenderStatusResponse {
  success: boolean;
  render_status: "none" | "pending" | "processing" | "completed" | "failed";
  has_renders: boolean;
  render_count: number;
  render_quality?: "high" | "medium" | "low";
  render_strategy?: string;
  render_error?: string;

  // STL Model
  stl_generated?: boolean;
  stl_path?: string;

  // Quick access to isometric view
  isometric_view?: string;

  // Background task info
  background_task?: {
    success: boolean;
    result?: {
      success: boolean;
      renders: number;
      strategy: string;
      render_paths: string[];
    };
  };

  // Debug information
  debug_info?: {
    analysis_id: string;
    file_type: string;
    original_filename: string;
    matched_step_path?: string;
    extracted_step_path?: string;
    step_analysis_available: boolean;
  };

  // Render timing
  last_render_update?: number;

  // Task status
  task_status?: {
    status: string;
    [key: string]: any;
  };

  // Basic renders structure (for compatibility)
  renders?: {
    [key: string]: {
      file_path: string;
      excel_path?: string;
      file_exists?: boolean;
    };
  };

  // Detailed render information
  render_details?: {
    [key: string]: {
      file_path: string;
      success: boolean;
      view_type: string;
      svg_path?: string;
      excel_path?: string;
      dimensions?: {
        width: number;
        height: number;
        depth: number;
      };
      quality?: string;
      file_size?: number;
      format?: string;
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

// ✅ YENİ - Grup analizi için interface'ler
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

// ✅ YENİ - Cache refresh interface'leri
export interface CacheRefreshResponse {
  success: boolean;
  message: string;
  cache_refreshed?: boolean;
  material_count?: number;
  refresh_time?: string;
  admin_user?: string;
}

export interface CacheStatusResponse {
  success: boolean;
  cache_info: {
    database_material_count: number;
    cache_material_count?: number;
    cache_status: "active" | "empty" | "unknown";
    analysis_service_ready: boolean;
    cache_db_sync?: boolean;
    last_refresh?: string;
    service_error?: string;
  };
  recommendations: Array<{
    type: "success" | "info" | "warning" | "error";
    message: string;
    action: string;
  }>;
}

// ✅ YENİ - Re-analysis interface'leri
export interface ReanalysisResponse {
  success: boolean;
  message: string;
  analysis: AnalysisResult["analysis"];
  processing_time: number;
  reanalysis: boolean;
  material_cache_refreshed: boolean;
  changes: {
    old_materials: string[];
    new_materials: string[];
    material_changed: boolean;
  };
}

export interface BulkReanalysisResponse {
  success: boolean;
  message: string;
  results: Array<{
    analysis_id: string;
    success: boolean;
    message: string;
    filename?: string;
    processing_time?: number;
    material_changed?: boolean;
    old_materials?: string[];
    new_materials?: string[];
  }>;
  summary: {
    total: number;
    successful: number;
    failed: number;
    material_cache_refreshed: boolean;
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

  // ============================================================================
  // FILE UPLOAD METHODS
  // ============================================================================

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

  async uploadMultipleFiles(files: File[]): Promise<MultipleUploadResponse> {
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

  // ============================================================================
  // ANALYSIS METHODS
  // ============================================================================

  async analyzeFile(analysisId: string, rotationStrategy: 'aselsan' | 'other' = 'other'): Promise<AnalysisResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/upload/analyze/${analysisId}`,
    {
      method: "POST",
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        rotation_strategy: rotationStrategy
      })
    }
  );

  return response.json();
}

  // ✅ YENİ - Force re-analysis (updated materials ile)
  async forceReanalysis(analysisId: string): Promise<ReanalysisResponse> {
    try {
      console.log("🔄 Force re-analysis başlatılıyor...", { analysisId });

      const response = await fetch(
        `${API_BASE_URL}/api/upload/re-analyze/${analysisId}`,
        {
          method: "POST",
          headers: this.getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ Force re-analysis başarılı:", result);
      return result;
    } catch (error: any) {
      console.error("❌ Force re-analysis hatası:", error);
      throw error;
    }
  }

  // ✅ YENİ - Bulk re-analysis
  async bulkReanalysis(analysisIds: string[]): Promise<BulkReanalysisResponse> {
    try {
      console.log("🔄 Bulk re-analysis başlatılıyor...", {
        analysisCount: analysisIds.length,
        analysisIds,
      });

      const response = await fetch(
        `${API_BASE_URL}/api/upload/bulk-re-analyze`,
        {
          method: "POST",
          headers: this.getAuthHeaders(),
          body: JSON.stringify({
            analysis_ids: analysisIds,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ Bulk re-analysis başarılı:", {
        total: result.summary?.total,
        successful: result.summary?.successful,
        failed: result.summary?.failed,
      });

      return result;
    } catch (error: any) {
      console.error("❌ Bulk re-analysis hatası:", error);
      return {
        success: false,
        message: error.message || "Toplu yeniden analiz başarısız",
        results: [],
        summary: {
          total: analysisIds.length,
          successful: 0,
          failed: analysisIds.length,
          material_cache_refreshed: false,
        },
      };
    }
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

  // ============================================================================
  // MATERIAL CACHE METHODS - ✅ YENİ
  // ============================================================================

  // ✅ YENİ - Material cache refresh
  async refreshMaterialCache(): Promise<CacheRefreshResponse> {
    try {
      console.log("🔄 Material cache refresh API çağrısı...");

      const response = await fetch(
        `${API_BASE_URL}/api/materials/refresh-cache`,
        {
          method: "POST",
          headers: this.getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ Material cache refresh başarılı:", result);
      return result;
    } catch (error: any) {
      console.error("❌ Material cache refresh hatası:", error);
      return {
        success: false,
        message: error.message || "Cache yenileme başarısız",
      };
    }
  }

  // ✅ YENİ - Cache status kontrolü
  async getCacheStatus(): Promise<CacheStatusResponse> {
    try {
      console.log("📊 Cache status kontrolü...");

      const response = await fetch(
        `${API_BASE_URL}/api/materials/cache-status`,
        {
          method: "GET",
          headers: this.getAuthHeaders(),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ Cache status alındı:", result);
      return result;
    } catch (error: any) {
      console.error("❌ Cache status hatası:", error);
      return {
        success: false,
        cache_info: {
          database_material_count: 0,
          cache_status: "unknown",
          analysis_service_ready: false,
          service_error: error.message,
        },
        recommendations: [
          {
            type: "error",
            message: "Cache status alınamadı",
            action: "Bağlantıyı kontrol edin",
          },
        ],
      };
    }
  }

  // ✅ YENİ - Material analysis health check
  async checkMaterialAnalysisHealth(): Promise<{
    success: boolean;
    material_count: number;
    cache_status: string;
    last_cache_update?: string;
    analysis_service_ready: boolean;
  }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/materials/health`, {
        method: "GET",
        headers: this.getAuthHeaders(),
      });

      return response.json();
    } catch (error: any) {
      console.error("❌ Material analysis health check failed:", error);
      return {
        success: false,
        material_count: 0,
        cache_status: "error",
        analysis_service_ready: false,
      };
    }
  }

  // ============================================================================
  // ANALYSIS STATUS & MANAGEMENT
  // ============================================================================

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

  // ============================================================================
  // EXCEL EXPORT METHODS
  // ============================================================================

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

  // ============================================================================
  // EXCEL MERGE METHODS
  // ============================================================================

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

  // ============================================================================
  // RENDER METHODS
  // ============================================================================

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

  // ============================================================================
  // AUTH METHODS
  // ============================================================================

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

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  async getSupportedFormats(): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/upload/supported-formats`,
      {
        method: "GET",
      }
    );

    return response.json();
  }

  // ============================================================================
  // MATERIAL MANAGEMENT METHODS - ✅ YENİ
  // ============================================================================

  async getMaterials(
    page = 1,
    limit = 50,
    search = "",
    category = ""
  ): Promise<ApiResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...(search && { search }),
      ...(category && { category }),
    });

    const response = await fetch(`${API_BASE_URL}/api/materials?${params}`, {
      method: "GET",
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }

  async createMaterial(materialData: {
    name: string;
    aliases?: string[];
    density?: number;
    price_per_kg?: number;
    category?: string;
    description?: string;
  }): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/materials`, {
      method: "POST",
      headers: this.getAuthHeaders(),
      body: JSON.stringify(materialData),
    });

    return response.json();
  }

  async updateMaterial(
    materialId: string,
    updateData: {
      name?: string;
      aliases?: string[];
      density?: number;
      price_per_kg?: number;
      category?: string;
      description?: string;
    }
  ): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/materials/${materialId}`,
      {
        method: "PUT",
        headers: this.getAuthHeaders(),
        body: JSON.stringify(updateData),
      }
    );

    return response.json();
  }

  async deleteMaterial(materialId: string): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/materials/${materialId}`,
      {
        method: "DELETE",
        headers: this.getAuthHeaders(),
      }
    );

    return response.json();
  }

  async addMaterialAliases(
    materialId: string,
    aliases: string[]
  ): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/materials/${materialId}/aliases`,
      {
        method: "POST",
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ aliases }),
      }
    );

    return response.json();
  }

  async removeMaterialAlias(
    materialId: string,
    alias: string
  ): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/materials/${materialId}/aliases/${encodeURIComponent(
        alias
      )}`,
      {
        method: "DELETE",
        headers: this.getAuthHeaders(),
      }
    );

    return response.json();
  }

  async getMaterialCategories(): Promise<ApiResponse> {
    const response = await fetch(`${API_BASE_URL}/api/materials/categories`, {
      method: "GET",
      headers: this.getAuthHeaders(),
    });

    return response.json();
  }

  async bulkUpdateMaterialPrices(priceUpdates: {
    [materialName: string]: number;
  }): Promise<ApiResponse> {
    const response = await fetch(
      `${API_BASE_URL}/api/materials/bulk-update-prices`,
      {
        method: "POST",
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ price_updates: priceUpdates }),
      }
    );

    return response.json();
  }
}

export const apiService = new ApiService();
