import argparse
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Add src to path so script can run from repository root or backend folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.vision.preprocessor import DocumentPreprocessor
from src.vision.spatial_ocr import SpatialOCREngine


def generate_sample_invoice(angle: float = 6.5, width: int = 900, height: int = 1200) -> np.ndarray:
    image = np.full((height, width, 3), 255, dtype=np.uint8)

    # Header
    cv2.putText(image, "DISTRIBUIDORA INDUSTRIAL S.A.C.", (60, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(image, "RUC: 20549812341", (60, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(image, "FACTURA ELECTRONICA: F001-0008492", (60, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(image, "FECHA EMISION: 28/10/2026", (60, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)

    # Line separator
    cv2.line(image, (60, 240), (840, 240), (100, 100, 100), 2)

    # Table items
    items = [
        ("001", "VALVULA DE CONTROL 1/2 PULG", "4", "120.00", "480.00"),
        ("002", "MANOMETRO DE PRESION DIFERENCIAL", "2", "350.00", "700.00"),
        ("003", "FILTRO DE AIRE INDUSTRIAL 10UM", "10", "45.00", "450.00"),
    ]

    y = 300
    cv2.putText(image, "ITEM   DESCRIPCION                           CANT    P.UNIT     TOTAL", (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    y += 20
    cv2.line(image, (60, y), (840, y), (180, 180, 180), 1)

    for item_id, desc, qty, price, total in items:
        y += 50
        row_text = f"{item_id:<6} {desc:<36} {qty:<7} {price:<10} {total}"
        cv2.putText(image, row_text, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1)

    # Total section
    y += 80
    cv2.line(image, (500, y), (840, y), (100, 100, 100), 2)
    y += 40
    cv2.putText(image, "SUBTOTAL:    S/ 1,630.00", (520, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
    y += 35
    cv2.putText(image, "IGV (18%):   S/   293.40", (520, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
    y += 40
    cv2.putText(image, "TOTAL:       S/ 1,923.40", (520, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2)

    # Artificial tilt / skew
    if abs(angle) > 0.01:
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

    return image


def run_pipeline(
    input_path: str | None = None,
    output_dir: str = "output_demo",
    min_confidence: float = 0.20,
) -> None:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    preprocessor = DocumentPreprocessor(target_dpi=300, enable_clahe=True)
    ocr_engine = SpatialOCREngine(min_confidence=min_confidence)

    print("=================================================================")
    print("      DOCUMIND FINANCIAL AI - DEMOSTRACION DE PIPELINE          ")
    print("=================================================================")
    print(f"Dispositivo GPU disponible: {ocr_engine.use_gpu}")

    if input_path:
        file = Path(input_path)
        print(f"Cargando archivo: {file.resolve()}")
        pages = preprocessor.process_file(file)
    else:
        print("Generando comprobante de prueba sintetico con inclinacion (+6.5 grados)...")
        raw_image = generate_sample_invoice(angle=6.5)
        raw_path = out_path / "1_original_inclinado.png"
        cv2.imwrite(str(raw_path), raw_image)
        print(f"Imagen original guardada en: {raw_path}")
        pages = [preprocessor.process_image(raw_image, page_number=1)]

    for page in pages:
        print("\n-----------------------------------------------------------------")
        print(f"Procesando Pagina {page.page_number} ({page.width}x{page.height} px)")
        print(f"Angulo de inclinacion detectado: {page.original_skew_angle:+.2f} grados")

        corrected_path = out_path / f"2_deskewed_pagina_{page.page_number}.png"
        cv2.imwrite(str(corrected_path), page.image)
        print(f"Imagen corregida y contrastada guardada en: {corrected_path}")

        print("\nEjecutando OCR Espacial acelerado por CUDA...")
        t0 = time.perf_counter()
        ocr_result = ocr_engine.extract_tokens(page.image, page_number=page.page_number)
        ocr_time = (time.perf_counter() - t0) * 1000

        print(f"OCR finalizado en {ocr_time:.1f} ms. Tokens detectados: {len(ocr_result.tokens)}")
        print("\nTokens extraidos (Muestra de primeros 10):")
        print(f"{'TEXTO':<30} | {'CONF':<6} | {'BBOX [ymin, xmin, ymax, xmax]'}")
        print("-" * 70)
        for token in ocr_result.tokens[:10]:
            print(f"{token.text[:30]:<30} | {token.confidence:0.2f}   | {token.bbox}")

        # Render annotated image with bounding boxes
        annotated = page.image.copy()
        for token in ocr_result.tokens:
            pts = np.array(token.raw_box, np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [pts], isClosed=True, color=(0, 180, 0), thickness=2)

        annotated_path = out_path / f"3_annotated_ocr_pagina_{page.page_number}.png"
        cv2.imwrite(str(annotated_path), annotated)
        print(f"\nImagen con cajas espaciales superpuestas: {annotated_path}")

    print("\n=================================================================")
    print("Pipeline ejecutado exitosamente. Archivos generados en:", out_path.resolve())
    print("=================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo del Pipeline de Vision y OCR de DocuMind Financial AI")
    parser.add_argument("--input", "-i", type=str, default=None, help="Ruta a PDF o imagen para procesar (opcional)")
    parser.add_argument("--outdir", "-o", type=str, default="output_demo", help="Directorio para guardar imagenes procesadas")
    parser.add_argument("--conf", "-c", type=float, default=0.15, help="Umbral minimo de confianza OCR (default: 0.15)")
    args = parser.parse_args()

    run_pipeline(input_path=args.input, output_dir=args.outdir, min_confidence=args.conf)
