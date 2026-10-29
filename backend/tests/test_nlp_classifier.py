import pytest
from src.nlp.classifier import ClassificationResult, DocumentClassifier, DocumentType


def test_classify_invoice():
    classifier = DocumentClassifier()
    invoice_text = """
    DISTRIBUIDORA INDUSTRIAL S.A.C.
    RUC: 20549812341
    FACTURA ELECTRONICA F001-0008492
    FECHA EMISION: 28/10/2026
    SUBTOTAL: S/ 1,630.00
    IGV (18%): S/ 293.40
    TOTAL A PAGAR: S/ 1,923.40
    """
    result = classifier.classify(invoice_text)
    assert isinstance(result, ClassificationResult)
    assert result.doc_type == DocumentType.INVOICE
    assert result.confidence >= 0.7
    assert any("FACTURA" in tok or "RUC" in tok for tok in result.evidence_tokens)


def test_classify_shipping_guide():
    classifier = DocumentClassifier()
    guide_text = """
    TRANSPORTES Y LOGISTICA PERU S.A.
    RUC: 20491823901
    GUIA DE REMISION REMITENTE T001-0004521
    MOTIVO DE TRASLADO: VENTA
    PUNTO DE PARTIDA: AV. INDUSTRIAL 450, LIMA
    PUNTO DE LLEGADA: PLANTA TRUJILLO KM 560
    DATOS DEL TRANSPORTISTA: JUAN PEREZ PLACA: ABC-123
    """
    result = classifier.classify(guide_text)
    assert result.doc_type == DocumentType.SHIPPING_GUIDE
    assert result.confidence >= 0.7
    assert any("GUIA" in tok or "TRASLADO" in tok for tok in result.evidence_tokens)


def test_classify_payment_voucher():
    classifier = DocumentClassifier()
    voucher_text = """
    BANCO DE CREDITO DEL PERU - BCP
    CONSTANCIA DE TRANSFERENCIA BANCARIA
    NUMERO DE OPERACION: 98421045
    CUENTA ORIGEN: 193-4920194-0-45
    CUENTA DESTINO: 191-8849201-0-12
    IMPORTE PAGADO: S/ 1,923.40
    FECHA: 29/10/2026 HORA: 14:32:10
    """
    result = classifier.classify(voucher_text)
    assert result.doc_type == DocumentType.PAYMENT_VOUCHER
    assert result.confidence >= 0.7
    assert any("TRANSFERENCIA" in tok or "OPERACION" in tok for tok in result.evidence_tokens)


def test_classify_unknown_document():
    classifier = DocumentClassifier()
    random_text = """
    MANUAL DE USUARIO Y CONFIGURACION DE ROUTER WI-FI
    CAPITULO 1: INTRODUCCION A LA RED Y ANTENAS
    CONECTE EL CABLE DE RED EN EL PUERTO AZUL.
    """
    result = classifier.classify(random_text)
    assert result.doc_type == DocumentType.UNKNOWN
    assert result.confidence < 0.5


def test_classify_empty_text():
    classifier = DocumentClassifier()
    result = classifier.classify("")
    assert result.doc_type == DocumentType.UNKNOWN
    assert result.confidence == 0.0
