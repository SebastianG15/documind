from datetime import date
import pytest

from src.nlp.entity_extractor import EntityExtractor
from src.nlp.schemas import (
    InvoiceExtraction,
    PaymentVoucherExtraction,
    ShippingGuideExtraction,
)
from src.vision.spatial_ocr import OCRResult, SpatialToken


def _make_token(text: str, bbox: tuple[int, int, int, int], conf: float = 0.95) -> SpatialToken:
    return SpatialToken(
        text=text,
        confidence=conf,
        bbox=bbox,
        raw_box=[[bbox[1], bbox[0]], [bbox[3], bbox[0]], [bbox[3], bbox[2]], [bbox[1], bbox[2]]],
    )


def test_extract_invoice_from_tokens():
    tokens = [
        _make_token("DISTRIBUIDORA INDUSTRIAL S.A.C.", (87, 113, 112, 500)),
        _make_token("RUC: 20549812341", (121, 113, 141, 309)),
        _make_token("FACTURA ELECTRONICA: F001-0008492", (151, 113, 172, 504)),
        _make_token("FECHA EMISION: 28/10/2026", (185, 113, 203, 354)),
        _make_token("MONEDA: SOLES", (185, 400, 203, 520)),
        # Encabezado de tabla
        _make_token("ITEM", (255, 114, 271, 150)),
        _make_token("DESCRIPCION", (255, 170, 271, 350)),
        _make_token("CANT", (255, 367, 271, 413)),
        _make_token("P.UNIT", (255, 423, 271, 478)),
        _make_token("TOTAL", (255, 492, 271, 544)),
        # Fila 1
        _make_token("001", (310, 114, 328, 146)),
        _make_token("VALVULA DE CONTROL 1/2 PULG", (309, 154, 327, 350)),
        _make_token("4.00", (310, 370, 328, 410)),
        _make_token("120.00", (310, 430, 328, 475)),
        _make_token("480.00", (310, 495, 328, 540)),
        # Fila 2
        _make_token("002", (340, 114, 358, 146)),
        _make_token("MANOMETRO DE PRESION", (339, 154, 357, 340)),
        _make_token("2.00", (340, 370, 358, 410)),
        _make_token("350.00", (340, 430, 358, 475)),
        _make_token("700.00", (340, 495, 358, 540)),
        # Totales
        _make_token("SUBTOTAL: 1180.00", (430, 350, 450, 540)),
        _make_token("IGV (18%): 212.40", (460, 350, 480, 540)),
        _make_token("TOTAL A PAGAR: 1392.40", (490, 350, 510, 540)),
    ]

    ocr_result = OCRResult(
        page_number=1,
        tokens=tokens,
        full_text=" ".join(t.text for t in tokens),
        width=1000,
        height=1400,
    )

    extractor = EntityExtractor()
    invoice = extractor.extract_invoice(ocr_result)

    assert isinstance(invoice, InvoiceExtraction)
    assert invoice.supplier_ruc == "20549812341"
    assert "DISTRIBUIDORA INDUSTRIAL" in invoice.supplier_name
    assert invoice.invoice_number == "F001-0008492"
    assert invoice.issue_date == date(2026, 10, 28)
    assert invoice.currency == "PEN"
    assert invoice.subtotal == 1180.00
    assert invoice.tax_amount == 212.40
    assert invoice.total_amount == 1392.40
    assert len(invoice.line_items) == 2
    assert invoice.line_items[0].description == "VALVULA DE CONTROL 1/2 PULG"
    assert invoice.line_items[0].quantity == 4.0
    assert invoice.line_items[0].unit_price == 120.00
    assert invoice.line_items[0].line_total == 480.00
    assert invoice.header_bbox is not None


def test_extract_shipping_guide_from_tokens():
    tokens = [
        _make_token("TRANSPORTE LOGISTICO NACIONAL S.A.", (70, 100, 95, 450)),
        _make_token("RUC REMITENTE: 20100454521", (105, 100, 125, 320)),
        _make_token("RUC DESTINATARIO: 20549812341", (130, 100, 150, 350)),
        _make_token("GUIA DE REMISION REMITENTE: T001-000452", (160, 100, 180, 480)),
        _make_token("FECHA DE EMISION: 27/10/2026", (190, 100, 210, 350)),
        _make_token("PUNTO DE PARTIDA: AV. INDUSTRIAL 1200 CALLAO", (220, 100, 240, 520)),
        _make_token("PUNTO DE LLEGADA: CARRETERA CENTRAL KM 15 ATE", (250, 100, 270, 530)),
        # Items transportados
        _make_token("1", (320, 100, 338, 130)),
        _make_token("VALVULA DE CONTROL 1/2 PULG", (320, 140, 338, 380)),
        _make_token("4.00", (320, 400, 338, 440)),
        _make_token("2", (350, 100, 368, 130)),
        _make_token("MANOMETRO DE PRESION", (350, 140, 368, 370)),
        _make_token("2.00", (350, 400, 368, 440)),
    ]

    ocr_result = OCRResult(
        page_number=1,
        tokens=tokens,
        full_text=" ".join(t.text for t in tokens),
        width=1000,
        height=1400,
    )

    extractor = EntityExtractor()
    guide = extractor.extract_shipping_guide(ocr_result)

    assert isinstance(guide, ShippingGuideExtraction)
    assert guide.guide_number == "T001-000452"
    assert guide.sender_ruc == "20100454521"
    assert guide.recipient_ruc == "20549812341"
    assert guide.issue_date == date(2026, 10, 27)
    assert "AV. INDUSTRIAL 1200" in (guide.origin_address or "")
    assert "CARRETERA CENTRAL" in (guide.destination_address or "")
    assert len(guide.items) == 2
    assert guide.items[0].quantity == 4.0
    assert guide.items[1].quantity == 2.0


def test_extract_payment_voucher_from_tokens():
    tokens = [
        _make_token("BANCO DE CREDITO BCP", (100, 200, 130, 450)),
        _make_token("CONSTANCIA DE TRANSFERENCIA BANCARIA", (140, 150, 165, 520)),
        _make_token("NUMERO DE OPERACION: 88472910", (180, 150, 205, 450)),
        _make_token("FECHA: 29/10/2026", (220, 150, 240, 320)),
        _make_token("CUENTA ORIGEN: 191-23456789-0-12", (260, 150, 280, 450)),
        _make_token("CUENTA DESTINO: 191-98765432-1-45", (300, 150, 320, 460)),
        _make_token("MONTO: S/ 1392.40", (340, 150, 370, 360)),
    ]

    ocr_result = OCRResult(
        page_number=1,
        tokens=tokens,
        full_text=" ".join(t.text for t in tokens),
        width=1000,
        height=1400,
    )

    extractor = EntityExtractor()
    voucher = extractor.extract_payment_voucher(ocr_result)

    assert isinstance(voucher, PaymentVoucherExtraction)
    assert "BCP" in voucher.bank_name.upper()
    assert voucher.operation_number == "88472910"
    assert voucher.amount == 1392.40
    assert voucher.currency == "PEN"
    assert voucher.payment_date == date(2026, 10, 29)
    assert voucher.source_account is not None
    assert voucher.destination_account is not None


def test_extract_invoice_with_dollar_currency():
    tokens = [
        _make_token("GLOBAL PARTS CORP", (80, 100, 105, 350)),
        _make_token("RUC: 20456789012", (115, 100, 135, 290)),
        _make_token("FACTURA: E001-000312", (145, 100, 165, 340)),
        _make_token("FECHA: 2026-10-25", (175, 100, 195, 310)),
        _make_token("MONEDA: DOLARES AMERICANOS (USD)", (205, 100, 225, 480)),
        _make_token("SUBTOTAL: USD 500.00", (300, 300, 320, 500)),
        _make_token("IGV: 90.00", (330, 300, 350, 500)),
        _make_token("TOTAL: 590.00", (360, 300, 380, 500)),
    ]

    ocr_result = OCRResult(
        page_number=1,
        tokens=tokens,
        full_text=" ".join(t.text for t in tokens),
        width=1000,
        height=1400,
    )

    extractor = EntityExtractor()
    invoice = extractor.extract_invoice(ocr_result)

    assert invoice.currency == "USD"
    assert invoice.total_amount == 590.00
    assert invoice.subtotal == 500.00
    assert invoice.tax_amount == 90.00


def test_extract_invoice_amount_imputation_from_total():
    tokens = [
        _make_token("SERVICIOS Y SOLUCIONES SAC", (80, 100, 105, 380)),
        _make_token("RUC: 20123456789", (115, 100, 135, 290)),
        _make_token("FACTURA ELECTRONICA: F002-000100", (145, 100, 165, 420)),
        _make_token("FECHA: 2026-10-30", (175, 100, 195, 310)),
        _make_token("TOTAL A PAGAR: 118.00", (300, 300, 320, 500)),
    ]

    ocr_result = OCRResult(
        page_number=1,
        tokens=tokens,
        full_text=" ".join(t.text for t in tokens),
        width=1000,
        height=1400,
    )

    extractor = EntityExtractor()
    invoice = extractor.extract_invoice(ocr_result)

    assert invoice.total_amount == 118.00
    assert invoice.subtotal == 100.00
    assert invoice.tax_amount == 18.00


def test_extract_shipping_guide_fallback():
    tokens = [
        _make_token("GUIA DE REMISION", (100, 100, 120, 300)),
        _make_token("NRO: T002-009988", (130, 100, 150, 320)),
        _make_token("RUC: 20999888771", (160, 100, 180, 310)),
    ]

    ocr_result = OCRResult(
        page_number=1,
        tokens=tokens,
        full_text=" ".join(t.text for t in tokens),
        width=1000,
        height=1400,
    )

    extractor = EntityExtractor()
    guide = extractor.extract_shipping_guide(ocr_result)

    assert guide.guide_number == "T002-009988"
    assert guide.sender_ruc == "20999888771"
