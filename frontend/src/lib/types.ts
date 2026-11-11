export interface BoundingBox2D {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
}

export interface ExtractionItem {
  field_name: string;
  field_value: string;
  confidence: number;
  bbox?: BoundingBox2D | null;
}

export interface LineItemDetail {
  sku?: string | null;
  description: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  bbox?: BoundingBox2D | null;
}

export interface DocumentDetail {
  id: string;
  doc_type: "INVOICE" | "SHIPPING_GUIDE" | "PAYMENT_VOUCHER" | "UNKNOWN";
  file_path: string;
  pages_count: number;
  extractions: ExtractionItem[];
  line_items: LineItemDetail[];
}

export interface DiscrepancyItem {
  type: string;
  [key: string]: any;
}

export interface ReconciliationDetail {
  math_valid: boolean;
  goods_matched: boolean;
  payment_matched: boolean;
  summary: string;
  discrepancies: DiscrepancyItem[];
}

export interface DossierDetailResponse {
  id: string;
  title: string;
  status: "PENDING" | "RECONCILED" | "DISCREPANCY_FOUND";
  created_at: string;
  documents: DocumentDetail[];
  reconciliation?: ReconciliationDetail | null;
}

export interface DossierUploadResponse {
  dossier_id: string;
  title: string;
  status: "PENDING" | "RECONCILED" | "DISCREPANCY_FOUND";
  documents_processed: number;
  reconciliation_summary: string;
  math_valid: boolean;
  goods_matched: boolean;
  payment_matched: boolean;
}

export interface DossierSummaryItem {
  id: string;
  title: string;
  status: "PENDING" | "RECONCILED" | "DISCREPANCY_FOUND";
  created_at: string;
  documents_count: number;
  doc_types: string[];
  math_valid: boolean;
  goods_matched: boolean;
  payment_matched: boolean;
  summary: string;
  discrepancies_count: number;
}

export interface SearchResultItem {
  page_id: string;
  document_id: string;
  dossier_id: string;
  dossier_title: string;
  dossier_status: string;
  doc_type: string;
  similarity_score: number;
  image_url: string;
}

export interface SearchResponse {
  total_results: number;
  query: string;
  results: SearchResultItem[];
}
