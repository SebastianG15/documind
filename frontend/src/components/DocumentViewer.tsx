"use client";

import React, { useState, useEffect } from "react";
import { BoundingBox2D, DocumentDetail } from "@/lib/types";
import { ZoomIn, ZoomOut, RotateCcw, Crosshair } from "lucide-react";

interface Props {
  dossierId: string;
  document: DocumentDetail;
  activeBbox: BoundingBox2D | null;
  onSelectEntity?: (label: string, bbox: BoundingBox2D) => void;
}

type BoxCategory = "all" | "supplier" | "total" | "item" | "header";

export default function DocumentViewer({ dossierId, document, activeBbox, onSelectEntity }: Props) {
  const [currentPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [hoveredBox, setHoveredBox] = useState<{ label: string; bbox: BoundingBox2D } | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<BoxCategory>("all");
  const [imageError, setImageError] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const totalPages = Math.max(1, document.pages_count);
  const imageUrl = `${API_BASE}/dossiers/${dossierId}/pages/${document.id}/image`;

  useEffect(() => {
    setImageError(false);
    setZoom(1);
  }, [document.id]);

  const allBoxes: Array<{
    id: string;
    label: string;
    type: "supplier" | "total" | "item" | "header";
    bbox: BoundingBox2D;
  }> = [];

  const isMatchingBbox = (a?: BoundingBox2D | null, b?: BoundingBox2D | null) => {
    if (!a || !b) return false;
    return a.ymin === b.ymin && a.xmin === b.xmin && a.ymax === b.ymax && a.xmax === b.xmax;
  };

  document.extractions.forEach((ext, i) => {
    if (ext.bbox) {
      let bType: "supplier" | "total" | "header" = "supplier";
      if (
        ext.field_name.includes("TOTAL") ||
        ext.field_name.includes("SUBTOTAL") ||
        ext.field_name.includes("TAX") ||
        ext.field_name.includes("AMOUNT") ||
        ext.field_name.includes("CURRENCY")
      ) {
        bType = "total";
      }

      allBoxes.push({
        id: `ext-${i}`,
        label: `${ext.field_name}: ${ext.field_value}`,
        type: bType,
        bbox: ext.bbox,
      });
    }
  });

  document.line_items.forEach((item, i) => {
    if (item.bbox) {
      allBoxes.push({
        id: `item-${i}`,
        label: `${item.description} (${item.quantity}x)`,
        type: "item",
        bbox: item.bbox,
      });
    }
  });

  const visibleBoxes = allBoxes.filter(
    (b) => categoryFilter === "all" || b.type === categoryFilter || isMatchingBbox(b.bbox, activeBbox)
  );

  const getStrokeColor = (type: string, isActive: boolean) => {
    if (isActive) return "#f59e0b"; // Warm Amber highlight when active
    switch (type) {
      case "supplier":
        return "#a1a1aa"; // Stone
      case "total":
        return "#10b981"; // Emerald
      case "item":
        return "#eab308"; // Gold
      default:
        return "#d4d4d8"; // Zinc
    }
  };

  const getFillColor = (type: string, isActive: boolean) => {
    if (isActive) return "rgba(245, 158, 11, 0.24)";
    switch (type) {
      case "supplier":
        return "rgba(161, 161, 170, 0.14)";
      case "total":
        return "rgba(16, 185, 129, 0.14)";
      case "item":
        return "rgba(234, 179, 8, 0.14)";
      default:
        return "rgba(212, 212, 216, 0.12)";
    }
  };

  const inspectedBbox = hoveredBox?.bbox || activeBbox;
  const inspectedLabel =
    hoveredBox?.label ||
    allBoxes.find((b) => isMatchingBbox(b.bbox, activeBbox))?.label ||
    "Pasa el cursor sobre un dato para ubicarlo en el comprobante";

  return (
    <div className="flex flex-col h-full surface-card overflow-hidden">
      {/* Compact Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 border-b border-zinc-800 bg-[#141418]">
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Filtrar regiones del documento">
          {(
            [
              { id: "all", label: "Todo" },
              { id: "supplier", label: "Emisor" },
              { id: "total", label: "Importes" },
              { id: "item", label: "Ítems" },
            ] as const
          ).map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setCategoryFilter(f.id)}
              aria-pressed={categoryFilter === f.id}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                categoryFilter === f.id
                  ? "bg-zinc-800 text-zinc-100 border border-zinc-700"
                  : "text-zinc-400 hover:text-zinc-200 border border-transparent"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-1 bg-[#0b0b0d] border border-zinc-800 rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.65, Number((z - 0.15).toFixed(2))))}
            aria-label="Reducir zoom"
            className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-100 transition"
          >
            <ZoomOut className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <span className="text-[0.7rem] font-mono text-zinc-300 px-1.5 min-w-[3rem] text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(2.4, Number((z + 0.15).toFixed(2))))}
            aria-label="Aumentar zoom"
            className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-100 transition"
          >
            <ZoomIn className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            aria-label="Restablecer zoom"
            className="p-1.5 hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-100 border-l border-zinc-800 transition"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="scroller flex-1 overflow-auto p-4 sm:p-5 flex items-start justify-center bg-[#09090b] relative">
        <div
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: "center top",
            transition: "transform 0.15s ease-out",
          }}
          className="relative w-full max-w-[520px] rounded-lg overflow-hidden border border-zinc-800 shadow-xl bg-white"
        >
          {!imageError ? (
            <img
              src={imageUrl}
              alt={`Comprobante digitalizado ${document.doc_type}`}
              width={800}
              height={1000}
              className="w-full h-auto block select-none"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="w-full aspect-[4/5] bg-[#fafaf9] text-zinc-800 p-6 flex flex-col justify-between relative select-none">
              <div className="border-b border-zinc-300 pb-3 flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-500 block">
                    Vista Estructurada (Pág. {currentPage}/{totalPages})
                  </span>
                  <h4 className="text-sm font-bold text-zinc-900 mt-0.5">{document.doc_type}</h4>
                </div>
                <div className="border border-zinc-800 px-2.5 py-1 rounded text-right font-mono text-xs font-bold">
                  {document.extractions.find((e) => e.field_name.includes("NUMBER") || e.field_name.includes("RUC"))
                    ?.field_value || "COMPROBANTE"}
                </div>
              </div>
              <div className="my-auto text-center text-xs text-zinc-400 font-mono py-12 border border-dashed border-zinc-300 rounded">
                Coordenadas del Documento (1000 × 1000)
              </div>
              <div className="border-t border-zinc-300 pt-2 flex justify-between text-[10px] font-mono text-zinc-500">
                <span>DocuMind</span>
                <span>{allBoxes.length} campos mapeados</span>
              </div>
            </div>
          )}

          {/* SVG Vector Overlay */}
          <svg
            viewBox="0 0 1000 1000"
            className="absolute inset-0 w-full h-full pointer-events-auto"
            preserveAspectRatio="none"
            aria-label="Regiones detectadas en el comprobante"
          >
            {visibleBoxes.map((box) => {
              const isActive =
                isMatchingBbox(box.bbox, activeBbox) || isMatchingBbox(box.bbox, hoveredBox?.bbox);
              const x = Math.max(4, box.bbox.xmin - 4);
              const y = Math.max(4, box.bbox.ymin - 3);
              const width = Math.min(992 - x, Math.max(14, box.bbox.xmax - box.bbox.xmin + 8));
              const height = Math.min(992 - y, Math.max(14, box.bbox.ymax - box.bbox.ymin + 6));

              return (
                <g key={box.id}>
                  {isActive && (
                    <rect
                      x={Math.max(1, x - 3)}
                      y={Math.max(1, y - 3)}
                      width={width + 6}
                      height={height + 6}
                      fill="none"
                      stroke="rgba(245, 158, 11, 0.45)"
                      strokeWidth={3}
                      rx={5}
                      className="pointer-events-none"
                    />
                  )}
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={getFillColor(box.type, isActive)}
                    stroke={getStrokeColor(box.type, isActive)}
                    strokeWidth={isActive ? 3 : 1.5}
                    rx={3}
                    className="cursor-pointer transition-colors duration-150"
                    onMouseEnter={() => setHoveredBox({ label: box.label, bbox: box.bbox })}
                    onMouseLeave={() => setHoveredBox(null)}
                    onClick={() => onSelectEntity && onSelectEntity(box.label, box.bbox)}
                  />
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Footer Info Bar (fixed height to prevent layout shifts on hover) */}
      <div className="h-10 shrink-0 px-4 border-t border-zinc-800 bg-[#141418] flex items-center justify-between gap-2 text-xs text-zinc-400">
        <div className="flex items-center gap-2 min-w-0">
          <Crosshair
            className={`h-3.5 w-3.5 flex-shrink-0 transition-colors ${
              inspectedBbox ? "text-amber-400" : "text-zinc-500"
            }`}
            aria-hidden="true"
          />
          <span className={`truncate ${inspectedBbox ? "text-zinc-100 font-medium" : "text-zinc-400"}`}>
            {inspectedLabel}
          </span>
        </div>

        <span
          className={`font-mono text-[0.68rem] px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-amber-300/90 flex-shrink-0 transition-opacity ${
            inspectedBbox ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
          aria-hidden={!inspectedBbox}
        >
          {inspectedBbox
            ? `[${inspectedBbox.ymin}, ${inspectedBbox.xmin}, ${inspectedBbox.ymax}, ${inspectedBbox.xmax}]`
            : "[000, 000, 000, 000]"}
        </span>
      </div>
    </div>
  );
}
