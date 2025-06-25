import { useEffect, useState, useCallback, useRef } from "react";
import {
  apiService,
  FileUploadResponse,
  AnalysisResult,
  RenderStatusResponse,
} from "../services/api";

export interface UploadedFile {
  file: File;
  analysisId?: string;
  status:
    | "pending"
    | "uploading"
    | "uploaded"
    | "analyzing"
    | "completed"
    | "failed";
  progress: number;
  error?: string;
  result?: AnalysisResult;
  renderStatus?: "none" | "pending" | "processing" | "completed" | "failed";
  renderCheckInterval?: NodeJS.Timer;
}

export const useFileUpload = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [totalProcessingTime, setTotalProcessingTime] = useState(0);
  
  // Interval'leri takip etmek için ref kullan
  const intervalsRef = useRef<Map<string, NodeJS.Timer>>(new Map());

  // Interval temizleme fonksiyonu
  const clearRenderInterval = useCallback((analysisId: string) => {
    const interval = intervalsRef.current.get(analysisId);
    if (interval) {
      clearInterval(interval);
      intervalsRef.current.delete(analysisId);
      console.log(`🧹 Interval temizlendi: ${analysisId}`);
    }
  }, []);

  // Tüm interval'leri temizle
  const clearAllIntervals = useCallback(() => {
    intervalsRef.current.forEach((interval, analysisId) => {
      clearInterval(interval);
      console.log(`🧹 Interval temizlendi: ${analysisId}`);
    });
    intervalsRef.current.clear();
  }, []);

  const checkRenderStatus = useCallback(async (analysisId: string, fileIndex: number) => {
    try {
      const response: RenderStatusResponse = await apiService.getRenderStatus(analysisId);
      
      if (response.success) {
        setFiles(prev => {
          const newFiles = [...prev];
          const file = newFiles[fileIndex];
          
          if (!file) {
            // Dosya artık listede değilse interval'i temizle
            clearRenderInterval(analysisId);
            return prev;
          }
          
          // Render tamamlandıysa
          if (response.render_status === 'completed') {
            clearRenderInterval(analysisId);
            console.log(`✅ Render tamamlandı: ${analysisId}`);
            
            // Analiz sonuçlarını güncelle
            if (file.result && file.result.analysis) {
              if (response.stl_generated !== undefined) {
                file.result.analysis.stl_generated = response.stl_generated;
              }
              
              if (response.stl_path) {
                file.result.analysis.stl_path = response.stl_path;
              }
              
              file.result.analysis.render_status = 'completed';
              
              // ✅ Render sonuçlarını enhanced_renders'a ekle
              if (response.renders && file.result) {
                file.result.analysis.enhanced_renders = {};
                
                // Her render'ı dönüştür
                Object.entries(response.renders).forEach(([viewType, renderData]) => {
                  if (file.result && file.result.analysis.enhanced_renders) {
                    file.result.analysis.enhanced_renders[viewType] = {
                      success: true,
                      view_type: viewType,
                      file_path: renderData.file_path,
                      excel_path: renderData.excel_path || undefined,
                      svg_path: undefined // API'den svg_path gelmiyor
                    };
                  }
                });
                
                console.log(`✅ Enhanced renders güncellendi:`, file.result.analysis.enhanced_renders);
              }
            }
            
            newFiles[fileIndex] = {
              ...file,
              renderStatus: 'completed',
              renderCheckInterval: undefined
            };
          }
          // Render başarısız olduysa
          else if (response.render_status === 'failed') {
            clearRenderInterval(analysisId);
            console.log(`❌ Render başarısız: ${analysisId}`);
            
            if (file.result && file.result.analysis) {
              file.result.analysis.render_status = 'failed';
            }
            
            newFiles[fileIndex] = {
              ...file,
              renderStatus: 'failed',
              renderCheckInterval: undefined
            };
          }
          // Hala işleniyorsa sadece durumu güncelle
          else if (response.render_status === 'processing') {
            newFiles[fileIndex] = {
              ...file,
              renderStatus: 'processing'
            };
          }
          
          return newFiles;
        });
      }
    } catch (error) {
      console.error('Render status check failed:', error);
      // Hata durumunda da interval'i temizlemeyi düşünebilirsiniz
      // clearRenderInterval(analysisId);
    }
  }, [clearRenderInterval]);

  const addFiles = useCallback((newFiles: File[]) => {
    const uploadedFiles: UploadedFile[] = newFiles.map((file) => ({
      file,
      status: "pending",
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...uploadedFiles]);
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => {
      const fileToRemove = prev[index];
      // Dosya silinirken interval'ini de temizle
      if (fileToRemove?.analysisId) {
        clearRenderInterval(fileToRemove.analysisId);
      }
      return prev.filter((_, i) => i !== index);
    });
  }, [clearRenderInterval]);

  const clearFiles = useCallback(() => {
    // Tüm dosyaları temizlerken tüm interval'leri de temizle
    clearAllIntervals();
    setFiles([]);
    setTotalProcessingTime(0);
  }, [clearAllIntervals]);

  const updateFileStatus = useCallback(
    (index: number, updates: Partial<UploadedFile>) => {
      setFiles((prev) =>
        prev.map((file, i) => (i === index ? { ...file, ...updates } : file))
      );
    },
    []
  );

  const startRenderStatusCheck = useCallback((analysisId: string, fileIndex: number) => {
    // Önce eski interval'i temizle (eğer varsa)
    clearRenderInterval(analysisId);
    
    console.log(`🎨 Render status kontrolü başlatılıyor: ${analysisId}`);
    
    const interval = setInterval(() => {
      // Her interval çalıştığında dosyanın hala var olup olmadığını kontrol et
      setFiles(currentFiles => {
        if (!currentFiles[fileIndex] || currentFiles[fileIndex].analysisId !== analysisId) {
          clearRenderInterval(analysisId);
          return currentFiles;
        }
        return currentFiles;
      });
      
      checkRenderStatus(analysisId, fileIndex);
    }, 3000);
    
    // Interval'i ref'e kaydet
    intervalsRef.current.set(analysisId, interval);
    
    // State'e de kaydet (opsiyonel, UI'da göstermek için)
    setFiles(prev => prev.map((f, i) => 
      i === fileIndex ? { ...f, renderCheckInterval: interval } : f
    ));
  }, [checkRenderStatus, clearRenderInterval]);

  const uploadAndAnalyze = useCallback(async () => {
    if (files.length === 0) return;

    const pendingFiles = files
      .map((file, index) => ({ file, index }))
      .filter(({ file }) => file.status === 'pending');

    if (pendingFiles.length === 0) {
      console.log('Tüm dosyalar zaten işlenmiş veya işleniyor');
      return;
    }

    setIsUploading(true);
    const startTime = Date.now();

    try {
      for (const { file, index } of pendingFiles) {
        updateFileStatus(index, { status: 'uploading', progress: 0 });

        try {
          const uploadResponse: FileUploadResponse = await apiService.uploadSingleFile(file.file);
          
          if (uploadResponse.success && uploadResponse.file_info) {
            const analysisId = uploadResponse.file_info.analysis_id;
            
            updateFileStatus(index, { 
              status: 'uploaded', 
              progress: 50,
              analysisId: analysisId 
            });

            updateFileStatus(index, { status: 'analyzing', progress: 60 });

            const analysisResponse = await apiService.analyzeFile(analysisId);
            
            if (analysisResponse.success) {
              updateFileStatus(index, { 
                status: 'completed', 
                progress: 100,
                result: analysisResponse,
                renderStatus: analysisResponse.render_status || 'none'
              });
              
              // Render işlemi devam ediyorsa, periyodik kontrol başlat
              if (analysisResponse.render_status !== 'completed' && analysisResponse.render_status !== 'failed') {
                startRenderStatusCheck(analysisId, index);
              }
            } else {
              updateFileStatus(index, { 
                status: 'failed', 
                progress: 0,
                error: analysisResponse.message || 'Analiz başarısız' 
              });
            }
          } else {
            updateFileStatus(index, { 
              status: 'failed', 
              progress: 0,
              error: uploadResponse.message || 'Upload başarısız' 
            });
          }
        } catch (error) {
          updateFileStatus(index, { 
            status: 'failed', 
            progress: 0,
            error: error instanceof Error ? error.message : 'Bilinmeyen hata' 
          });
        }
      }

      const endTime = Date.now();
      setTotalProcessingTime((endTime - startTime) / 1000);
    } finally {
      setIsUploading(false);
    }
  }, [files, updateFileStatus, startRenderStatusCheck]);

  const retryFile = useCallback(
    async (index: number) => {
      const file = files[index];
      if (!file || file.status === "uploading" || file.status === "analyzing")
        return;

      // Retry yaparken eski interval'i temizle
      if (file.analysisId) {
        clearRenderInterval(file.analysisId);
      }

      updateFileStatus(index, {
        status: "uploading",
        progress: 0,
        error: undefined,
      });

      try {
        const uploadResponse = await apiService.uploadSingleFile(file.file);

        if (uploadResponse.success && uploadResponse.file_info) {
          const analysisId = uploadResponse.file_info.analysis_id;
          
          updateFileStatus(index, {
            status: "uploaded",
            progress: 50,
            analysisId: analysisId,
          });

          updateFileStatus(index, { status: "analyzing", progress: 60 });

          const analysisResponse = await apiService.analyzeFile(analysisId);

          if (analysisResponse.success) {
            updateFileStatus(index, {
              status: "completed",
              progress: 100,
              result: analysisResponse,
              renderStatus: analysisResponse.render_status || 'none'
            });
            
            // Render işlemi devam ediyorsa, periyodik kontrol başlat
            if (analysisResponse.render_status !== 'completed' && analysisResponse.render_status !== 'failed') {
              startRenderStatusCheck(analysisId, index);
            }
          } else {
            updateFileStatus(index, {
              status: "failed",
              progress: 0,
              error: analysisResponse.message || "Analiz başarısız",
            });
          }
        } else {
          updateFileStatus(index, {
            status: "failed",
            progress: 0,
            error: uploadResponse.message || "Upload başarısız",
          });
        }
      } catch (error) {
        updateFileStatus(index, {
          status: "failed",
          progress: 0,
          error: error instanceof Error ? error.message : "Bilinmeyen hata",
        });
      }
    },
    [files, updateFileStatus, clearRenderInterval, startRenderStatusCheck]
  );

  const exportToExcel = useCallback(
    async (analysisId: string, fileName: string) => {
      try {
        const blob = await apiService.exportAnalysisExcel(analysisId);

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${fileName}_analysis.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (error) {
        console.error("Excel export failed:", error);
      }
    },
    []
  );

  const exportMultipleToExcel = useCallback(
    async (analysisIds: string[], customFileName?: string) => {
      try {
        console.log("📊 Çoklu Excel export başlıyor...", {
          analysisCount: analysisIds.length,
          analysisIds: analysisIds,
        });

        const result = await apiService.exportMultipleAnalysesExcel(
          analysisIds
        );

        if (result.success && result.blob) {
          const url = window.URL.createObjectURL(result.blob);
          const a = document.createElement("a");
          a.style.display = "none";
          a.href = url;
          a.download =
            customFileName ||
            result.filename ||
            `coklu_analiz_${analysisIds.length}_dosya.xlsx`;

          document.body.appendChild(a);
          a.click();

          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);

          console.log("✅ Çoklu Excel export başarılı:", {
            filename: a.download,
            blobSize: result.blob.size,
          });

          return { success: true, filename: a.download };
        } else {
          throw new Error(result.message || "Excel export başarısız");
        }
      } catch (error: any) {
        console.error("❌ Çoklu Excel export hatası:", error);
        return { success: false, error: error.message || "Bilinmeyen hata" };
      }
    },
    []
  );

  const exportAllCompletedToExcel = useCallback(async () => {
    const completedFiles = files.filter(
      (f) => f.status === "completed" && f.result?.analysis?.id
    );

    if (completedFiles.length === 0) {
      console.warn("Export edilecek tamamlanmış analiz bulunamadı");
      return { success: false, error: "Export edilecek analiz bulunamadı" };
    }

    const analysisIds = completedFiles.map((f) => f.result!.analysis.id);

    console.log("📊 Tüm tamamlanmış analizleri Excel'e export ediliyor...", {
      completedCount: completedFiles.length,
      fileNames: completedFiles.map((f) => f.file.name),
    });

    return await exportMultipleToExcel(
      analysisIds,
      `tum_analizler_${Date.now()}.xlsx`
    );
  }, [files, exportMultipleToExcel]);

  // Component unmount olduğunda tüm interval'leri temizle
  useEffect(() => {
    return () => {
      clearAllIntervals();
    };
  }, [clearAllIntervals]);

  return {
    files,
    isUploading,
    totalProcessingTime,
    addFiles,
    removeFile,
    clearFiles,
    uploadAndAnalyze,
    retryFile,
    exportToExcel,
    exportMultipleToExcel,
    exportAllCompletedToExcel,
  };
};