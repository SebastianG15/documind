"use client";

import React, { useState } from "react";
import DossierUpload from "@/components/DossierUpload";
import SemanticSearchBar from "@/components/SemanticSearchBar";
import { Sparkles, Cpu, Layers, ShieldCheck, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  const [selectedDossierId, setSelectedDossierId] = useState<string | null>(null);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Hero section */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Inteligencia Documental & Cotejo Contable de 3 Vías</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
          Auditoría y Conciliación Automática de <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">Cuentas por Pagar</span>
        </h1>
        <p className="text-base text-gray-400 leading-relaxed">
          Verifica en segundos la consistencia matemática entre Facturas Comerciales, recepción en almacén con Guías de Remisión y pagos con Vouchers Bancarios mediante inferencia 100% local en GPU.
        </p>

        {/* Semantic Search Bar */}
        <div className="pt-4 max-w-2xl mx-auto">
          <SemanticSearchBar onSelectResult={(id) => setSelectedDossierId(id)} />
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-[#111827]/80 border border-gray-800 flex items-start gap-4">
          <div className="h-10 w-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 flex-shrink-0">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">OCR Espacial en GPU</h3>
            <p className="text-xs text-gray-400 mt-1">
              Deskewing afin por Hough y extracción de coordenadas de cajas delimitadoras en milisegundos con CUDA.
            </p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#111827]/80 border border-gray-800 flex items-start gap-4">
          <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">3-Way Matching Engine</h3>
            <p className="text-xs text-gray-400 mt-1">
              Cotejo cruzado de cantidades facturadas vs. recepcionadas y auditoría de transferencias bancarias.
            </p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#111827]/80 border border-gray-800 flex items-start gap-4">
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 flex-shrink-0">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Vectores pgvector (384d)</h3>
            <p className="text-xs text-gray-400 mt-1">
              Búsqueda semántica híbrida por similitud de coseno sobre la base de datos PostgreSQL 16.
            </p>
          </div>
        </div>
      </div>

      {/* Main Upload / Viewer Container */}
      <div className="space-y-6">
        <DossierUpload onDossierUploaded={(id) => setSelectedDossierId(id)} />

        {selectedDossierId && (
          <div className="p-5 bg-blue-950/30 border border-blue-500/30 rounded-2xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="h-3 w-3 rounded-full bg-blue-400 animate-pulse" />
              <div>
                <p className="text-sm font-semibold text-white">Expediente cargado con éxito</p>
                <p className="text-xs text-gray-400 font-mono">ID: {selectedDossierId}</p>
              </div>
            </div>
            <Link
              href={`/dossier/${selectedDossierId}`}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition shadow"
            >
              <span>Abrir en Visor Interactivo</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
