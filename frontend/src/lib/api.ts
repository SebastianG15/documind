import { DossierDetailResponse, DossierSummaryItem, DossierUploadResponse, SearchResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function listDossiers(limit: number = 20): Promise<DossierSummaryItem[]> {
  try {
    const response = await fetch(`${API_BASE}/dossiers?limit=${limit}`, { cache: "no-store" });
    if (!response.ok) return [];
    return response.json();
  } catch {
    return [];
  }
}

export async function uploadDossier(title: string, files: File[]): Promise<DossierUploadResponse> {
  const formData = new FormData();
  formData.append("title", title);
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${API_BASE}/dossiers/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Error al subir expediente" }));
    throw new Error(err.detail || "Error en el servidor al procesar el expediente");
  }

  return response.json();
}

export async function getDossier(dossierId: string): Promise<DossierDetailResponse> {
  const response = await fetch(`${API_BASE}/dossiers/${dossierId}`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Expediente no encontrado" }));
    throw new Error(err.detail || "Error al obtener detalle del expediente");
  }
  return response.json();
}

export async function searchDossiers(
  query: string,
  limit: number = 10,
  docType?: string,
  status?: string
): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE}/dossiers/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit, doc_type: docType, status }),
  });

  if (!response.ok) {
    throw new Error("Error al ejecutar busqueda semantica");
  }

  return response.json();
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch("http://localhost:8000/health", { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
