"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, FileText, Layers, ShieldCheck, XCircle } from "lucide-react";
import { checkBackendHealth } from "@/lib/api";

export default function Navbar() {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    checkBackendHealth().then((status) => setIsOnline(status));
    const interval = setInterval(() => {
      checkBackendHealth().then((status) => setIsOnline(status));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="border-b border-gray-800 bg-[#0f172a]/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-lg tracking-tight">DocuMind</span>
              <span className="px-2 py-0.5 text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded">
                Financial AI
              </span>
            </div>
            <p className="text-xs text-gray-400 hidden sm:block">Motor de Cotejo de 3 Vías & Extracción Espacial</p>
          </div>
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-full">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span className="text-gray-300 font-medium">3-Way Matching Engine</span>
          </div>

          <div className="flex items-center gap-1.5 text-xs bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-full">
            {isOnline === null ? (
              <span className="h-2 w-2 rounded-full bg-yellow-400 animate-pulse" />
            ) : isOnline ? (
              <>
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="text-emerald-400 font-medium">API Conectada</span>
              </>
            ) : (
              <>
                <span className="h-2 w-2 rounded-full bg-rose-400" />
                <span className="text-rose-400 font-medium">API Desconectada</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
