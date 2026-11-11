"use client";

import React, { useState, useRef, useId } from "react";
import { Upload, FileUp, X, CheckCircle2, AlertTriangle, Loader2, FileCheck2 } from "lucide-react";
import { uploadDossier } from "@/lib/api";
import { DossierUploadResponse } from "@/lib/types";

interface Props {
  onDossierUploaded: (dossierId: string) => void;
}

export default function DossierUpload({ onDossierUploaded }: Props) {
  const titleInputId = useId();
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
        f.name.toLowerCase().endsWith(".pdf") ||
        f.name.toLowerCase().endsWith(".png") ||
        f.name.toLowerCase().endsWith(".jpg") ||
        f.name.toLowerCase().endsWith(".jpeg")
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

  const lowerNames = files.map((f) => f.name.toLowerCase());
  const hasInvoice = lowerNames.some((n) => n.includes("fact") || n.includes("inv") || n.includes("f001")) || files.length >= 1;
  const hasGuide = lowerNames.some((n) => n.includes("guia") || n.includes("remis") || n.includes("t001")) || files.length >= 2;
  const hasVoucher = lowerNames.some((n) => n.includes("vouch") || n.includes("pago") || n.includes("bcp") || n.includes("banc")) || files.length >= 3;

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
    <section id="nuevo-expediente" className="surface-card p-5 sm:p-6" aria-labelledby="upload-section-heading">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-zinc-800/80">
        <div>
          <h2 id="upload-section-heading" className="text-sm font-semibold text-zinc-100">
            Cargar Comprobantes para Conciliación
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Adjunta la Factura, Guía de Remisión y Voucher de Pago del expediente.
          </p>
        </div>

        {/* Clean 3-Document Checklist */}
        <div className="flex flex-wrap items-center gap-1.5 text-[0.7rem]" aria-label="Comprobantes detectados">
          <span
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border ${
              hasInvoice
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                : "bg-zinc-900 border-zinc-800 text-zinc-500"
            }`}
          >
            <span>Factura</span>
            {hasInvoice && <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />}
          </span>
          <span
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border ${
              hasGuide
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                : "bg-zinc-900 border-zinc-800 text-zinc-500"
            }`}
          >
            <span>Guía</span>
            {hasGuide && <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />}
          </span>
          <span
            className={`inline-flex items-center gap-1 px-2 py-1 rounded-md border ${
              hasVoucher
                ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                : "bg-zinc-900 border-zinc-800 text-zinc-500"
            }`}
          >
            <span>Voucher</span>
            {hasVoucher && <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />}
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor={titleInputId}
            className="block text-xs font-medium text-zinc-300 mb-1.5"
          >
            Glosa o Referencia
          </label>
          <input
            id={titleInputId}
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ej. OC-2026-098 • Corporación Industrial Ferretera"
            required
            className="w-full bg-[#0b0b0d] border border-zinc-800 hover:border-zinc-700 focus:border-amber-500/70 rounded-lg px-3.5 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none transition"
          />
        </div>

        {/* Dropzone */}
        <div
          role="button"
          tabIndex={0}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          className={`border border-dashed rounded-xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center focus:outline-none focus:ring-1 focus:ring-amber-500/50 ${
            isDragging
              ? "border-amber-500 bg-amber-500/5"
              : "border-zinc-800 hover:border-zinc-700 bg-[#0b0b0d]/60 hover:bg-[#0b0b0d]"
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
          <div className="min-h-[2.5rem] min-w-[2.5rem] rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-amber-400 mb-2.5">
            <FileUp className="h-4 w-4" aria-hidden="true" />
          </div>
          <p className="text-xs sm:text-sm font-medium text-zinc-200">
            Arrastra los archivos aquí o <span className="text-amber-400 underline underline-offset-4">examina tu equipo</span>
          </p>
          <p className="text-[0.7rem] text-zinc-500 mt-1">
            PDF, PNG o JPEG (máx. 25 MB por archivo)
          </p>
        </div>

        {/* Files list */}
        {files.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-zinc-400">
                Archivos adjuntos ({files.length})
              </p>
              <button
                type="button"
                onClick={() => setFiles([])}
                className="text-xs text-zinc-500 hover:text-rose-400 transition"
              >
                Limpiar
              </button>
            </div>
            <ul className="grid grid-cols-1 gap-1.5">
              {files.map((file, idx) => (
                <li
                  key={`${file.name}-${idx}`}
                  className="flex items-center justify-between px-3 py-2 bg-[#0b0b0d] border border-zinc-800/90 rounded-lg"
                >
                  <div className="flex items-center gap-2 min-w-0 mr-2">
                    <FileCheck2 className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" aria-hidden="true" />
                    <span className="text-xs text-zinc-200 truncate">{file.name}</span>
                    <span className="text-[0.65rem] text-zinc-500 font-mono flex-shrink-0">
                      {(file.size / 1024).toFixed(0)} KB
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(idx);
                    }}
                    aria-label={`Quitar archivo ${file.name}`}
                    className="p-1 hover:bg-zinc-800 rounded text-zinc-500 hover:text-rose-400 transition"
                  >
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="p-3 bg-rose-500/10 border border-rose-500/25 rounded-lg flex items-center gap-2.5 text-rose-300 text-xs"
          >
            <AlertTriangle className="h-4 w-4 flex-shrink-0 text-rose-400" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/25 rounded-lg flex items-center justify-between gap-2 text-xs text-emerald-200">
            <div className="flex items-center gap-2 min-w-0">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" aria-hidden="true" />
              <span className="truncate font-medium">{result.title} procesado</span>
            </div>
            <span className="font-mono text-[0.68rem] px-2 py-0.5 rounded bg-zinc-900 text-zinc-200">
              {result.status}
            </span>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || files.length === 0 || !title.trim()}
          className="w-full py-2.5 px-4 bg-zinc-100 hover:not(:disabled):bg-white disabled:bg-zinc-900 disabled:text-zinc-600 text-zinc-950 rounded-lg font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 transition"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              <span>Procesando comprobantes...</span>
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" aria-hidden="true" />
              <span>Ejecutar Conciliación ({files.length})</span>
            </>
          )}
        </button>
      </form>
    </section>
  );
}
