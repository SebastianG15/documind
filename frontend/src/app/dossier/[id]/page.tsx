"use client";

import React, { useEffect, useState, useRef, use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Copy,
  Check,
  Printer,
} from "lucide-react";
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
  const [pinnedBbox, setPinnedBbox] = useState<BoundingBox2D | null>(null);
  const [hoveredBbox, setHoveredBbox] = useState<BoundingBox2D | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const panelHeadingRef = useRef<HTMLHeadingElement>(null);

  const activeBbox = hoveredBbox || pinnedBbox;

  const isSameBbox = (a?: BoundingBox2D | null, b?: BoundingBox2D | null) => {
    if (!a || !b) return false;
    return a.ymin === b.ymin && a.xmin === b.xmin && a.ymax === b.ymax && a.xmax === b.xmax;
  };

  const handleTogglePinBbox = (bbox?: BoundingBox2D | null) => {
    if (!bbox) return;
    setPinnedBbox((prev) => (isSameBbox(prev, bbox) ? null : bbox));
  };

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

  const handleSelectDocumentTab = (idx: number, e: React.MouseEvent<HTMLButtonElement>) => {
    const btn = e.currentTarget;
    const updateTab = () => {
      setSelectedDocIndex(idx);
      setPinnedBbox(null);
      setHoveredBbox(null);
    };

    if (typeof document !== "undefined" && "startViewTransition" in document) {
      const transition = (document as any).startViewTransition(() => {
        updateTab();
      });
      transition.finished.finally(() => {
        panelHeadingRef.current?.focus({ preventScroll: true });
      });
    } else {
      updateTab();
      panelHeadingRef.current?.focus({ preventScroll: true });
    }

    btn.scrollIntoView({ block: "nearest", inline: "nearest" });
  };

  const handleCopyId = () => {
    if (!dossier) return;
    navigator.clipboard?.writeText(dossier.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] gap-2.5">
        <Loader2 className="h-6 w-6 text-amber-400 animate-spin" aria-hidden="true" />
        <p className="text-xs text-zinc-400">Cargando expediente...</p>
      </div>
    );
  }

  if (error || !dossier) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="min-h-[2.75rem] min-w-[2.75rem] w-11 rounded-xl bg-rose-500/10 text-rose-400 mx-auto flex items-center justify-center border border-rose-500/25">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </div>
        <h1 className="text-lg font-bold text-zinc-100">No se pudo cargar el expediente</h1>
        <p className="text-xs text-zinc-400">{error || "Expediente no encontrado"}</p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 rounded-lg text-xs font-medium transition"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Volver a Expedientes</span>
        </Link>
      </div>
    );
  }

  const activeDocument: DocumentDetail | undefined = dossier.documents[selectedDocIndex];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-zinc-800/90">
        <div className="flex items-start sm:items-center gap-3">
          <Link
            href="/"
            aria-label="Volver a Expedientes"
            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-100 transition border border-zinc-800"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          </Link>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-lg sm:text-xl font-bold text-zinc-100 tracking-tight">{dossier.title}</h1>
              <span
                className={`inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-md font-mono font-semibold border ${
                  dossier.status === "RECONCILED"
                    ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/25"
                    : "bg-rose-500/10 text-rose-300 border-rose-500/25"
                }`}
              >
                {dossier.status === "RECONCILED" ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                ) : (
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />
                )}
                <span>{dossier.status === "RECONCILED" ? "Conciliado" : "Observado"}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 mt-1 text-[0.7rem] text-zinc-500 font-mono">
              <span>ID: {dossier.id}</span>
              <button
                type="button"
                onClick={handleCopyId}
                aria-label="Copiar ID"
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition"
              >
                {copiedId ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-400" aria-hidden="true" />
                    <span className="text-emerald-300">Copiado</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" aria-hidden="true" />
                    <span>Copiar</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Document Tabs & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {dossier.documents.length > 0 && (
            <div
              role="tablist"
              aria-label="Comprobantes del expediente"
              className="tablist-scroller bg-[#121215] border border-zinc-800 rounded-lg"
            >
              {dossier.documents.map((doc, idx) => (
                <button
                  key={doc.id}
                  id={`doc-tab-${idx}`}
                  type="button"
                  role="tab"
                  aria-selected={selectedDocIndex === idx}
                  onClick={(e) => handleSelectDocumentTab(idx, e)}
                  className="text-xs font-medium flex items-center gap-1.5"
                >
                  <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>{doc.doc_type}</span>
                </button>
              ))}
            </div>
          )}

          <button
            type="button"
            onClick={() => window.print()}
            aria-label="Imprimir o exportar dictamen contable"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-zinc-100 text-xs font-medium transition active:scale-95"
          >
            <Printer className="h-3.5 w-3.5 text-amber-500" aria-hidden="true" />
            <span className="hidden sm:inline">Imprimir Dictamen</span>
          </button>
        </div>
      </div>

      {/* Split Pane Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Pane: Document Viewer (7 cols) */}
        <div className="lg:col-span-7 h-[780px] lg:h-[calc(100vh-5.5rem)] lg:min-h-[680px] lg:max-h-[860px] lg:sticky lg:top-[4.25rem]">
          {activeDocument ? (
            <DocumentViewer
              dossierId={dossier.id}
              document={activeDocument}
              activeBbox={activeBbox}
              onSelectEntity={(_, bbox) => handleTogglePinBbox(bbox)}
            />
          ) : (
            <div className="h-full flex items-center justify-center surface-card text-zinc-500 text-xs">
              Sin documentos en este expediente.
            </div>
          )}
        </div>

        {/* Right Pane: Reconciliation & Extractions (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          <ReconciliationPanel reconciliation={dossier.reconciliation} status={dossier.status} />

          {activeDocument && (
            <section
              role="tabpanel"
              aria-labelledby={`doc-tab-${selectedDocIndex}`}
              className="surface-card p-5 space-y-5"
            >
              <div>
                <h2
                  ref={panelHeadingRef}
                  tabIndex={-1}
                  className="text-sm font-semibold text-zinc-100 focus:outline-none"
                >
                  Datos Extraídos ({activeDocument.doc_type})
                </h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Pasa el cursor o haz clic en un campo para fijar su posición en el documento.
                </p>
              </div>

              {/* Fields Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {activeDocument.extractions.map((ext, idx) => {
                  const isPinned = isSameBbox(pinnedBbox, ext.bbox);
                  const isActive = isSameBbox(activeBbox, ext.bbox);
                  return (
                    <button
                      key={`${ext.field_name}-${idx}`}
                      type="button"
                      onMouseEnter={() => ext.bbox && setHoveredBbox(ext.bbox)}
                      onMouseLeave={() => setHoveredBbox(null)}
                      onClick={() => handleTogglePinBbox(ext.bbox)}
                      className={`p-2.5 text-left rounded-lg border transition-colors ${
                        isPinned
                          ? "bg-amber-500/20 border-amber-500/70 ring-1 ring-amber-500/30"
                          : isActive
                          ? "bg-amber-500/12 border-amber-500/45"
                          : "bg-[#0b0b0d] hover:bg-zinc-900 border-zinc-800/90 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[0.65rem] font-mono text-zinc-400 uppercase block">
                          {ext.field_name}
                        </span>
                        {ext.bbox && (
                          <span
                            className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${
                              isActive ? "bg-amber-400" : "bg-zinc-600"
                            }`}
                            title="Coordenadas espaciales mapeadas"
                          />
                        )}
                      </div>
                      <span className="text-zinc-100 font-semibold block mt-0.5 truncate">
                        {ext.field_value || "—"}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Line Items Table */}
              {activeDocument.line_items.length > 0 && (
                <div className="space-y-2.5 pt-1">
                  <h3
                    id="line-items-table-caption"
                    className="text-xs font-semibold text-zinc-300"
                  >
                    Detalle de Ítems ({activeDocument.line_items.length})
                  </h3>

                  <div
                    tabIndex={0}
                    role="region"
                    aria-labelledby="line-items-table-caption"
                    className="table-wrapper scroller"
                  >
                    <table
                      className="responsive-data-table text-left text-xs"
                      style={
                        {
                          "--label-2": '"Cant."',
                          "--label-3": '"P. Unit"',
                          "--label-4": '"Total"',
                        } as React.CSSProperties
                      }
                    >
                      <thead className="border-b border-zinc-800 text-zinc-400 uppercase font-mono text-[0.65rem]">
                        <tr>
                          <th scope="col" className="py-2 px-3">
                            Descripción
                          </th>
                          <th scope="col" className="py-2 px-2 text-right">
                            Cant.
                          </th>
                          <th scope="col" className="py-2 px-2 text-right">
                            P. Unit
                          </th>
                          <th scope="col" className="py-2 px-3 text-right">
                            Total
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-800/60 font-mono">
                        {activeDocument.line_items.map((item, idx) => {
                          const isRowActive = isSameBbox(activeBbox, item.bbox);
                          return (
                            <tr
                              key={idx}
                              onMouseEnter={() => item.bbox && setHoveredBbox(item.bbox)}
                              onMouseLeave={() => setHoveredBbox(null)}
                              onClick={() => handleTogglePinBbox(item.bbox)}
                              className={`cursor-pointer transition-colors ${
                                isRowActive ? "bg-amber-500/15" : "hover:bg-zinc-800/50"
                              }`}
                            >
                              <th scope="row" className="py-2 px-3 text-zinc-100 font-sans text-xs">
                                {item.description}
                              </th>
                              <td className="py-2 px-2 text-right text-zinc-300">{item.quantity}</td>
                              <td className="py-2 px-2 text-right text-zinc-300">
                                S/ {item.unit_price.toFixed(2)}
                              </td>
                              <td className="py-2 px-3 text-right font-semibold text-emerald-400">
                                S/ {item.line_total.toFixed(2)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
