"use client";

import React, { useState, useRef } from "react";
import { Upload, FileUp, X, CheckCircle, AlertTriangle, Loader2, ArrowRight } from "lucide-react";
import { uploadDossier } from "@/lib/api";
import { DossierUploadResponse } from "@/lib/types";

interface Props {
  onDossierUploaded: (dossierId: string) => void;
}

export default function DossierUpload({ onDossierUploaded }: Props) {
  const [title, setTitle] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DossierUploadResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (newFiles: File[]) => {
    const valid = newFiles.filter(
      (f) =>
        f.type.includes("pdf") ||
        f.type.includes("image") ||
        f.name.endsWith(".pdf") ||
        f.name.endsWith(".png") ||
        f.name.endsWith(".jpg") ||
        f.name.endsWith(".jpeg")
    );
    setFiles((prev) => [...prev, ...valid]);
    if (!title && valid.length > 0) {
      const baseName = valid[0].name.replace(/\.[^/.]+$/, "");
      setTitle(`Expediente - ${baseName}`);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || files.length === 0) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await uploadDossier(title, files);
      setResult(res);
      onDossierUploaded(res.dossier_id);
    } catch (err: any) {
      setError(err.message || "Error al procesar el expediente");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 sm:p-8 shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Cargar Expediente Contable</h2>
          <p className="text-sm text-gray-400 mt-1">
            Sube los comprobantes (Factura comercial, Guías de remisión y Vouchers de pago) para cotejo de 3 vías.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title input */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-300 mb-2">
            Título del Expediente
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ej. Factura F001-0008492 - Proveedor Industrial"
            required
            className="w-full bg-[#1e293b]/60 border border-gray-700 hover:border-gray-600 focus:border-blue-500 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition"
          />
        </div>

        {/* Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition flex flex-col items-center justify-center ${
            isDragging
              ? "border-blue-500 bg-blue-500/10"
              : "border-gray-700 hover:border-gray-600 bg-[#1e293b]/30 hover:bg-[#1e293b]/50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={handleFileChange}
            className="hidden"
          />
          <div className="h-12 w-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-4">
            <FileUp className="h-6 w-6" />
          </div>
          <p className="text-sm font-medium text-white">
            Arrastra y suelta tus documentos aquí, o <span className="text-blue-400 underline">haz clic para examinar</span>
          </p>
          <p className="text-xs text-gray-400 mt-1">Soporta PDF multipágina, imágenes PNG y JPEG de alta resolución</p>
        </div>

        {/* Files list */}
        {files.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Documentos adjuntos ({files.length})
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {files.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 bg-[#1e293b]/60 border border-gray-800 rounded-xl"
                >
                  <div className="truncate mr-2">
                    <p className="text-xs font-medium text-gray-200 truncate">{file.name}</p>
                    <p className="text-[10px] text-gray-400 font-mono">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(idx);
                    }}
                    className="p-1 hover:bg-gray-700/60 rounded text-gray-400 hover:text-white"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error alert */}
        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-center gap-3 text-rose-400 text-sm">
            <AlertTriangle className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Action Button */}
        <button
          type="submit"
          disabled={loading || files.length === 0 || !title.trim()}
          className="w-full py-3.5 px-6 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition shadow-lg shadow-blue-600/20"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Ejecutando OCR en GPU y Conciliación de 3 Vías...</span>
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              <span>Procesar Expediente Completo</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
