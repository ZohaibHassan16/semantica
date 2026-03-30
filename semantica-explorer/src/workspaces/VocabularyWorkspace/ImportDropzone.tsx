import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, CheckCircle2, Loader2 } from 'lucide-react';
import { useImportVocabulary } from './queries';
import type { ImportResponse } from './types'; 

export const ImportDropzone: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);
  const importMutation = useImportVocabulary();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      setFile(selectedFile);
      setImportResult(null);

      importMutation.mutate(selectedFile, {
        onSuccess: (data) => {
          setImportResult(data); 
          setTimeout(() => {
            setFile(null);
            setImportResult(null);
          }, 4000); 
        },
        onError: (err) => {
          console.error("Upload failed:", err);
          setFile(null);
        }
      });
    }
  }, [importMutation]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/turtle': ['.ttl'],
      'application/rdf+xml': ['.rdf', '.owl']
    },
    maxFiles: 1
  });

  return (
    <div style={{ marginTop: '20px' }}>
      <div 
        {...getRootProps()} 
        style={{
          border: `2px dashed ${isDragActive ? '#3b82f6' : '#d1d5db'}`,
          backgroundColor: isDragActive ? '#eff6ff' : '#f9fafb',
          borderRadius: '6px',
          padding: '24px 16px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }}
      >
        <input {...getInputProps()} />
        
        {importMutation.isPending ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#6b7280' }}>
            <Loader2 className="animate-spin" size={24} style={{ marginBottom: '8px' }} />
            <span style={{ fontSize: '14px' }}>Uploading {file?.name}...</span>
          </div>
        ) : importResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#10b981' }}>
            <CheckCircle2 size={24} style={{ marginBottom: '8px' }} />
            <span style={{ fontSize: '14px', fontWeight: 500 }}>Import Successful!</span>
            <span style={{ fontSize: '12px', marginTop: '4px', color: '#059669' }}>
              Added {importResult.nodes_added} concepts & {importResult.edges_added} links.
            </span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', color: '#6b7280' }}>
            <UploadCloud size={24} style={{ marginBottom: '8px', color: isDragActive ? '#3b82f6' : '#9ca3af' }} />
            <span style={{ fontSize: '14px', fontWeight: 500, color: '#374151' }}>
              {isDragActive ? "Drop file here..." : "Import Vocabulary"}
            </span>
            <span style={{ fontSize: '12px', marginTop: '4px' }}>Drag & drop .ttl or .rdf</span>
          </div>
        )}
      </div>
      {importMutation.isError && (
        <p style={{ color: '#ef4444', fontSize: '12px', marginTop: '8px', textAlign: 'center' }}>
          Upload failed. Check console.
        </p>
      )}
    </div>
  );
};