"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import { ArrowLeft, FileText, CheckCircle2, AlertTriangle, Layers, Clock, Loader2, Sparkles } from "lucide-react";
import DocumentViewer from "@/components/DocumentViewer";
import ReconciliationPanel from "@/components/ReconciliationPanel";
import { getDossier } from "@/lib/api";
import { BoundingBox2D, DocumentDetail, DossierDetailResponse } from "@/lib/types";

export default function DossierDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const dossierId = resolvedParams.id;

  const [dossier, setDossier] = useState<DossierDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocIndex, setSelectedDocIndex] = useState(0);
  const [activeBbox, setActiveBbox] = useState<BoundingBox2D | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await getDossier(dossierId);
        setDossier(data);
      } catch (err: any) {
        setError(err.message || "Error al cargar el expediente");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [dossierId]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
        <p className="text-sm text-gray-400 font-medium">Cargando expediente contable...</p>
      </div>
    );
  }

  if (error || !dossier) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="h-12 w-12 rounded-xl bg-rose-500/10 text-rose-400 mx-auto flex items-center justify-center">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold text-white">No se pudo cargar el expediente</h2>
        <p className="text-sm text-gray-400">{error || "Expediente no encontrado en el sistema"}</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs font-semibold"
        >
          <ArrowLeft className="h-4 w-4" />
          Volver al Inicio
        </Link>
      </div>
    );
  }

  const activeDocument: DocumentDetail | undefined = dossier.documents[selectedDocIndex];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 hover:bg-gray-800/80 rounded-xl text-gray-400 hover:text-white transition border border-gray-800"
            title="Volver"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-white tracking-tight">{dossier.title}</h1>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold ${
                  dossier.status === "RECONCILED"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                }`}
              >
                {dossier.status}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5 font-mono">ID: {dossier.id}</p>
          </div>
        </div>

        {/* Document Tabs */}
        {dossier.documents.length > 0 && (
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-800 p-1 rounded-xl">
            {dossier.documents.map((doc, idx) => (
              <button
                key={doc.id}
                onClick={() => {
                  setSelectedDocIndex(idx);
                  setActiveBbox(null);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                  selectedDocIndex === idx
                    ? "bg-blue-600 text-white shadow"
                    : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                <span>{doc.doc_type}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Split Pane Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Pane: Interactive SVG Document Viewer (7 cols) */}
        <div className="lg:col-span-7 h-[700px] sticky top-20">
          {activeDocument ? (
            <DocumentViewer
              dossierId={dossier.id}
              document={activeDocument}
              activeBbox={activeBbox}
              onSelectEntity={(_, bbox) => setActiveBbox(bbox)}
            />
          ) : (
            <div className="h-full flex items-center justify-center bg-[#111827] border border-gray-800 rounded-2xl text-gray-500 text-sm">
              No hay documentos cargados en este expediente.
            </div>
          )}
        </div>

        {/* Right Pane: 3-Way Reconciler & Extracted Data Tables (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* 3-Way Reconciliation Results Card */}
          <ReconciliationPanel reconciliation={dossier.reconciliation} status={dossier.status} />

          {/* Active Document Extractions & Items */}
          {activeDocument && (
            <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 shadow-xl space-y-6">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">
                  Entidades Extraídas ({activeDocument.doc_type})
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Pasa el cursor o haz clic en cualquier campo para resaltar su caja espacial en el visor.
                </p>
              </div>

              {/* Header Fields Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                {activeDocument.extractions.map((ext, idx) => (
                  <div
                    key={idx}
                    onMouseEnter={() => ext.bbox && setActiveBbox(ext.bbox)}
                    onMouseLeave={() => setActiveBbox(null)}
                    onClick={() => ext.bbox && setActiveBbox(ext.bbox)}
                    className="p-3 bg-[#1e293b]/40 hover:bg-blue-500/10 border border-gray-800 hover:border-blue-500/40 rounded-xl cursor-pointer transition"
                  >
                    <span className="text-[10px] font-mono text-gray-400 block uppercase">{ext.field_name}</span>
                    <span className="text-gray-100 font-semibold block mt-0.5 truncate">{ext.field_value}</span>
                  </div>
                ))}
              </div>

              {/* Line Items Table */}
              {activeDocument.line_items.length > 0 && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-400">
                      Líneas de Ítems ({activeDocument.line_items.length})
                    </h4>
                    <span className="text-[10px] text-gray-500">Sincronizado con SVG</span>
                  </div>

                  <div className="border border-gray-800 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-[#1e293b]/80 border-b border-gray-800 text-gray-400 uppercase font-mono text-[10px]">
                        <tr>
                          <th className="py-2.5 px-3">Descripción</th>
                          <th className="py-2.5 px-2 text-right">Cant.</th>
                          <th className="py-2.5 px-2 text-right">P. Unit</th>
                          <th className="py-2.5 px-3 text-right">Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800/60 font-mono">
                        {activeDocument.line_items.map((item, idx) => (
                          <tr
                            key={idx}
                            onMouseEnter={() => item.bbox && setActiveBbox(item.bbox)}
                            onMouseLeave={() => setActiveBbox(null)}
                            onClick={() => item.bbox && setActiveBbox(item.bbox)}
                            className="hover:bg-amber-400/10 cursor-pointer transition"
                          >
                            <td className="py-2 px-3 text-gray-200 font-sans text-xs">{item.description}</td>
                            <td className="py-2 px-2 text-right text-gray-300">{item.quantity}</td>
                            <td className="py-2 px-2 text-right text-gray-300">S/ {item.unit_price.toFixed(2)}</td>
                            <td className="py-2 px-3 text-right font-bold text-emerald-400">
                              S/ {item.line_total.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
