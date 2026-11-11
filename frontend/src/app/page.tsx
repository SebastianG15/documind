"use client";

import React, { useEffect, useState, useCallback } from "react";
import DossierUpload from "@/components/DossierUpload";
import SemanticSearchBar from "@/components/SemanticSearchBar";
import {
  ArrowUpRight,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
  Plus,
  Percent,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listDossiers } from "@/lib/api";
import { DossierSummaryItem } from "@/lib/types";

type StatusFilter = "ALL" | "RECONCILED" | "DISCREPANCY_FOUND";

export default function HomePage() {
  const router = useRouter();
  const [selectedDossierId, setSelectedDossierId] = useState<string | null>(null);
  const [dossiers, setDossiers] = useState<DossierSummaryItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");

  const fetchDossiers = useCallback(async () => {
    setLoadingList(true);
    try {
      const data = await listDossiers(25);
      setDossiers(data);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    fetchDossiers();
    const onCreated = () => fetchDossiers();
    window.addEventListener("documind:dossier-created", onCreated);
    return () => window.removeEventListener("documind:dossier-created", onCreated);
  }, [fetchDossiers]);

  const handleFilterChange = (nextFilter: StatusFilter, e: React.MouseEvent<HTMLButtonElement>) => {
    const targetBtn = e.currentTarget;
    const applyState = () => setStatusFilter(nextFilter);

    if (typeof document !== "undefined" && "startViewTransition" in document) {
      (document as any).startViewTransition(() => {
        applyState();
      });
    } else {
      applyState();
    }

    targetBtn.scrollIntoView({ block: "nearest", inline: "nearest" });
  };

  const filteredDossiers = dossiers.filter((d) => {
    if (statusFilter === "ALL") return true;
    return d.status === statusFilter;
  });

  const reconciledCount = dossiers.filter((d) => d.status === "RECONCILED").length;
  const discrepancyCount = dossiers.filter((d) => d.status === "DISCREPANCY_FOUND").length;
  const successRate = dossiers.length > 0 ? Math.round((reconciledCount / dossiers.length) * 100) : 0;

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("es-PE", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString.slice(0, 10);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Workspace Header + Search Bar */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-zinc-800/90">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-widest text-amber-500 font-semibold">
              Auditoría Financiera
            </span>
            <span className="text-xs text-zinc-500">•</span>
            <span className="text-xs text-zinc-400 font-mono">Motor Three-Way Match</span>
          </div>
          <h1 className="fluid-page-title font-bold text-zinc-100 tracking-tight mt-1">
            Consola de Conciliación de Cuentas por Pagar
          </h1>
        </div>

        <div className="w-full md:w-96">
          <SemanticSearchBar
            onSelectResult={(id) => {
              setSelectedDossierId(id);
              router.push(`/dossier/${id}`);
            }}
          />
        </div>
      </div>

      {/* 4 Summary Metric Cards */}
      <section aria-label="Indicadores contables" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="surface-card px-4 py-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Expedientes Totales</span>
            <span className="text-xs font-mono text-zinc-400 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800">
              Cuentas x Pagar
            </span>
          </div>
          <span className="text-2xl font-bold text-zinc-100 font-mono mt-2 block">{dossiers.length}</span>
        </div>

        <div className="surface-card px-4 py-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Conciliados al 100%</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold text-emerald-400 font-mono">{reconciledCount}</span>
            <span className="text-xs text-zinc-500">aptos para liquidar</span>
          </div>
        </div>

        <div className="surface-card px-4 py-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Con Discrepancia</span>
            <AlertTriangle className="h-4 w-4 text-rose-400" aria-hidden="true" />
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold text-rose-400 font-mono">{discrepancyCount}</span>
            <span className="text-xs text-rose-400/80">requieren revisión</span>
          </div>
        </div>

        <div className="surface-card px-4 py-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-medium">Tasa de Efectividad</span>
            <Percent className="h-4 w-4 text-amber-400" aria-hidden="true" />
          </div>
          <div className="mt-2 space-y-1.5">
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-bold text-amber-400 font-mono">{successRate}%</span>
              <span className="text-[0.68rem] text-zinc-500 font-mono">automatización</span>
            </div>
            <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-amber-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${successRate}%` }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Dossier Table (7 cols) */}
        <section
          className="lg:col-span-7 surface-card p-5 sm:p-6 space-y-4"
          aria-labelledby="recent-dossiers-caption"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="recent-dossiers-caption" className="text-sm font-semibold text-zinc-100">
                Bandeja de Expedientes Auditados
              </h2>
              <p className="text-xs text-zinc-400 mt-0.5">
                Selecciona cualquier fila para abrir el visor con cajas delimitadoras de OCR.
              </p>
            </div>

            <div className="flex items-center gap-1.5">
              <div
                role="tablist"
                aria-label="Filtrar expedientes por estado"
                className="tablist-scroller bg-[#09090b] border border-zinc-800 rounded-lg"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={statusFilter === "ALL"}
                  onClick={(e) => handleFilterChange("ALL", e)}
                  className="text-xs font-medium"
                >
                  Todos ({dossiers.length})
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={statusFilter === "RECONCILED"}
                  onClick={(e) => handleFilterChange("RECONCILED", e)}
                  className="text-xs font-medium"
                >
                  Conciliados ({reconciledCount})
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={statusFilter === "DISCREPANCY_FOUND"}
                  onClick={(e) => handleFilterChange("DISCREPANCY_FOUND", e)}
                  className="text-xs font-medium"
                >
                  Observados ({discrepancyCount})
                </button>
              </div>

              <button
                type="button"
                onClick={fetchDossiers}
                aria-label="Actualizar lista de expedientes"
                className="p-2 rounded-lg bg-[#09090b] hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition active:scale-95"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loadingList ? "animate-spin text-amber-400" : ""}`} aria-hidden="true" />
              </button>
            </div>
          </div>

          {filteredDossiers.length === 0 ? (
            <div className="p-10 text-center border border-dashed border-zinc-800 rounded-xl space-y-3">
              <p className="text-xs text-zinc-400">
                {loadingList
                  ? "Cargando expedientes desde la base de datos..."
                  : "No se encontraron expedientes en este estado."}
              </p>
              <button
                type="button"
                onClick={() => window.dispatchEvent(new CustomEvent("documind:open-upload-modal"))}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-xs font-medium transition"
              >
                <Plus className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                <span>Iniciar primer expediente</span>
              </button>
            </div>
          ) : (
            <div tabIndex={0} role="region" aria-labelledby="recent-dossiers-caption" className="table-wrapper scroller">
              <table
                className="responsive-data-table text-left text-xs"
                style={
                  {
                    "--label-2": '"Estado"',
                    "--label-3": '"Pilares 3-Way"',
                    "--label-4": '"Detalle"',
                  } as React.CSSProperties
                }
              >
                <thead className="border-b border-zinc-800 text-zinc-400 uppercase font-mono text-[0.65rem]">
                  <tr>
                    <th scope="col" className="py-2.5 px-3.5">
                      Expediente / Proveedor
                    </th>
                    <th scope="col" className="py-2.5 px-2.5">
                      Dictamen
                    </th>
                    <th scope="col" className="py-2.5 px-2.5">
                      Mat · Alm · Pag
                    </th>
                    <th scope="col" className="py-2.5 px-3.5 text-right">
                      Inspección
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {filteredDossiers.map((item) => {
                    const isRec = item.status === "RECONCILED";
                    const isDisc = item.status === "DISCREPANCY_FOUND";
                    return (
                      <tr key={item.id} className="transition group">
                        <th scope="row" className="py-3 px-3.5 text-zinc-100">
                          <div className="font-semibold text-xs text-zinc-100 group-hover:text-amber-400 transition">
                            {item.title}
                          </div>
                          <div className="text-[0.68rem] text-zinc-500 font-mono mt-0.5 flex flex-wrap items-center gap-2">
                            <span>{formatDate(item.created_at)}</span>
                            <span aria-hidden="true">·</span>
                            <span>{item.documents_count} comprobantes</span>
                            {item.doc_types.length > 0 && (
                              <div className="inline-flex gap-1">
                                {item.doc_types.map((dt, i) => (
                                  <span
                                    key={i}
                                    className="px-1 py-0.2 rounded text-[0.6rem] bg-zinc-900 border border-zinc-800 text-zinc-400"
                                  >
                                    {dt === "INVOICE" ? "FAC" : dt === "SHIPPING_GUIDE" ? "GUIA" : "VOUCH"}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </th>
                        <td className="py-3 px-2.5">
                          {isRec ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 font-mono text-[0.68rem] font-semibold">
                              <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />
                              <span>Conciliado</span>
                            </span>
                          ) : isDisc ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 font-mono text-[0.68rem] font-semibold discrepancy-pulse">
                              <AlertTriangle className="h-3 w-3 text-rose-400" aria-hidden="true" />
                              <span>Observado ({item.discrepancies_count})</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/25 text-amber-300 font-mono text-[0.68rem] font-semibold">
                              <Clock className="h-3 w-3 text-amber-400" aria-hidden="true" />
                              <span>Pendiente</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-2.5 font-mono">
                          <div className="inline-flex items-center gap-1">
                            <span
                              title={item.math_valid ? "Cálculo matemático correcto" : "Descuadre matemático"}
                              className={`px-1.5 py-0.5 rounded text-[0.65rem] font-semibold ${
                                item.math_valid
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-rose-500/10 text-rose-400"
                              }`}
                            >
                              M:{item.math_valid ? "✓" : "✕"}
                            </span>
                            <span
                              title={item.goods_matched ? "Recepción de almacén conforme" : "Faltante en almacén"}
                              className={`px-1.5 py-0.5 rounded text-[0.65rem] font-semibold ${
                                item.goods_matched
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-rose-500/10 text-rose-400"
                              }`}
                            >
                              A:{item.goods_matched ? "✓" : "✕"}
                            </span>
                            <span
                              title={item.payment_matched ? "Liquidación bancaria total" : "Saldo pendiente de pago"}
                              className={`px-1.5 py-0.5 rounded text-[0.65rem] font-semibold ${
                                item.payment_matched
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-rose-500/10 text-rose-400"
                              }`}
                            >
                              P:{item.payment_matched ? "✓" : "✕"}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-3.5 text-right">
                          <Link
                            href={`/dossier/${item.id}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-100 font-medium text-xs transition active:scale-95"
                          >
                            <span>Auditar</span>
                            <ArrowUpRight className="h-3.5 w-3.5 text-zinc-400 group-hover:text-amber-400 transition" aria-hidden="true" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Right Column: Upload Form (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <DossierUpload
            onDossierUploaded={(id) => {
              setSelectedDossierId(id);
              fetchDossiers();
            }}
          />

          {selectedDossierId && (
            <div className="p-4 bg-[#141418] border border-amber-500/35 rounded-xl flex items-center justify-between gap-3 shadow-sm">
              <div>
                <p className="text-xs font-semibold text-zinc-100">Expediente listo</p>
                <p className="text-[0.7rem] text-zinc-400 font-mono">ID: {selectedDossierId.slice(0, 16)}…</p>
              </div>
              <Link
                href={`/dossier/${selectedDossierId}`}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-zinc-950 rounded-lg text-xs font-semibold flex items-center gap-1 transition"
              >
                <span>Ver Dictamen</span>
                <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
