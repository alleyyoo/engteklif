import { useState, useCallback } from 'react';
import { apiService, FileUploadResponse, AnalysisResult } from '../services/api';

export interface UploadedFile {
  file: File;
  analysisId?: string;
  status: 'pending' | 'uploading' | 'uploaded' | 'analyzing' | 'completed' | 'failed';
  progress: number;
  error?: string;
  result?: AnalysisResult;
}

export const useFileUpload = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [totalProcessingTime, setTotalProcessingTime] = useState(0);

  const addFiles = useCallback((newFiles: File[]) => {
    const uploadedFiles: UploadedFile[] = newFiles.map(file => ({
      file,
      status: 'pending',
      progress: 0,
    }));
    setFiles(prev => [...prev, ...uploadedFiles]);
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
    setTotalProcessingTime(0);
  }, []);

  const updateFileStatus = useCallback((index: number, updates: Partial<UploadedFile>) => {
    setFiles(prev => prev.map((file, i) => i === index ? { ...file, ...updates } : file));
  }, []);

  const uploadAndAnalyze = useCallback(async () => {
    if (files.length === 0) return;

    // Sadece henüz işlenmemiş dosyaları al (pending durumunda olanlar)
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
      // Sadece pending dosyaları upload et
      for (const { file, index } of pendingFiles) {
        // Upload başlat
        updateFileStatus(index, { status: 'uploading', progress: 0 });

        try {
          // Dosyayı upload et
          const uploadResponse: FileUploadResponse = await apiService.uploadSingleFile(file.file);
          
          if (uploadResponse.success && uploadResponse.file_info) {
            updateFileStatus(index, { 
              status: 'uploaded', 
              progress: 50,
              analysisId: uploadResponse.file_info.analysis_id 
            });

            // Analizi başlat
            updateFileStatus(index, { status: 'analyzing', progress: 60 });

            const analysisResponse = await apiService.analyzeFile(uploadResponse.file_info.analysis_id);
            
            if (analysisResponse.success) {
              updateFileStatus(index, { 
                status: 'completed', 
                progress: 100,
                result: analysisResponse 
              });
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
  }, [files, updateFileStatus]);

  const retryFile = useCallback(async (index: number) => {
    const file = files[index];
    if (!file || file.status === 'uploading' || file.status === 'analyzing') return;

    updateFileStatus(index, { status: 'uploading', progress: 0, error: undefined });

    try {
      const uploadResponse = await apiService.uploadSingleFile(file.file);
      
      if (uploadResponse.success && uploadResponse.file_info) {
        updateFileStatus(index, { 
          status: 'uploaded', 
          progress: 50,
          analysisId: uploadResponse.file_info.analysis_id 
        });

        updateFileStatus(index, { status: 'analyzing', progress: 60 });

        const analysisResponse = await apiService.analyzeFile(uploadResponse.file_info.analysis_id);
        
        if (analysisResponse.success) {
          updateFileStatus(index, { 
            status: 'completed', 
            progress: 100,
            result: analysisResponse 
          });
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
  }, [files, updateFileStatus]);

  // ✅ ESKİ - Tek analiz Excel export (deprecated)
  const exportToExcel = useCallback(async (analysisId: string, fileName: string) => {
    try {
      const blob = await apiService.exportAnalysisExcel(analysisId);
      
      // Blob'u indir
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${fileName}_analysis.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Excel export failed:', error);
    }
  }, []);

  // ✅ YENİ - Çoklu analiz Excel export
  const exportMultipleToExcel = useCallback(async (analysisIds: string[], customFileName?: string) => {
    try {
      console.log('📊 Çoklu Excel export başlıyor...', {
        analysisCount: analysisIds.length,
        analysisIds: analysisIds
      });

      const result = await apiService.exportMultipleAnalysesExcel(analysisIds);
      
      if (result.success && result.blob) {
        // Blob'u indir
        const url = window.URL.createObjectURL(result.blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = customFileName || result.filename || `coklu_analiz_${analysisIds.length}_dosya.xlsx`;
        
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        console.log('✅ Çoklu Excel export başarılı:', {
          filename: a.download,
          blobSize: result.blob.size
        });

        return { success: true, filename: a.download };
      } else {
        throw new Error(result.message || 'Excel export başarısız');
      }
    } catch (error: any) {
      console.error('❌ Çoklu Excel export hatası:', error);
      return { success: false, error: error.message || 'Bilinmeyen hata' };
    }
  }, []);

  // ✅ Completed analizleri otomatik Excel export
  const exportAllCompletedToExcel = useCallback(async () => {
    const completedFiles = files.filter(f => 
      f.status === 'completed' && 
      f.result?.analysis?.id
    );

    if (completedFiles.length === 0) {
      console.warn('Export edilecek tamamlanmış analiz bulunamadı');
      return { success: false, error: 'Export edilecek analiz bulunamadı' };
    }

    const analysisIds = completedFiles.map(f => f.result!.analysis.id);
    
    console.log('📊 Tüm tamamlanmış analizleri Excel\'e export ediliyor...', {
      completedCount: completedFiles.length,
      fileNames: completedFiles.map(f => f.file.name)
    });

    return await exportMultipleToExcel(analysisIds, `tum_analizler_${Date.now()}.xlsx`);
  }, [files, exportMultipleToExcel]);

  return {
    files,
    isUploading,
    totalProcessingTime,
    addFiles,
    removeFile,
    clearFiles,
    uploadAndAnalyze,
    retryFile,
    exportToExcel, // Deprecated - geriye uyumluluk için
    exportMultipleToExcel, // ✅ YENİ - Ana export fonksiyonu
    exportAllCompletedToExcel, // ✅ YENİ - Otomatik tüm analizleri export
  };
};