"use client";

import React, { useState } from "react";
import { Search, Loader2, Sparkles, FileText, ArrowRight } from "lucide-react";
import { searchDossiers } from "@/lib/api";
import { SearchResultItem } from "@/lib/types";

interface Props {
  onSelectResult?: (dossierId: string) => void;
}

export default function SemanticSearchBar({ onSelectResult }: Props) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || query.length < 2) return;

    setLoading(true);
    setHasSearched(true);
    try {
      const data = await searchDossiers(query, 5);
      setResults(data.results);
    } catch (err) {
      console.error(err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full relative">
      <form onSubmit={handleSearch} className="relative">
        <div className="relative flex items-center">
          <Search className="absolute left-4 h-5 w-5 text-gray-400 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar semánticamente (ej. 'válvulas de control', 'pagos del BCP')..."
            className="w-full bg-[#1e293b]/70 border border-gray-700 hover:border-gray-600 focus:border-blue-500 rounded-xl pl-12 pr-28 py-3.5 text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition"
          />
          <button
            type="submit"
            disabled={loading || query.trim().length < 2}
            className="absolute right-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Buscar
          </button>
        </div>
      </form>

      {/* Results Dropdown */}
      {hasSearched && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-[#0f172a] border border-gray-800 rounded-xl shadow-2xl p-3 z-40 max-h-96 overflow-y-auto">
          <div className="text-xs font-semibold text-gray-400 px-3 py-1.5 uppercase tracking-wider flex items-center justify-between">
            <span>Resultados por similitud vectorial (pgvector)</span>
            <span>{results.length} encontrados</span>
          </div>

          {results.length === 0 ? (
            <p className="text-sm text-gray-500 px-3 py-4 text-center">
              No se encontraron coincidencias vectoriales para esta consulta.
            </p>
          ) : (
            <div className="divide-y divide-gray-800/60 mt-1">
              {results.map((res) => (
                <div
                  key={res.page_id}
                  onClick={() => onSelectResult && onSelectResult(res.dossier_id)}
                  className="p-3 hover:bg-gray-800/40 rounded-lg cursor-pointer transition flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-gray-200 group-hover:text-blue-400 transition">
                        {res.dossier_title}
                      </h4>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-gray-400 font-mono">{res.doc_type}</span>
                        <span className="text-xs text-gray-600">•</span>
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                            res.dossier_status === "RECONCILED"
                              ? "bg-emerald-500/10 text-emerald-400"
                              : "bg-amber-500/10 text-amber-400"
                          }`}
                        >
                          {res.dossier_status}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-xs font-semibold text-emerald-400 font-mono">
                        {(res.similarity_score * 100).toFixed(1)}%
                      </span>
                      <p className="text-[10px] text-gray-500">similitud</p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-gray-500 group-hover:text-white transition" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
