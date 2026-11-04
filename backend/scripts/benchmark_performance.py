"""Suite de Benchmarking de Rendimiento y Latencia para DocuMind Financial AI.

Evalua el rendimiento computacional de extremo a extremo:
1. Preprocesamiento de vision (Deskewing por Transformada de Hough + CLAHE).
2. Inferencia de OCR Espacial (EasyOCR CRAFT + Latin) comparando GPU vs CPU.
3. Generacion de embeddings densos 384d (all-MiniLM-L6-v2) con multiples tamanos de batch.
4. Motor de conciliacion contable de 3 vias (ThreeWayReconciler) a escala.

Exporta resultados estructurados a JSON y genera tablas comparativas de rendimiento.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import torch

# Asegurar inclusion del directorio raiz de backend en sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.vision.preprocessor import DocumentPreprocessor, detect_skew_angle, enhance_contrast, rotate_image
from src.vision.spatial_ocr import SpatialOCREngine
from src.nlp.embeddings import EmbeddingEngine
from src.nlp.reconciler import ThreeWayReconciler
from src.nlp.schemas import (
    InvoiceExtraction,
    LineItemExtraction,
    PaymentVoucherExtraction,
    ShippingGuideExtraction,
)


def get_hardware_info() -> Dict[str, Any]:
    """Recopila especificaciones de hardware del entorno de ejecucion."""
    info: Dict[str, Any] = {
        "os": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
        "cpu": platform.processor() or "x86_64 Compatible",
        "python": platform.python_version(),
        "pytorch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["gpu_capability"] = f"{torch.cuda.get_device_capability(0)[0]}.{torch.cuda.get_device_capability(0)[1]}"
        info["gpu_vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    else:
        info["gpu_name"] = "N/A"
        info["gpu_capability"] = "N/A"
        info["gpu_vram_gb"] = 0.0

    return info


def generate_benchmark_page(width: int = 1200, height: int = 1600, angle: float = 4.5) -> np.ndarray:
    """Genera una imagen sintetica de factura de alta resolucion con rotacion controlada."""
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)

    # Cabecera empresarial
    cv2.putText(canvas, "IMPORTADORA & DISTRIBUIDORA ANDINA S.A.C.", (80, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (15, 15, 15), 2)
    cv2.putText(canvas, "RUC: 20601234567 - AV. LOS CONQUISTADORES 1040, LIMA", (80, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(canvas, "FACTURA ELECTRONICA: F001-00045892", (80, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(canvas, "FECHA DE EMISION: 28/10/2026 - MONEDA: PEN (S/)", (80, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)

    cv2.line(canvas, (80, 300), (width - 80, 300), (80, 80, 80), 2)

    # Tabla de items (10 filas representativas)
    headers = "ITEM  CODIGO     DESCRIPCION                           CANT    U.M.   P.UNIT     SUBTOTAL"
    cv2.putText(canvas, headers, (80, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
    cv2.line(canvas, (80, 375), (width - 80, 375), (150, 150, 150), 1)

    items_data = [
        ("1", "VALV-001", "VALVULA DE RETENCION CHECK 2 PULG", "5", "UND", "180.00", "900.00"),
        ("2", "TUBO-045", "TUBERIA DE ACERO INOXIDABLE SCH 40", "12", "UND", "85.00", "1020.00"),
        ("3", "EMP-088", "EMPAQUETADURA DE TEFLON INDUSTRIAL", "25", "PQ", "14.50", "362.50"),
        ("4", "MAN-012", "MANOMETRO GLICERINA 0-100 PSI 1/4", "6", "UND", "75.00", "450.00"),
        ("5", "FIL-034", "ELEMENTO FILTRANTE DE ACEITE 25UM", "8", "UND", "110.00", "880.00"),
        ("6", "BRI-099", "BRIDA FORJADA ANSI 150 RF 2 PULG", "10", "UND", "62.00", "620.00"),
        ("7", "ACE-500", "LUBRICANTE SINTETICO ISO VG 46 5GL", "3", "BAL", "340.00", "1020.00"),
        ("8", "TER-003", "TERMOMETRO BIMETALICO 0-150C POST", "4", "UND", "95.00", "380.00"),
        ("9", "PER-120", "PERNO HEXAGONAL G8 5/8 X 3 PULG", "80", "UND", "3.20", "256.00"),
        ("10", "RET-015", "RETEN NITRILO DOBLE LABIO 45X65X10", "15", "UND", "18.00", "270.00"),
    ]

    y_pos = 420
    for it in items_data:
        row_str = f"{it[0]:<5} {it[1]:<10} {it[2]:<37} {it[3]:<7} {it[4]:<6} {it[5]:<10} {it[6]}"
        cv2.putText(canvas, row_str, (80, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1)
        y_pos += 45

    # Totales
    cv2.line(canvas, (width - 550, y_pos + 20), (width - 80, y_pos + 20), (80, 80, 80), 2)
    cv2.putText(canvas, "SUBTOTAL:      S/  6,158.50", (width - 520, y_pos + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(canvas, "IGV (18%):     S/  1,108.53", (width - 520, y_pos + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(canvas, "TOTAL A PAGAR: S/  7,267.03", (width - 520, y_pos + 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Aplicar rotacion sintetica
    if abs(angle) > 0.01:
        center = (width // 2, height // 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        canvas = cv2.warpAffine(canvas, rot_mat, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    return canvas


def benchmark_preprocessor(test_image: np.ndarray, iterations: int = 25) -> Dict[str, Any]:
    """Mide la latencia de deskewing (Hough) y mejora CLAHE."""
    print("\n[1/4] Ejecutando benchmark de preprocesamiento de vision...")

    # Warm-up
    for _ in range(3):
        _ = detect_skew_angle(test_image)
        _ = enhance_contrast(test_image)

    # 1.1 Deskewing (Deteccion + Rotacion)
    deskew_times: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        ang = detect_skew_angle(test_image)
        _ = rotate_image(test_image, ang)
        deskew_times.append((time.perf_counter() - t0) * 1000.0)

    # 1.2 Contrast Enhancement (CLAHE)
    clahe_times: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = enhance_contrast(test_image)
        clahe_times.append((time.perf_counter() - t0) * 1000.0)

    total_preproc_times = [d + c for d, c in zip(deskew_times, clahe_times)]

    return {
        "iterations": iterations,
        "image_dimensions": f"{test_image.shape[1]}x{test_image.shape[0]}",
        "deskew_mean_ms": round(float(np.mean(deskew_times)), 2),
        "deskew_p95_ms": round(float(np.percentile(deskew_times, 95)), 2),
        "clahe_mean_ms": round(float(np.mean(clahe_times)), 2),
        "total_mean_ms": round(float(np.mean(total_preproc_times)), 2),
        "total_p95_ms": round(float(np.percentile(total_preproc_times, 95)), 2),
        "throughput_pages_sec": round(1000.0 / float(np.mean(total_preproc_times)), 2),
    }


def benchmark_spatial_ocr(test_image: np.ndarray, iterations: int = 5) -> Dict[str, Any]:
    """Mide latencia de EasyOCR CRAFT comparando GPU vs CPU."""
    print("\n[2/4] Ejecutando benchmark de OCR Espacial (GPU vs CPU)...")
    results: Dict[str, Any] = {}

    has_gpu = torch.cuda.is_available()

    # Evaluacion en GPU si esta disponible
    if has_gpu:
        print("  -> Inicializando motor OCR en GPU (CUDA)...")
        ocr_gpu = SpatialOCREngine(use_gpu=True)
        # Warmup
        _ = ocr_gpu.extract_tokens(test_image)
        torch.cuda.synchronize()

        gpu_times: List[float] = []
        token_count_gpu = 0
        for _ in range(iterations):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            res = ocr_gpu.extract_tokens(test_image)
            torch.cuda.synchronize()
            gpu_times.append((time.perf_counter() - t0) * 1000.0)
            token_count_gpu = len(res.tokens)

        results["gpu"] = {
            "device": torch.cuda.get_device_name(0),
            "iterations": iterations,
            "tokens_extracted": token_count_gpu,
            "mean_latency_ms": round(float(np.mean(gpu_times)), 2),
            "median_latency_ms": round(float(np.median(gpu_times)), 2),
            "p95_latency_ms": round(float(np.percentile(gpu_times, 95)), 2),
            "min_latency_ms": round(float(np.min(gpu_times)), 2),
            "throughput_pages_min": round(60000.0 / float(np.mean(gpu_times)), 2),
        }
    else:
        results["gpu"] = None

    # Evaluacion en CPU
    print("  -> Inicializando motor OCR en CPU (PyTorch Threads)...")
    ocr_cpu = SpatialOCREngine(use_gpu=False)
    # Warmup
    _ = ocr_cpu.extract_tokens(test_image)

    cpu_times: List[float] = []
    token_count_cpu = 0
    # CPU suele ser mas lenta, limitamos iteraciones a 3 si no se especifico
    cpu_iters = min(iterations, 3)
    for _ in range(cpu_iters):
        t0 = time.perf_counter()
        res = ocr_cpu.extract_tokens(test_image)
        cpu_times.append((time.perf_counter() - t0) * 1000.0)
        token_count_cpu = len(res.tokens)

    results["cpu"] = {
        "device": f"CPU ({platform.processor() or 'Host CPU'})",
        "iterations": cpu_iters,
        "tokens_extracted": token_count_cpu,
        "mean_latency_ms": round(float(np.mean(cpu_times)), 2),
        "median_latency_ms": round(float(np.median(cpu_times)), 2),
        "p95_latency_ms": round(float(np.percentile(cpu_times, 95)), 2),
        "min_latency_ms": round(float(np.min(cpu_times)), 2),
        "throughput_pages_min": round(60000.0 / float(np.mean(cpu_times)), 2),
    }

    if has_gpu and results["gpu"]:
        speedup = results["cpu"]["mean_latency_ms"] / results["gpu"]["mean_latency_ms"]
        results["gpu_speedup_factor"] = round(speedup, 2)
    else:
        results["gpu_speedup_factor"] = 1.0

    return results


def benchmark_embeddings(iterations: int = 20) -> Dict[str, Any]:
    """Mide throughput y latencia de inferencia de sentence-transformers."""
    print("\n[3/4] Ejecutando benchmark de embeddings densos (all-MiniLM-L6-v2)...")

    sample_queries = [
        "Factura distribuidora andina repuestos valvulas industriales octubre 2026",
        "Guia de remision de remitente por transporte de tuberia acero inoxidable",
        "Constancia de transferencia bancaria BCP pago a proveedores cuenta corriente soles",
        "Filtro de aire industrial y manometro de presion diferencial sch 40",
        "Comprobante fiscal retenciones igv exonerado subtotal y total facturado",
        "Acta de conformidad de recepcion de mercaderia en almacen central callao",
        "Nota de credito electronica modificacion de valor monetario",
        "Detalle de linea de item cantidad precio unitario descripcion arancelaria",
    ]

    has_gpu = torch.cuda.is_available()
    devices = ["cuda", "cpu"] if has_gpu else ["cpu"]
    batch_sizes = [1, 8, 32, 64]

    results: Dict[str, Any] = {}

    for dev in devices:
        print(f"  -> Evaluando embeddings en {dev.upper()}...")
        engine = EmbeddingEngine(device=dev)
        # Warmup
        _ = engine.embed_text("Warmup text string for embedding initialization")
        if dev == "cuda":
            torch.cuda.synchronize()

        dev_results: Dict[str, Any] = {}

        for bs in batch_sizes:
            # Crear batch multiplicando queries
            batch_texts = (sample_queries * ((bs // len(sample_queries)) + 1))[:bs]

            latencies: List[float] = []
            for _ in range(iterations):
                if dev == "cuda":
                    torch.cuda.synchronize()
                t0 = time.perf_counter()
                _ = engine.embed_batch(batch_texts)
                if dev == "cuda":
                    torch.cuda.synchronize()
                latencies.append((time.perf_counter() - t0) * 1000.0)

            mean_ms = float(np.mean(latencies))
            throughput = (bs / mean_ms) * 1000.0  # items/sec

            dev_results[f"batch_{bs}"] = {
                "batch_size": bs,
                "mean_latency_ms": round(mean_ms, 2),
                "latency_per_item_ms": round(mean_ms / bs, 3),
                "throughput_vectors_sec": round(throughput, 1),
            }

        results[dev] = dev_results

    return results


def benchmark_reconciler(iterations: int = 1000) -> Dict[str, Any]:
    """Mide la latencia y rendimiento del motor de conciliacion de 3 vias."""
    print(f"\n[4/4] Ejecutando benchmark de reconciliador de 3 vias ({iterations} iteraciones)...")

    catalog_descriptions = [
        "VALVULA DE RETENCION CHECK 2 PULG",
        "TUBERIA DE ACERO INOXIDABLE SCH 40",
        "EMPAQUETADURA DE TEFLON INDUSTRIAL",
        "MANOMETRO GLICERINA 0-100 PSI 1/4",
        "ELEMENTO FILTRANTE DE ACEITE 25UM",
        "BRIDA FORJADA ANSI 150 RF 2 PULG",
        "LUBRICANTE SINTETICO ISO VG 46 5GL",
        "TERMOMETRO BIMETALICO 0-150C POST",
        "PERNO HEXAGONAL G8 5/8 X 3 PULG",
        "RETEN NITRILO DOBLE LABIO 45X65X10",
    ]

    # Crear dataset representativo
    items: List[LineItemExtraction] = []
    for i in range(1, 11):
        qty = float(i * 2)
        unit_p = 50.0 + (i * 10.0)
        line_tot = round(qty * unit_p, 2)
        items.append(
            LineItemExtraction(
                item_number=i,
                sku=f"COD-{i:03d}",
                description=catalog_descriptions[i - 1],
                quantity=qty,
                unit_price=unit_p,
                line_total=line_tot,
            )
        )

    subtotal = round(sum(it.line_total for it in items), 2)
    tax_amount = round(subtotal * 0.18, 2)
    total_amount = round(subtotal + tax_amount, 2)

    invoice = InvoiceExtraction(
        supplier_ruc="20601234567",
        supplier_name="DISTRIBUIDORA ANDINA INDUSTRIAL S.A.C.",
        invoice_number="F001-00045892",
        issue_date=date(2026, 10, 28),
        currency="PEN",
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        line_items=items,
    )

    # 2 guias de remision que completan el despacho
    guide1_items: List[LineItemExtraction] = []
    guide2_items: List[LineItemExtraction] = []
    for it in items:
        q1 = float(int(it.quantity // 2))
        t1 = round(q1 * it.unit_price, 2)
        guide1_items.append(
            LineItemExtraction(
                item_number=it.item_number,
                sku=it.sku,
                description=it.description,
                quantity=q1,
                unit_price=it.unit_price,
                line_total=t1,
            )
        )

        q2 = it.quantity - q1
        t2 = round(q2 * it.unit_price, 2)
        guide2_items.append(
            LineItemExtraction(
                item_number=it.item_number,
                sku=it.sku,
                description=it.description,
                quantity=q2,
                unit_price=it.unit_price,
                line_total=t2,
            )
        )

    guide1 = ShippingGuideExtraction(
        guide_number="T001-000124",
        sender_ruc="20601234567",
        recipient_ruc="20100045891",
        issue_date=date(2026, 10, 28),
        items=guide1_items,
    )
    guide2 = ShippingGuideExtraction(
        guide_number="T001-000125",
        sender_ruc="20601234567",
        recipient_ruc="20100045891",
        issue_date=date(2026, 10, 29),
        items=guide2_items,
    )

    voucher = PaymentVoucherExtraction(
        bank_name="BANCO DE CREDITO DEL PERU",
        operation_number="OP-98765432",
        payment_date=date(2026, 10, 30),
        amount=total_amount,
        currency="PEN",
    )

    reconciler = ThreeWayReconciler(tolerance=0.05)

    # Warmup
    _ = reconciler.reconcile(invoice, [guide1, guide2], [voucher])

    latencies_us: List[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        report = reconciler.reconcile(invoice, [guide1, guide2], [voucher])
        latencies_us.append((time.perf_counter() - t0) * 1_000_000.0)

    mean_us = float(np.mean(latencies_us))
    p95_us = float(np.percentile(latencies_us, 95))
    p99_us = float(np.percentile(latencies_us, 99))

    return {
        "iterations": iterations,
        "items_per_invoice": len(items),
        "shipping_guides_count": 2,
        "payment_vouchers_count": 1,
        "report_status": report.status.value,
        "math_valid": report.math_valid,
        "goods_matched": report.goods_matched,
        "payment_matched": report.payment_matched,
        "mean_latency_microseconds": round(mean_us, 1),
        "mean_latency_ms": round(mean_us / 1000.0, 3),
        "p95_latency_ms": round(p95_us / 1000.0, 3),
        "p99_latency_ms": round(p99_us / 1000.0, 3),
        "throughput_reconciliations_sec": round(1_000_000.0 / mean_us, 1),
    }


def print_senior_summary_tables(hw: Dict[str, Any], preproc: Dict[str, Any], ocr: Dict[str, Any], emb: Dict[str, Any], rec: Dict[str, Any]) -> None:
    """Imprime resumen ejecutivo y tablas de benchmark en consola."""
    separator = "=" * 80
    print("\n" + separator)
    print("DOCUMIND FINANCIAL AI - BENCHMARK DE RENDIMIENTO TECNICO")
    print(separator)
    print(f"Fecha de Ejecucion : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Sistema Operativo  : {hw['os']}")
    print(f"CPU Host           : {hw['cpu']}")
    print(f"Acelerador GPU     : {hw['gpu_name']} ({hw.get('gpu_vram_gb', 0)} GB VRAM)")
    print(f"Entorno PyTorch    : v{hw['pytorch']} (CUDA: {hw['cuda_available']})")
    print(separator)

    # 1. Vision Preprocessor
    print("\n1. PREPROCESAMIENTO Y CORRECCION ESPACIAL (HOUGH DESKEW + CLAHE)")
    print("-" * 80)
    print(f"  Resolucion de Prueba : {preproc['image_dimensions']} px (300 DPI)")
    print(f"  Muestreo Estadistico : {preproc['iterations']} iteraciones")
    print(f"  Deskewing (Hough)    : {preproc['deskew_mean_ms']:>8.2f} ms (p95: {preproc['deskew_p95_ms']:.2f} ms)")
    print(f"  CLAHE Enhancement    : {preproc['clahe_mean_ms']:>8.2f} ms")
    print(f"  Pipeline Total       : {preproc['total_mean_ms']:>8.2f} ms (Throughput: {preproc['throughput_pages_sec']:.1f} pag/seg)")

    # 2. Spatial OCR
    print("\n2. EXTRACCION OCR ESPACIAL CON EASYOCR CRAFT (GPU VS CPU)")
    print("-" * 80)
    header_ocr = f"{'Dispositivo':<32} | {'Tokens':<8} | {'Media (ms)':<12} | {'p95 (ms)':<10} | {'Pag/Min':<10}"
    print(header_ocr)
    print("-" * 80)
    if ocr["gpu"]:
        g = ocr["gpu"]
        print(f"{g['device'][:32]:<32} | {g['tokens_extracted']:<8} | {g['mean_latency_ms']:>10.2f} ms | {g['p95_latency_ms']:>8.2f} ms | {g['throughput_pages_min']:>8.1f}")
    c = ocr["cpu"]
    print(f"{c['device'][:32]:<32} | {c['tokens_extracted']:<8} | {c['mean_latency_ms']:>10.2f} ms | {c['p95_latency_ms']:>8.2f} ms | {c['throughput_pages_min']:>8.1f}")
    print("-" * 80)
    if ocr.get("gpu_speedup_factor"):
        print(f"  Factor de Aceleracion Hardware (GPU vs CPU): {ocr['gpu_speedup_factor']:.2f}x mas rapido en GPU")

    # 3. Dense Embeddings
    print("\n3. VECTORIZACION SEMANTICA 384D (all-MiniLM-L6-v2)")
    print("-" * 80)
    header_emb = f"{'Dispositivo':<10} | {'Batch Size':<12} | {'Latencia Batch':<16} | {'Por Item':<12} | {'Throughput':<16}"
    print(header_emb)
    print("-" * 80)
    for dev, batch_dict in emb.items():
        for b_name, b_val in batch_dict.items():
            print(
                f"{dev.upper():<10} | {b_val['batch_size']:<12} | "
                f"{b_val['mean_latency_ms']:>12.2f} ms | "
                f"{b_val['latency_per_item_ms']:>9.3f} ms | "
                f"{b_val['throughput_vectors_sec']:>11.1f} vec/s"
            )
    print("-" * 80)

    # 4. Three-Way Reconciler
    print("\n4. MOTOR DE CONCILIACION DE 3 VIAS (ThreeWayReconciler)")
    print("-" * 80)
    print(f"  Complejidad de Prueba : 1 Factura (10 line items) + 2 Guias de Remision + 1 Voucher")
    print(f"  Iteraciones Medidas   : {rec['iterations']} evaluaciones completas")
    print(f"  Resultado de Auditoria: {rec['report_status']} (Math Valid: {rec['math_valid']}, Goods: {rec['goods_matched']}, Pay: {rec['payment_matched']})")
    print(f"  Latencia Media        : {rec['mean_latency_ms']:>8.3f} ms ({rec['mean_latency_microseconds']:.1f} microsegundos)")
    print(f"  Latencia Percentil 95 : {rec['p95_latency_ms']:>8.3f} ms")
    print(f"  Throughput de Auditoria: {rec['throughput_reconciliations_sec']:>8.1f} expedientes/seg")
    print(separator + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de Rendimiento para DocuMind Financial AI")
    parser.add_argument("--ocr-iterations", type=int, default=5, help="Iteraciones para benchmark OCR")
    parser.add_argument("--save-json", type=str, default="benchmark_results.json", help="Ruta de guardado para metricas JSON")
    args = parser.parse_args()

    print("[DocuMind] Iniciando Suite de Benchmarking de Rendimiento...")
    hw_info = get_hardware_info()
    test_img = generate_benchmark_page(width=1200, height=1600, angle=4.5)

    preproc_res = benchmark_preprocessor(test_img, iterations=25)
    ocr_res = benchmark_spatial_ocr(test_img, iterations=args.ocr_iterations)
    emb_res = benchmark_embeddings(iterations=15)
    rec_res = benchmark_reconciler(iterations=1000)

    print_senior_summary_tables(hw_info, preproc_res, ocr_res, emb_res, rec_res)

    # Guardar reporte JSON estructurado
    benchmark_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hardware": hw_info,
        "vision_preprocessor": preproc_res,
        "spatial_ocr": ocr_res,
        "dense_embeddings": emb_res,
        "three_way_reconciler": rec_res,
    }

    output_path = BACKEND_DIR / args.save_json
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"[OK] Reporte completo exportado exitosamente a: {output_path}")


if __name__ == "__main__":
    main()
