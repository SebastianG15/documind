"use client";

import React, { useState, useRef } from "react";
import { BoundingBox2D, DocumentDetail, ExtractionItem, LineItemDetail } from "@/lib/types";
import { ZoomIn, ZoomOut, RotateCcw, Eye, Layers } from "lucide-react";

interface Props {
  dossierId: string;
  document: DocumentDetail;
  activeBbox: BoundingBox2D | null;
  onSelectEntity?: (label: string, bbox: BoundingBox2D) => void;
}

export default function DocumentViewer({ dossierId, document, activeBbox, onSelectEntity }: Props) {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [hoveredBox, setHoveredBox] = useState<BoundingBox2D | null>(null);

  const totalPages = Math.max(1, document.pages_count);
  const imageUrl = `http://localhost:8000/api/v1/dossiers/${dossierId}/pages/${document.id}/image`;

  // Collect all labeled boxes for rendering on SVG
  const allBoxes: Array<{
    id: string;
    label: string;
    type: "supplier" | "total" | "item" | "header";
    bbox: BoundingBox2D;
  }> = [];

  // 1. Extractions
  document.extractions.forEach((ext, i) => {
    if (ext.bbox) {
      let bType: "supplier" | "total" | "header" = "header";
      if (ext.field_name.includes("RUC") || ext.field_name.includes("SUPPLIER")) bType = "supplier";
      else if (ext.field_name.includes("TOTAL") || ext.field_name.includes("SUBTOTAL") || ext.field_name.includes("TAX"))
        bType = "total";

      allBoxes.push({
        id: `ext-${i}`,
        label: `${ext.field_name}: ${ext.field_value}`,
        type: bType,
        bbox: ext.bbox,
      });
    }
  });

  // 2. Line Items
  document.line_items.forEach((item, i) => {
    if (item.bbox) {
      allBoxes.push({
        id: `item-${i}`,
        label: `Item: ${item.description} (${item.quantity}x)`,
        type: "item",
        bbox: item.bbox,
      });
    }
  });

  const getStrokeColor = (type: string, isActive: boolean) => {
    if (isActive) return "#38bdf8"; // Bright sky blue when active
    switch (type) {
      case "supplier":
        return "#60a5fa"; // Blue
      case "total":
        return "#34d399"; // Emerald
      case "item":
        return "#fbbf24"; // Amber
      default:
        return "#c084fc"; // Purple
    }
  };

  const getFillColor = (type: string, isActive: boolean) => {
    if (isActive) return "rgba(56, 189, 248, 0.25)";
    switch (type) {
      case "supplier":
        return "rgba(96, 165, 250, 0.12)";
      case "total":
        return "rgba(52, 211, 153, 0.12)";
      case "item":
        return "rgba(251, 191, 36, 0.12)";
      default:
        return "rgba(192, 132, 252, 0.12)";
    }
  };

  const isMatchingBbox = (a?: BoundingBox2D | null, b?: BoundingBox2D | null) => {
    if (!a || !b) return false;
    return a.ymin === b.ymin && a.xmin === b.xmin && a.ymax === b.ymax && a.xmax === b.xmax;
  };

  return (
    <div className="flex flex-col h-full bg-[#0f172a] border border-gray-800 rounded-2xl overflow-hidden shadow-2xl">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-[#1e293b]/50">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-blue-400" />
          <span className="text-xs font-semibold text-white uppercase tracking-wider">
            Visor Espacial OCR (Normalizado 0-1000)
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-mono">
            Pág. {currentPage} / {totalPages}
          </span>
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded-lg p-1">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.7, z - 0.15))}
            className="p-1 hover:bg-gray-800 rounded text-gray-400 hover:text-white"
            title="Reducir Zoom"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <span className="text-[11px] font-mono text-gray-400 px-1.5">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}
            className="p-1 hover:bg-gray-800 rounded text-gray-400 hover:text-white"
            title="Aumentar Zoom"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="p-1 hover:bg-gray-800 rounded text-gray-400 hover:text-white ml-1 border-l border-gray-800"
            title="Restablecer"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-[#070b14] relative">
        <div
          style={{ transform: `scale(${zoom})`, transformOrigin: "center center", transition: "transform 0.15s ease-out" }}
          className="relative max-w-full rounded-xl overflow-hidden border border-gray-800 shadow-2xl bg-white"
        >
          {/* Document Base Image (Deskewed) */}
          <img
            src={imageUrl}
            alt="Comprobante Digitalizado"
            className="w-full h-auto block select-none"
            onError={(e) => {
              // Fallback placeholder if backend is not streaming this specific page
              (e.target as HTMLElement).style.display = "none";
            }}
          />

          {/* SVG Vector Overlay for Bounding Boxes */}
          <svg
            viewBox="0 0 1000 1000"
            className="absolute inset-0 w-full h-full pointer-events-auto"
            preserveAspectRatio="none"
          >
            {allBoxes.map((box) => {
              const isActive = isMatchingBbox(box.bbox, activeBbox) || isMatchingBbox(box.bbox, hoveredBox);
              const x = box.bbox.xmin;
              const y = box.bbox.ymin;
              const width = Math.max(8, box.bbox.xmax - box.bbox.xmin);
              const height = Math.max(8, box.bbox.ymax - box.bbox.ymin);

              return (
                <g key={box.id}>
                  <rect
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={getFillColor(box.type, isActive)}
                    stroke={getStrokeColor(box.type, isActive)}
                    strokeWidth={isActive ? 3 : 1.5}
                    rx={2}
                    className="cursor-pointer transition-all duration-150"
                    onMouseEnter={() => setHoveredBox(box.bbox)}
                    onMouseLeave={() => setHoveredBox(null)}
                    onClick={() => onSelectEntity && onSelectEntity(box.label, box.bbox)}
                  />
                  {isActive && (
                    <text
                      x={x + 4}
                      y={Math.max(16, y - 4)}
                      fill="#38bdf8"
                      fontSize="14"
                      fontWeight="bold"
                      fontFamily="monospace"
                      className="select-none pointer-events-none drop-shadow"
                    >
                      {box.label.slice(0, 32)}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Legend Footer */}
      <div className="px-4 py-2.5 border-t border-gray-800 bg-[#1e293b]/40 flex flex-wrap items-center justify-between text-xs text-gray-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded bg-blue-500" />
            <span>Proveedor/RUC</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded bg-emerald-500" />
            <span>Importes/Totales</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded bg-amber-400" />
            <span>Líneas de Ítems</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded bg-purple-400" />
            <span>Serie / Fechas</span>
          </span>
        </div>

        <span className="text-[11px] text-gray-500 hidden sm:block">
          Pasa el cursor sobre la tabla para resaltar su caja espacial
        </span>
      </div>
    </div>
  );
}
