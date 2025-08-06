import React, { useState, useRef, useCallback } from 'react';
import { Upload, X, FileText, AlertCircle, CheckCircle } from 'lucide-react';

interface UploadedDoc {
  filename: string;
  status: 'uploading' | 'success' | 'error';
  message?: string;
  fileType?: string;
}

interface DocumentUploadProps {
  chatId: string;
  token: string | null;
  onDocumentsChange?: (documents: UploadedDoc[]) => void;
}

export function DocumentUpload({ chatId, token, onDocumentsChange }: DocumentUploadProps) {
  const [documents, setDocuments] = useState<UploadedDoc[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateDocuments = useCallback((newDocs: UploadedDoc[]) => {
    setDocuments(newDocs);
    onDocumentsChange?.(newDocs);
  }, [onDocumentsChange]);

  const handleFiles = async (files: FileList) => {
    const newFiles = Array.from(files);
    const supportedTypes = ['.pdf', '.docx', '.pptx', '.txt', '.csv'];
    
    // Add uploading status for new files
    const uploadingDocs = newFiles.map(file => ({
      filename: file.name,
      status: 'uploading' as const,
      fileType: file.name.split('.').pop()?.toLowerCase()
    }));
    
    updateDocuments([...documents, ...uploadingDocs]);

    // Create FormData for upload
    const formData = new FormData();
    newFiles.forEach(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (supportedTypes.includes(ext)) {
        formData.append('files', file);
      }
    });

    try {
      const headers: Record<string, string> = {};

      const response = await fetch(
        `${getBackendUrl()}/upload-files/${chatId}`,
        {
          method: 'POST',
          headers,
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Update document statuses based on server response
      const updatedDocs = documents.concat(
        result.processed_files.map((file: any) => ({
          filename: file.filename,
          status: file.status as 'success' | 'error',
          message: file.message,
          fileType: file.filename.split('.').pop()?.toLowerCase()
        }))
      );
      
      updateDocuments(updatedDocs);
    } catch (error) {
      // Mark all uploading files as error
      const errorDocs = documents.concat(
        uploadingDocs.map(doc => ({
          ...doc,
          status: 'error' as const,
          message: 'Upload failed'
        }))
      );
      updateDocuments(errorDocs);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  }, [documents, chatId, token]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(e.target.files);
    }
  };

  const removeDocument = async (filename: string) => {
    try {
      await fetch(
        `${getBackendUrl()}/chat-documents/${chatId}/${filename}`,
        { method: 'DELETE' }
      );
      updateDocuments(documents.filter(doc => doc.filename !== filename));
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
        return <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <FileText className="w-4 h-4 text-neutral-500" />;
    }
  };

  return (
    <div className="bg-white dark:bg-neutral-900 p-3 rounded-lg mb-2">
      <h3 className="text-responsive-base font-medium mb-3 text-neutral-700 dark:text-neutral-300">
        Chat Documents
      </h3>
      
      {documents.length === 0 ? (
        <div
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
            ${isDragging 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
              : 'border-neutral-300 dark:border-neutral-600 hover:border-neutral-400 dark:hover:border-neutral-500'
            }
          `}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleFileSelect}
        >
          <Upload className="w-8 h-8 mx-auto mb-2 text-neutral-400" />
          <p className="text-responsive-sm text-neutral-500 dark:text-neutral-400">
            Drop files here or click to upload
          </p>
          <p className="text-responsive-xs text-neutral-400 mt-1">
            Supports PDF, DOCX, PPTX, TXT, CSV
          </p>
        </div>
      ) : (
        <div 
          className={`
            grid grid-cols-1 gap-2 max-h-32 overflow-y-auto p-2 border-2 border-dashed rounded-lg
            ${isDragging 
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
              : 'border-neutral-200 dark:border-neutral-700'
            }
          `} 
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          {documents.map((doc, index) => (
            <div
              key={`${doc.filename}-${index}`}
              className="relative group bg-neutral-50 dark:bg-neutral-800 p-2 rounded border"
            >
              <div className="flex items-center space-x-2">
                {getStatusIcon(doc.status)}
                <div className="flex-1 min-w-0">
                  <p className="text-responsive-xs font-medium text-neutral-700 dark:text-neutral-300">
                    {doc.filename}
                  </p>
                  {doc.message && doc.status === 'error' && (
                    <p className="text-responsive-xs text-red-500">
                      {doc.message}
                    </p>
                  )}
                </div>
                {doc.status !== 'uploading' && (
                  <button
                    onClick={() => removeDocument(doc.filename)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded"
                  >
                    <X className="w-3 h-3 text-neutral-500" />
                  </button>
                )}
              </div>
            </div>
          ))}
          
          {/* Add more files button */}
          <div
            onClick={handleFileSelect}
            className="border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded p-2 flex items-center justify-center cursor-pointer hover:border-neutral-400 dark:hover:border-neutral-500 transition-colors"
          >
            <Upload className="w-4 h-4 text-neutral-400" />
          </div>
        </div>
      )}
      
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.pptx,.txt,.csv"
        onChange={handleFileInputChange}
        className="hidden"
      />
    </div>
  );
}