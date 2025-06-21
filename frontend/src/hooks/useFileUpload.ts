// src/hooks/useFileUpload.ts
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
  };
};