"""Generador de los 3 Flujos de Prueba Oficiales para DocuMind Financial AI.

Crea tres carpetas con comprobantes listos para arrastrar en la interfaz web (http://localhost:3000):
1. Flujo 1: Expediente 100% Conciliado (Happy Path - Semaforo Verde).
2. Flujo 2: Discrepancia Fisica en Almacen (Faltante de Mercaderia / Shortage - Alerta Naranja).
3. Flujo 3: Discrepancia Financiera (Pago Parcial y Saldo Pendiente - Alerta Roja).
"""

from pathlib import Path
import cv2
import numpy as np

OUTPUT_BASE = Path(__file__).resolve().parent.parent / "data" / "samples" / "flujos_de_prueba"


def draw_invoice(filename: Path, items: list[tuple[str, str, str, str, str]], subtotal: float, igv: float, total: float, angle: float = 3.0):
    w, h = 1000, 1400
    img = np.full((h, w, 3), 255, dtype=np.uint8)

    cv2.putText(img, "CORPORACION INDUSTRIAL FERRETERA S.A.C.", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(img, "RUC: 20491028491 - AV. MATERIALES 2040, LIMA", (70, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    cv2.putText(img, f"FACTURA ELECTRONICA: F001-0009581", (70, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(img, "FECHA: 28/10/2026 - MONEDA: PEN (SOLES)", (70, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    cv2.line(img, (70, 255), (w - 70, 255), (100, 100, 100), 2)

    headers = "ITEM  DESCRIPCION                           CANT    U.M.   P.UNIT     TOTAL"
    cv2.putText(img, headers, (70, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
    cv2.line(img, (70, 330), (w - 70, 330), (160, 160, 160), 1)

    y = 380
    for it in items:
        row = f"{it[0]:<5} {it[1]:<37} {it[2]:<7} {it[3]:<6} {it[4]:<10} {it[5]}"
        cv2.putText(img, row, (70, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
        y += 60

    cv2.line(img, (w - 480, y + 20), (w - 70, y + 20), (100, 100, 100), 2)
    cv2.putText(img, f"SUBTOTAL:      S/ {subtotal:,.2f}", (w - 450, y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(img, f"IGV (18%):     S/ {igv:,.2f}", (w - 450, y + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)
    cv2.putText(img, f"TOTAL FACTURA: S/ {total:,.2f}", (w - 450, y + 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    if abs(angle) > 0.01:
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    filename.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(filename), img)


def draw_shipping_guide(filename: Path, items: list[tuple[str, str, str, str]], received_status: str = "RECIBIDO CONFORME", angle: float = -2.5):
    w, h = 1000, 1400
    img = np.full((h, w, 3), 255, dtype=np.uint8)

    cv2.putText(img, "CORPORACION INDUSTRIAL FERRETERA S.A.C.", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(img, "GUIA DE REMISION DE REMITENTE: T001-0005820", (70, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(img, "RUC REMITENTE: 20491028491 - RUC DESTINATARIO: 20100045891", (70, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    cv2.putText(img, "PUNTO DE LLEGADA: ALMACEN CENTRAL CARRETERA CENTRAL KM 12", (70, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    cv2.line(img, (70, 265), (w - 70, 265), (100, 100, 100), 2)

    headers = "ITEM  CODIGO     DESCRIPCION FISICA ENTREGADA         CANTIDAD  U.M."
    cv2.putText(img, headers, (70, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
    cv2.line(img, (70, 335), (w - 70, 335), (160, 160, 160), 1)

    y = 390
    for it in items:
        row = f"{it[0]:<5} {it[1]:<10} {it[2]:<36} {it[3]:<9} {it[4]}"
        cv2.putText(img, row, (70, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
        y += 65

    # Sello de almacen
    cv2.rectangle(img, (70, y + 40), (480, y + 160), (120, 120, 120), 2)
    cv2.putText(img, "CONTROL DE ALMACEN CENTRAL", (85, y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 50), 2)
    color_sello = (0, 130, 0) if "CONFORME" in received_status else (0, 0, 180)
    cv2.putText(img, received_status, (85, y + 120), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color_sello, 2)

    if abs(angle) > 0.01:
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    filename.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(filename), img)


def draw_payment_voucher(filename: Path, amount: float, operation_num: str = "OP-7749102", angle: float = 1.5):
    w, h = 900, 1200
    img = np.full((h, w, 3), 255, dtype=np.uint8)

    cv2.putText(img, "BANCO DE CREDITO DEL PERU - BCP", (60, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (10, 30, 100), 2)
    cv2.putText(img, "CONSTANCIA DE TRANSFERENCIA BANCARIA", (60, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (50, 50, 50), 2)
    cv2.line(img, (60, 190), (w - 60, 190), (10, 30, 100), 3)

    cv2.putText(img, f"NUMERO DE OPERACION:  {operation_num}", (60, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
    cv2.putText(img, "FECHA DE OPERACION:   30/10/2026 11:20:05", (60, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)
    cv2.putText(img, "BENEFICIARIO:         CORPORACION INDUSTRIAL FERRETERA", (60, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    cv2.putText(img, "MONEDA DE PAGO:       PEN (SOLES)", (60, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (40, 40, 40), 2)
    cv2.line(img, (60, 450), (w - 60, 450), (150, 150, 150), 1)

    cv2.putText(img, "IMPORTE TOTAL TRANSFERIDO:", (60, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2)
    cv2.putText(img, f"S/ {amount:,.2f}", (480, 520), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 120, 0), 3)
    cv2.putText(img, "ESTADO: OPERACION LIQUIDADA EXITOSAMENTE", (60, 590), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 120, 0), 2)

    if abs(angle) > 0.01:
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    filename.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(filename), img)


def generate_all_flows():
    print("=" * 80)
    print("DOCUMIND FINANCIAL AI - GENERADOR DE COMPROBANTES PARA LOS 3 FLUJOS")
    print("=" * 80)

    # -------------------------------------------------------------
    # FLUJO 1: CONCILIADO 100% (Happy Path - Semaforo Verde)
    # -------------------------------------------------------------
    dir_1 = OUTPUT_BASE / "1_flujo_conciliado_exitoso"
    print("\n[Generando Flujo 1]: Expediente 100% Conciliado...")
    items_1 = [
        ("01", "VALVULA DE CONTROL 1/2 PULG", "4.00", "UND", "120.00", "480.00"),
        ("02", "MANOMETRO DE PRESION DIFERENCIAL", "2.00", "UND", "350.00", "700.00"),
    ]
    guide_items_1 = [
        ("01", "COD-01", "VALVULA DE CONTROL 1/2 PULG", "4.00", "UND"),
        ("02", "COD-02", "MANOMETRO DE PRESION DIFERENCIAL", "2.00", "UND"),
    ]
    draw_invoice(dir_1 / "1_factura_f001_0009581.png", items_1, 1180.00, 212.40, 1392.40)
    draw_shipping_guide(dir_1 / "2_guia_remision_completa.png", guide_items_1, "MERCADERIA RECIBIDA COMPLETA")
    draw_payment_voucher(dir_1 / "3_voucher_pago_total.png", 1392.40)
    print(f"  -> Guardado en: {dir_1}")

    # -------------------------------------------------------------
    # FLUJO 2: DISCREPANCIA FISICA (Faltante de Almacen)
    # Factura factura 10 tuberias, pero la guia solo recibe 6 (Faltan 4!)
    # -------------------------------------------------------------
    dir_2 = OUTPUT_BASE / "2_flujo_discrepancia_almacen"
    print("\n[Generando Flujo 2]: Discrepancia Fisica en Almacen (Faltante)...")
    items_2 = [
        ("01", "TUBERIA DE ACERO INOXIDABLE SCH 40", "10.00", "UND", "85.00", "850.00"),
        ("02", "BRIDA FORJADA ANSI 150 RF 2 PULG", "5.00", "UND", "62.00", "310.00"),
    ]
    guide_items_2 = [
        ("01", "COD-TUB", "TUBERIA DE ACERO INOXIDABLE SCH 40", "6.00", "UND"),  # Faltan 4!
        ("02", "COD-BRI", "BRIDA FORJADA ANSI 150 RF 2 PULG", "5.00", "UND"),
    ]
    draw_invoice(dir_2 / "1_factura_10_tuberias.png", items_2, 1160.00, 208.80, 1368.80)
    draw_shipping_guide(dir_2 / "2_guia_recepcion_incompleta.png", guide_items_2, "RECEPCION PARCIAL CON FALTANTE")
    draw_payment_voucher(dir_2 / "3_voucher_bancario.png", 1368.80)
    print(f"  -> Guardado en: {dir_2}")

    # -------------------------------------------------------------
    # FLUJO 3: DISCREPANCIA FINANCIERA (Pago Parcial y Saldo Pendiente)
    # Factura por S/ 2,360.00, pero voucher solo transfiere S/ 1,500.00 (Saldo: S/ 860.00)
    # -------------------------------------------------------------
    dir_3 = OUTPUT_BASE / "3_flujo_pago_parcial_saldo_pendiente"
    print("\n[Generando Flujo 3]: Discrepancia Financiera (Pago Parcial)...")
    items_3 = [
        ("01", "ELEMENTO FILTRANTE DE ACEITE 25UM", "8.00", "UND", "110.00", "880.00"),
        ("02", "LUBRICANTE SINTETICO ISO VG 46 5GL", "3.00", "BAL", "340.00", "1020.00"),
    ]
    guide_items_3 = [
        ("01", "COD-FIL", "ELEMENTO FILTRANTE DE ACEITE 25UM", "8.00", "UND"),
        ("02", "COD-LUB", "LUBRICANTE SINTETICO ISO VG 46 5GL", "3.00", "BAL"),
    ]
    draw_invoice(dir_3 / "1_factura_total_2360.png", items_3, 1900.00, 342.00, 2242.00)
    draw_shipping_guide(dir_3 / "2_guia_recepcion_total.png", guide_items_3, "MERCADERIA RECIBIDA COMPLETA")
    draw_payment_voucher(dir_3 / "3_voucher_pago_incompleto.png", 1500.00)  # Saldo pendiente de S/ 742.00!
    print(f"  -> Guardado en: {dir_3}")

    print("\n" + "=" * 80)
    print("EXITO: Los 3 juegos de comprobantes estan listos para auditar.")
    print("=" * 80)


if __name__ == "__main__":
    generate_all_flows()
