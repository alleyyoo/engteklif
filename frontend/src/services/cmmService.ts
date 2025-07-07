const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://188.132.220.35:5051";

export interface CMMUploadResponse {
  success: boolean;
  message: string;
  analysis_id: string;
  data: {
    file_count: number;
    measurement_count: number;
    operations: string[];
    excel_available: boolean;
    excel_filename: string;
    excel_download_url: string;
    processing_time: string;
  };
  upload_summary: {
    total_uploaded: number;
    total_measurements: number;
    operations_detected: string[];
    excel_generated: boolean;
  };
}

export interface CMMAnalysis {
  _id: string;
  user_id: string;
  analysis_id: string;
  uploaded_files: Array<{
    original_name: string;
    saved_name: string;
    file_path: string;
    file_size: number;
  }>;
  file_count: number;
  operations: string[];
  measurement_count: number;
  excel_path: string;
  excel_filename: string;
  status: string;
  created_at: string;
  excel_available: boolean;
  processing_summary: {
    total_files: number;
    successful_files: number;
    total_measurements: number;
    operations_found: string[];
  };
}

export interface CMMListResponse {
  success: boolean;
  analyses: CMMAnalysis[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface CMMStatsResponse {
  success: boolean;
  stats: {
    total_analyses: number;
    this_month_analyses: number;
    total_measurements: number;
    avg_measurements_per_analysis: number;
    top_operations: Array<{
      operation: string;
      count: number;
    }>;
  };
}

export interface CMMSupportedFormatsResponse {
  success: boolean;
  supported_formats: {
    rtf: {
      extensions: string[];
      description: string;
      mime_types: string[];
    };
  };
  max_file_size: string;
  max_files: number;
  features: string[];
}

class CMMService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem("accessToken");
    return {
      Authorization: token ? `Bearer ${token}` : "",
    };
  }

  private getJsonHeaders(): HeadersInit {
    const token = localStorage.getItem("accessToken");
    return {
      Authorization: token ? `Bearer ${token}` : "",
      "Content-Type": "application/json",
    };
  }

  // ============================================================================
  // CMM FILE UPLOAD & PROCESSING
  // ============================================================================

  /**
   * CMM RTF dosyalarını yükle ve parse et
   */
  async uploadCMMFiles(files: File[]): Promise<CMMUploadResponse> {
    try {
      console.log("📄 CMM dosyaları yükleniyor...", {
        fileCount: files.length,
        fileNames: files.map((f) => f.name),
      });

      // Dosya türü kontrolü
      const invalidFiles = files.filter(
        (file) => !file.name.toLowerCase().endsWith(".rtf")
      );

      if (invalidFiles.length > 0) {
        throw new Error(
          `Geçersiz dosya türleri: ${invalidFiles
            .map((f) => f.name)
            .join(", ")}. Sadece RTF dosyaları desteklenir.`
        );
      }

      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });

      const response = await fetch(`${API_BASE_URL}/api/cmm/upload`, {
        method: "POST",
        headers: this.getAuthHeaders(),
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ CMM upload başarılı:", {
        analysisId: result.analysis_id,
        measurementCount: result.data?.measurement_count,
        operations: result.data?.operations,
      });

      return result;
    } catch (error: any) {
      console.error("❌ CMM upload hatası:", error);
      throw error;
    }
  }

  /**
   * CMM Excel dosyasını indir
   */
  async downloadCMMExcel(
    analysisId: string
  ): Promise<{ blob: Blob; filename: string }> {
    try {
      console.log("📊 CMM Excel indiriliyor...", { analysisId });

      const response = await fetch(
        `${API_BASE_URL}/api/cmm/download/${analysisId}`,
        {
          method: "GET",
          headers: this.getAuthHeaders(),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const blob = await response.blob();

      // Filename'i header'dan al
      const contentDisposition = response.headers.get("content-disposition");
      let filename = `cmm_raporu_${analysisId}.xlsx`;

      if (contentDisposition) {
        const matches = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        );
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, "");
        }
      }

      console.log("✅ CMM Excel indirildi:", {
        blobSize: blob.size,
        filename,
        analysisId,
      });

      return { blob, filename };
    } catch (error: any) {
      console.error("❌ CMM Excel indirme hatası:", error);
      throw error;
    }
  }

  // ============================================================================
  // CMM ANALYSIS MANAGEMENT
  // ============================================================================

  /**
   * Kullanıcının CMM analizlerini listele
   */
  async getMyCMMAnalyses(page = 1, limit = 20): Promise<CMMListResponse> {
    try {
      console.log("📋 CMM analizleri alınıyor...", { page, limit });

      const response = await fetch(
        `${API_BASE_URL}/api/cmm/my-analyses?page=${page}&limit=${limit}`,
        {
          method: "GET",
          headers: this.getJsonHeaders(),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ CMM analizleri alındı:", {
        analysisCount: result.analyses?.length,
        totalCount: result.pagination?.total,
      });

      return result;
    } catch (error: any) {
      console.error("❌ CMM analiz listesi hatası:", error);
      throw error;
    }
  }

  /**
   * Belirli bir CMM analizinin detaylarını al
   */
  async getCMMAnalysis(
    analysisId: string
  ): Promise<{ success: boolean; analysis: CMMAnalysis }> {
    try {
      console.log("🔍 CMM analiz detayı alınıyor...", { analysisId });

      const response = await fetch(
        `${API_BASE_URL}/api/cmm/analysis/${analysisId}`,
        {
          method: "GET",
          headers: this.getJsonHeaders(),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ CMM analiz detayı alındı:", {
        analysisId: result.analysis?._id,
        measurementCount: result.analysis?.measurement_count,
      });

      return result;
    } catch (error: any) {
      console.error("❌ CMM analiz detayı hatası:", error);
      throw error;
    }
  }

  /**
   * CMM analizini sil
   */
  async deleteCMMAnalysis(
    analysisId: string
  ): Promise<{ success: boolean; message: string }> {
    try {
      console.log("🗑️ CMM analizi siliniyor...", { analysisId });

      const response = await fetch(
        `${API_BASE_URL}/api/cmm/delete/${analysisId}`,
        {
          method: "DELETE",
          headers: this.getJsonHeaders(),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ CMM analizi silindi:", { analysisId });

      return result;
    } catch (error: any) {
      console.error("❌ CMM analizi silme hatası:", error);
      throw error;
    }
  }

  // ============================================================================
  // CMM STATISTICS & INFO
  // ============================================================================

  /**
   * CMM istatistiklerini al
   */
  async getCMMStats(): Promise<CMMStatsResponse> {
    try {
      console.log("📊 CMM istatistikleri alınıyor...");

      const response = await fetch(`${API_BASE_URL}/api/cmm/stats`, {
        method: "GET",
        headers: this.getJsonHeaders(),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ CMM istatistikleri alındı:", {
        totalAnalyses: result.stats?.total_analyses,
        totalMeasurements: result.stats?.total_measurements,
      });

      return result;
    } catch (error: any) {
      console.error("❌ CMM istatistik hatası:", error);
      throw error;
    }
  }

  /**
   * Desteklenen dosya formatlarını al
   */
  async getSupportedFormats(): Promise<CMMSupportedFormatsResponse> {
    try {
      console.log("📋 CMM desteklenen formatlar alınıyor...");

      const response = await fetch(
        `${API_BASE_URL}/api/cmm/supported-formats`,
        {
          method: "GET",
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ CMM desteklenen formatlar alındı:", {
        formats: Object.keys(result.supported_formats || {}),
        maxFiles: result.max_files,
      });

      return result;
    } catch (error: any) {
      console.error("❌ CMM format bilgisi hatası:", error);
      throw error;
    }
  }

  // ============================================================================
  // CMM TESTING & DEBUG
  // ============================================================================

  /**
   * CMM parser'ı test et (admin/debug)
   */
  async testCMMParser(): Promise<{
    success: boolean;
    message: string;
    test_results?: {
      total_measurements: number;
      dataframe_rows: number;
      columns: string[];
      sample_data: any[];
      operations: string[];
    };
  }> {
    try {
      console.log("🧪 CMM parser test ediliyor...");

      const response = await fetch(`${API_BASE_URL}/api/cmm/test-parser`, {
        method: "POST",
        headers: this.getJsonHeaders(),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      console.log("✅ CMM parser test tamamlandı:", {
        success: result.success,
        measurementCount: result.test_results?.total_measurements,
      });

      return result;
    } catch (error: any) {
      console.error("❌ CMM parser test hatası:", error);
      throw error;
    }
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Dosya türü kontrolü
   */
  isValidCMMFile(file: File): boolean {
    return file.name.toLowerCase().endsWith(".rtf");
  }

  /**
   * Dosya boyutu kontrolü (max 10MB)
   */
  isValidFileSize(file: File): boolean {
    const maxSize = 10 * 1024 * 1024; // 10MB
    return file.size <= maxSize;
  }

  /**
   * Multiple dosya validasyonu
   */
  validateCMMFiles(files: File[]): {
    valid: File[];
    invalid: Array<{ file: File; reason: string }>;
  } {
    const valid: File[] = [];
    const invalid: Array<{ file: File; reason: string }> = [];

    files.forEach((file) => {
      if (!this.isValidCMMFile(file)) {
        invalid.push({ file, reason: "Sadece RTF dosyaları desteklenir" });
      } else if (!this.isValidFileSize(file)) {
        invalid.push({ file, reason: "Dosya boyutu 10MB'dan büyük olamaz" });
      } else {
        valid.push(file);
      }
    });

    return { valid, invalid };
  }

  /**
   * Excel dosyasını otomatik indir
   */
  async downloadAndSaveCMMExcel(analysisId: string): Promise<string> {
    try {
      const { blob, filename } = await this.downloadCMMExcel(analysisId);

      // Blob'u download et
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = filename;

      document.body.appendChild(a);
      a.click();

      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      console.log("✅ CMM Excel otomatik indirildi:", { filename });

      return filename;
    } catch (error: any) {
      console.error("❌ CMM Excel otomatik indirme hatası:", error);
      throw error;
    }
  }
}

export const cmmService = new CMMService();
