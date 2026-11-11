"use client";

import React, { useState, useId } from "react";
import { Search, Loader2, FileText, ArrowUpRight, X } from "lucide-react";
import { searchDossiers } from "@/lib/api";
import { SearchResultItem } from "@/lib/types";

interface Props {
  onSelectResult?: (dossierId: string) => void;
}

export default function SemanticSearchBar({ onSelectResult }: Props) {
  const inputId = useId();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const executeSearch = async (searchQuery: string) => {
    const trimmed = searchQuery.trim();
    if (trimmed.length < 2) return;

    setQuery(trimmed);
    setLoading(true);
    setHasSearched(true);
    try {
      const data = await searchDossiers(trimmed, 6);
      setResults(data.results);
    } catch (err) {
      console.error(err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    await executeSearch(query);
  };

  return (
    <search className="w-full relative" aria-label="Buscar expedientes o comprobantes">
      <form onSubmit={handleSearch} className="relative">
        <label htmlFor={inputId} className="sr-only">
          Buscar por proveedor, RUC, serie o concepto
        </label>
        <div className="relative flex items-center">
          <Search className="absolute left-3.5 h-4 w-4 text-zinc-500 pointer-events-none" aria-hidden="true" />
          <input
            id={inputId}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setHasSearched(false);
            }}
            placeholder="Buscar proveedor, serie, ítem o banco (ej. 'válvulas', 'BCP')..."
            className="w-full bg-[#121215] border border-zinc-800 hover:border-zinc-700 focus:border-amber-500/70 rounded-lg pl-10 pr-24 py-2 text-xs sm:text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none transition"
          />
          <div className="absolute right-1.5 flex items-center gap-1">
            {hasSearched && (
              <button
                type="button"
                onClick={() => {
                  setHasSearched(false);
                  setQuery("");
                }}
                aria-label="Cerrar búsqueda"
                className="p-1.5 text-zinc-400 hover:text-zinc-100 rounded-md hover:bg-zinc-800 transition"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}
            <button
              type="submit"
              disabled={loading || query.trim().length < 2}
              className="px-3 py-1 bg-zinc-800 hover:not(:disabled):bg-zinc-700 disabled:opacity-40 text-zinc-100 rounded-md text-xs font-medium flex items-center gap-1.5 transition"
            >
              {loading && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
              <span>Buscar</span>
            </button>
          </div>
        </div>
      </form>

      {/* Results Dropdown */}
      {hasSearched && (
        <div
          role="region"
          aria-label="Resultados encontrados"
          className="scroller absolute top-full left-0 right-0 mt-1.5 bg-[#141418] border border-zinc-800 rounded-xl shadow-2xl p-2 z-40 max-h-80 overflow-y-auto text-left"
        >
          <div className="text-[0.68rem] font-medium text-zinc-400 px-2.5 py-1 flex items-center justify-between border-b border-zinc-800/80 pb-1.5">
            <span>Coincidencias en expedientes</span>
            <span className="font-mono text-amber-400">{results.length}</span>
          </div>

          {results.length === 0 ? (
            <p className="text-xs text-zinc-400 px-3 py-5 text-center">
              Sin resultados para «{query}».
            </p>
          ) : (
            <ul className="divide-y divide-zinc-800/60 mt-1">
              {results.map((res) => (
                <li key={res.page_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setHasSearched(false);
                      onSelectResult && onSelectResult(res.dossier_id);
                    }}
                    className="w-full p-2.5 hover:bg-zinc-800/60 rounded-lg cursor-pointer transition flex items-center justify-between group text-left"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="min-h-[2rem] min-w-[2rem] rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-300 flex-shrink-0">
                        <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-xs font-semibold text-zinc-100 group-hover:text-amber-400 transition truncate">
                          {res.dossier_title}
                        </h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[0.68rem] text-zinc-400 font-mono">{res.doc_type}</span>
                          <span className="text-xs text-zinc-600" aria-hidden="true">
                            ·
                          </span>
                          <span
                            className={`text-[0.65rem] font-mono font-semibold ${
                              res.dossier_status === "RECONCILED" ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {res.dossier_status === "RECONCILED" ? "Conciliado" : "Observado"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                      <span className="text-[0.7rem] font-mono text-zinc-400">
                        {(res.similarity_score * 100).toFixed(0)}%
                      </span>
                      <ArrowUpRight
                        className="h-3.5 w-3.5 text-zinc-500 group-hover:text-zinc-200 transition"
                        aria-hidden="true"
                      />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </search>
  );
}
