import React, { useState, useEffect, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';
import { api } from '../api';
import type { CleaningReport } from '../types';

interface FileUploaderProps {
  onUploadSuccess: () => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

const PIPELINE_MESSAGES = [
  'Uploading spreadsheet workbook to server...',
  'Parsing workbook and resolving sheet dimensions...',
  'Executing Python cleaning pipeline (pandas)...',
  'Removing exact duplicate rows (48 expected)...',
  'Removing non-product administrative records ("DUMMY" & GROUP INCOME/EXPENSE)...',
  'Flagging product returns and zero-sales...',
  'Re-calculating cumulative product sales revenue...',
  'Performing chain-wide ABC classification...',
  'Caching cleaned store index maps in memory...',
  'Sanitizing data schemas. Almost finished...',
];

export const FileUploader: React.FC<FileUploaderProps> = ({
  onUploadSuccess,
  isLoading,
  setIsLoading,
}) => {
  const [error, setError] = useState<string | null>(null);
  const [successReport, setSuccessReport] = useState<CleaningReport | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [progressMsgIndex, setProgressMsgIndex] = useState<number>(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cycle through messages while pipeline is running
  useEffect(() => {
    let interval: number;
    if (isLoading) {
      setProgressMsgIndex(0);
      interval = window.setInterval(() => {
        setProgressMsgIndex((prev) => (prev + 1) % PIPELINE_MESSAGES.length);
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLoading]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await processFile(e.target.files[0]);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const processFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      setError('Invalid file type. Only Excel sheets (.xlsx) are allowed.');
      return;
    }

    setError(null);
    setSuccessReport(null);
    setIsLoading(true);

    try {
      const res = await api.uploadDataset(file);
      setSuccessReport(res.cleaning);
      onUploadSuccess();
    } catch (err: any) {
      console.error('File upload failed:', err);
      setError(err.message || 'An error occurred during dataset compilation.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-[#0f172a]/60 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-xs flex flex-col justify-center animate-fade-in h-full">
      <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4 pb-2 border-b border-slate-800/60 flex items-center gap-2">
        <Upload className="w-4 h-4 text-blue-400" />
        Upload New Dataset
      </h2>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-8 py-10 text-center border-2 border-dashed border-blue-500/30 rounded-lg bg-blue-950/5 h-64">
          <RefreshCw className="w-10 h-10 text-blue-400 animate-spin mb-4" />
          <h3 className="text-sm font-semibold text-slate-200 mb-1">Running ETL Pipeline...</h3>
          <p className="text-xs text-slate-400 max-w-xs h-10 flex items-center justify-center">
            {PIPELINE_MESSAGES[progressMsgIndex]}
          </p>
          <div className="w-48 bg-slate-800 h-1.5 rounded-full overflow-hidden mt-3 border border-slate-700">
            <div className="bg-blue-500 h-full rounded-full animate-pulse" style={{ width: '60%' }}></div>
          </div>
          <span className="text-[10px] text-slate-500 mt-2">Expected run time: 25 - 30 seconds</span>
        </div>
      ) : (
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={triggerFileInput}
          className={`flex flex-col items-center justify-center p-8 text-center border-2 border-dashed rounded-lg cursor-pointer h-64 transition-all ${
            dragActive
              ? 'border-blue-500 bg-blue-950/20 shadow-blue-500/10'
              : 'border-slate-700 bg-slate-900/30 hover:border-slate-500 hover:bg-slate-900/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleChange}
            accept=".xlsx"
            className="hidden"
          />
          <Upload className="w-10 h-10 text-slate-500 mb-4 transition-colors group-hover:text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-200 mb-1">
            Drag &amp; drop your sales workbook here
          </h3>
          <p className="text-xs text-slate-400 mb-3">
            Supports Microsoft Excel spreadsheet files (.xlsx)
          </p>
          <span className="px-3 py-1 bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold rounded-md hover:bg-slate-700">
            Select Excel File
          </span>
        </div>
      )}

      {/* Success Notification */}
      {successReport && !isLoading && (
        <div className="mt-4 flex gap-3 p-3 bg-emerald-950/20 border border-emerald-900/50 text-emerald-400 rounded-lg text-xs leading-relaxed animate-fade-in">
          <CheckCircle2 className="w-4.5 h-4.5 shrink-0 text-emerald-400" />
          <div>
            <strong className="block font-bold">ETL pipeline finished successfully!</strong>
            <span className="block mt-0.5 text-slate-300">
              Loaded {successReport.rows_after.toLocaleString()} product rows and compiled {successReport.unique_shops} shops.
            </span>
          </div>
        </div>
      )}

      {/* Error Notification */}
      {error && !isLoading && (
        <div className="mt-4 flex gap-3 p-3 bg-red-950/20 border border-red-900/50 text-red-400 rounded-lg text-xs leading-relaxed animate-fade-in">
          <AlertCircle className="w-4.5 h-4.5 shrink-0 text-red-400" />
          <div>
            <strong className="block font-bold">Data Import Failed</strong>
            <span className="block mt-0.5 text-slate-300">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
};
