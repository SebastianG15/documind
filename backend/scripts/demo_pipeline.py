"""Script de Demostracion End-to-End para DocuMind Financial AI.

Genera un expediente contable completo (Factura, Guia de Remision y Voucher Bancario)
con inclinacion angular sintetica y ejecuta el pipeline de extremo a extremo:
1. Preprocesamiento de imagen y correccion de inclinacion (Deskewing Hough + CLAHE).
2. Extraccion OCR espacial (EasyOCR CRAFT en GPU/CPU) con coordenadas normalizadas [0, 1000].
3. Clasificacion lexica heuristica del tipo documental.
4. Extraccion estructurada de metadatos fiscales y lineas de detalle.
5. Indexacion y vectorizacion semantica 384d (pgvector).
6. Auditoria matematica y fisica de 3 vias (Three-Way Matching).

Ademas, almacena los comprobantes en 'backend/data/samples/demo_expediente/' listos
para ser arrastrados y probados directamente en la interfaz grafica web (Next.js 15).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

# Asegurar path de importacion del backend
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.nlp.classifier import DocumentClassifier, DocumentType
from src.nlp.embeddings import EmbeddingEngine
from src.nlp.entity_extractor import EntityExtractor
from src.nlp.reconciler import ReconciliationStatus, ThreeWayReconciler
from src.services.pipeline_service import PipelineService
from src.vision.preprocessor import DocumentPreprocessor
from src.vision.spatial_ocr import SpatialOCREngine


def generate_sample_invoice(angle: float = 4.5, width: int = 1000, height: int = 1400) -> np.ndarray:
    """Genera una factura comercial electronica realista con tabla de items e inclinacion."""
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)

    # Cabecera emisor
    cv2.putText(canvas, "DISTRIBUIDORA INDUSTRIAL DEL SUR S.A.C.", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (20, 20, 20), 2)
    cv2.putText(canvas, "RUC: 20549812341 - AV. NICOLAS ARRIOLA 1840, LIMA", (70, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    cv2.putText(canvas, "FACTURA ELECTRONICA: F001-0008492", (70, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(canvas, "FECHA DE EMISION: 28/10/2026 - MONEDA: PEN (SOLES)", (70, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)

    cv2.line(canvas, (70, 255), (width - 70, 255), (100, 100, 100), 2)

    # Tabla de items
    headers = "ITEM  DESCRIPCION                           CANT    U.M.   P.UNIT     TOTAL"
    cv2.putText(canvas, headers, (70, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
    cv2.line(canvas, (70, 330), (width - 70, 330), (160, 160, 160), 1)

    items = [
        ("001", "VALVULA DE CONTROL 1/2 PULG", "4", "UND", "120.00", "480.00"),
        ("002", "MANOMETRO DE PRESION DIFERENCIAL", "2", "UND", "350.00", "700.00"),
        ("003", "FILTRO DE AIRE INDUSTRIAL 10UM", "10", "UND", "45.00", "450.00"),
    ]

    y = 380
    for it in items:
        row = f"{it[0]:<5} {it[1]:<37} {it[2]:<7} {it[3]:<6} {it[4]:<10} {it[5]}"
        cv2.putText(canvas, row, (70, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
        y += 60

    # Totales
    cv2.line(canvas, (width - 480, y + 20), (width - 70, y + 20), (100, 100, 100), 2)
    cv2.putText(canvas, "SUBTOTAL:      S/ 1,630.00", (width - 450, y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(canvas, "IGV (18%):     S/   293.40", (width - 450, y + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(canvas, "TOTAL FACTURA: S/ 1,923.40", (width - 450, y + 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Inclinacion sintetica
    if abs(angle) > 0.01:
        rot_mat = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
        canvas = cv2.warpAffine(canvas, rot_mat, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    return canvas


def generate_sample_shipping_guide(angle: float = -3.5, width: int = 1000, height: int = 1400) -> np.ndarray:
    """Genera una guia de remision de remitente para despacho de almacen."""
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)

    # Cabecera
    cv2.putText(canvas, "DISTRIBUIDORA INDUSTRIAL DEL SUR S.A.C.", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (20, 20, 20), 2)
    cv2.putText(canvas, "GUIA DE REMISION DE REMITENTE: T001-000412", (70, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(canvas, "RUC REMITENTE: 20549812341 - RUC DESTINATARIO: 20100045891", (70, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    cv2.putText(canvas, "FECHA DE TRASLADO: 29/10/2026 - MOTIVO: VENTA COMERCIAL", (70, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    cv2.putText(canvas, "PUNTO DE LLEGADA: PLANTA CENTRAL CARRETERA CENTRAL KM 12", (70, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)

    cv2.line(canvas, (70, 305), (width - 70, 305), (100, 100, 100), 2)

    headers = "ITEM  CODIGO     DESCRIPCION FISICA ENTREGADA         CANTIDAD  U.M."
    cv2.putText(canvas, headers, (70, 355), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
    cv2.line(canvas, (70, 375), (width - 70, 375), (160, 160, 160), 1)

    items = [
        ("01", "VALV-01", "VALVULA DE CONTROL 1/2 PULG", "4.00", "UND"),
        ("02", "MANO-02", "MANOMETRO DE PRESION DIFERENCIAL", "2.00", "UND"),
        ("03", "FILT-03", "FILTRO DE AIRE INDUSTRIAL 10UM", "10.00", "UND"),
    ]

    y = 430
    for it in items:
        row = f"{it[0]:<5} {it[1]:<10} {it[2]:<36} {it[3]:<9} {it[4]}"
        cv2.putText(canvas, row, (70, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
        y += 65

    # Sello de conformidad de recepcion
    cv2.rectangle(canvas, (70, y + 40), (450, y + 160), (120, 120, 120), 2)
    cv2.putText(canvas, "CONFORMIDAD DE RECEPCION DE ALMACEN", (85, y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 2)
    cv2.putText(canvas, "MERCADERIA RECIBIDA COMPLETA", (85, y + 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 120, 0), 2)

    if abs(angle) > 0.01:
        rot_mat = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
        canvas = cv2.warpAffine(canvas, rot_mat, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    return canvas


def generate_sample_payment_voucher(angle: float = 2.0, width: int = 900, height: int = 1200) -> np.ndarray:
    """Genera una constancia de transferencia bancaria BCP."""
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)

    # Logo / Encabezado bancario
    cv2.putText(canvas, "BANCO DE CREDITO DEL PERU - BCP", (60, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (10, 30, 100), 2)
    cv2.putText(canvas, "CONSTANCIA DE TRANSFERENCIA BANCARIA A TERCEROS", (60, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (50, 50, 50), 2)
    cv2.line(canvas, (60, 190), (width - 60, 190), (10, 30, 100), 3)

    cv2.putText(canvas, "NUMERO DE OPERACION:  OP-98765432", (60, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
    cv2.putText(canvas, "FECHA DE OPERACION:   30/10/2026 14:32:15", (60, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)
    cv2.putText(canvas, "CUENTA ORIGEN:        191-8849201-0-45 (SOLES)", (60, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)
    cv2.putText(canvas, "CUENTA DESTINO:       193-2948102-1-88", (60, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)
    cv2.putText(canvas, "BENEFICIARIO:         DISTRIBUIDORA INDUSTRIAL DEL SUR S.A.C.", (60, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    cv2.putText(canvas, "MONEDA DE PAGO:       PEN (SOLES)", (60, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)

    cv2.line(canvas, (60, 540), (width - 60, 540), (150, 150, 150), 1)

    cv2.putText(canvas, "IMPORTE TOTAL TRANSFERIDO:", (60, 610), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(canvas, "S/ 1,923.40", (520, 610), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 120, 0), 3)

    cv2.putText(canvas, "ESTADO: TRANSFERENCIA LIQUIDADA EXITOSAMENTE", (60, 680), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 120, 0), 2)

    if abs(angle) > 0.01:
        rot_mat = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)
        canvas = cv2.warpAffine(canvas, rot_mat, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    return canvas


def run_full_evaluation_demo(output_dir: str = "data/samples/demo_expediente") -> None:
    """Genera el lote de comprobantes y ejecuta la evaluacion del pipeline completo."""
    demo_dir = BACKEND_DIR / output_dir
    demo_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("        DOCUMIND FINANCIAL AI - DEMOSTRACION OFICIAL DE PIPELINE")
    print("=" * 80)
    print("1. Generando comprobantes de prueba para el expediente comercial...")

    # Generar y persistir imagenes para que puedan ser usadas tambien en la web UI
    inv_img = generate_sample_invoice(angle=4.5)
    guide_img = generate_sample_shipping_guide(angle=-3.5)
    vouch_img = generate_sample_payment_voucher(angle=2.0)

    p_inv = demo_dir / "1_factura_f001_0008492.png"
    p_guide = demo_dir / "2_guia_remision_t001_000412.png"
    p_vouch = demo_dir / "3_voucher_banco_bcp.png"

    cv2.imwrite(str(p_inv), inv_img)
    cv2.imwrite(str(p_guide), guide_img)
    cv2.imwrite(str(p_vouch), vouch_img)

    print(f"  [OK] Factura generada:       {p_inv.name}")
    print(f"  [OK] Guia de Remision:       {p_guide.name}")
    print(f"  [OK] Voucher Bancario:       {p_vouch.name}")
    print(f"  Directorio de muestras:      {demo_dir.resolve()}")
    print("-" * 80)

    # Iniciar orquestador de pipeline
    print("\n2. Inicializando servicios de inferencia local y OCR espacial (CUDA)...")
    service = PipelineService(upload_dir=demo_dir / "processed")

    t_start = time.perf_counter()
    result = service.process_dossier_files([p_inv, p_guide, p_vouch])
    total_duration = time.perf_counter() - t_start

    print(f"\n[PIPELINE] Procesamiento completado en {total_duration:.2f} segundos.")
    print(f"Documentos procesados: {len(result.documents)}")

    # Detalle por documento
    for idx, doc in enumerate(result.documents, 1):
        print(f"\nDocumento #{idx}: {Path(doc.file_path).name}")
        print(f"  Tipo Clasificado: {doc.doc_type.value}")
        print(f"  Paginas:          {len(doc.pages)} pag(s)")
        if doc.pages:
            tokens_count = len(doc.pages[0].ocr_result.tokens)
            print(f"  Tokens OCR:       {tokens_count} detectados con coordenadas espaciales")

    # Resumen de Auditoria de 3 Vias
    rep = result.reconciliation_report
    print("\n" + "=" * 80)
    print("                  RESULTADO DE AUDITORIA DE 3 VIAS")
    print("=" * 80)
    print(f"ESTADO DE AUDITORIA: [{rep.status.value}]")
    print(f"  - Pilar 1 (Integridad Matematica) : {'APROBADO' if rep.math_valid else 'DISCREPANCIA'}")
    print(f"  - Pilar 2 (Recepcion de Almacen)   : {'APROBADO' if rep.goods_matched else 'FALTANTE'}")
    print(f"  - Pilar 3 (Liquidacion Bancaria)  : {'APROBADO' if rep.payment_matched else 'PENDIENTE'}")
    print(f"  - Total Facturado                 : S/ {rep.total_billed:,.2f}")
    print(f"  - Total Pagado (Vouchers)         : S/ {rep.total_paid:,.2f}")
    print(f"  - Saldo Pendiente                 : S/ {rep.balance_pending:,.2f}")
    print(f"\nDictamen Contable: {rep.summary}")
    print("=" * 80)

    print("\n[PROXIMO PASO EN INTERFAZ GRAFICA]:")
    print("  1. Inicia el frontend web: cd frontend && npm run dev")
    print("  2. Abre http://localhost:3000 en tu navegador")
    print("  3. Arrastra los 3 archivos PNG generados en:")
    print(f"     {demo_dir.resolve()}")
    print("  4. Explora el visor SVG con resaltado bidireccional y el semaforo interactivo.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecucion de la Demo Oficial de DocuMind Financial AI")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="data/samples/demo_expediente",
        help="Directorio donde guardar los comprobantes generados",
    )
    args = parser.parse_args()
    run_full_evaluation_demo(output_dir=args.output_dir)
