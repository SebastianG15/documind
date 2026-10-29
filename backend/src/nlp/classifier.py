from dataclasses import dataclass, field
from enum import Enum
import re
import unicodedata


class DocumentType(str, Enum):
    INVOICE = "INVOICE"
    SHIPPING_GUIDE = "SHIPPING_GUIDE"
    PAYMENT_VOUCHER = "PAYMENT_VOUCHER"
    UNKNOWN = "UNKNOWN"


@dataclass
class ClassificationResult:
    doc_type: DocumentType
    confidence: float
    evidence_tokens: list[str] = field(default_factory=list)


def normalize_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("utf-8")
    return ascii_text.upper()


class DocumentClassifier:
    LEXICONS = {
        DocumentType.INVOICE: {
            "strong": [
                "FACTURA ELECTRONICA",
                "FACTURA DE VENTA",
                "FACTURA",
                "RUC",
                "SUBTOTAL",
                "IGV",
                "TOTAL A PAGAR",
                "VALOR VENTA",
                "PRECIO VENTA",
                "INVOICE",
            ],
            "medium": [
                "CLIENTE",
                "PRECIO UNITARIO",
                "IMPORTE TOTAL",
                "FORMA DE PAGO",
                "CONTADO",
                "CREDITO",
                "DETRACCION",
                "CANTIDAD",
                "DESCRIPCION",
            ],
        },
        DocumentType.SHIPPING_GUIDE: {
            "strong": [
                "GUIA DE REMISION",
                "GUIA DE TRASLADO",
                "PUNTO DE PARTIDA",
                "PUNTO DE LLEGADA",
                "DATOS DEL TRASLADO",
                "DESTINATARIO",
                "TRANSPORTISTA",
                "SHIPPING GUIDE",
                "WAYBILL",
            ],
            "medium": [
                "MOTIVO DE TRASLADO",
                "PLACA",
                "LICENCIA DE CONDUCIR",
                "PESO BRUTO",
                "REMITENTE",
                "BULTOS",
                "CONDUCTOR",
                "UNIDAD DE MEDIDA",
            ],
        },
        DocumentType.PAYMENT_VOUCHER: {
            "strong": [
                "CONSTANCIA DE TRANSFERENCIA",
                "TRANSFERENCIA BANCARIA",
                "NUMERO DE OPERACION",
                "NRO OPERACION",
                "NRO. OPERACION",
                "CUENTA ORIGEN",
                "CUENTA DESTINO",
                "VOUCHER",
                "COMPROBANTE DE PAGO",
            ],
            "medium": [
                "BANCO",
                "BCP",
                "BBVA",
                "INTERBANK",
                "SCOTIABANK",
                "BANCO DE LA NACION",
                "IMPORTE PAGADO",
                "MONTO TRANSFERIDO",
                "CANAL DE PAGO",
                "CCI",
            ],
        },
    }

    def __init__(self, min_confidence: float = 0.5) -> None:
        self.min_confidence = min_confidence

    def classify(self, text: str) -> ClassificationResult:
        if not text or not text.strip():
            return ClassificationResult(doc_type=DocumentType.UNKNOWN, confidence=0.0)

        normalized = normalize_text(text)
        scores: dict[DocumentType, float] = {
            DocumentType.INVOICE: 0.0,
            DocumentType.SHIPPING_GUIDE: 0.0,
            DocumentType.PAYMENT_VOUCHER: 0.0,
        }
        evidence: dict[DocumentType, list[str]] = {
            DocumentType.INVOICE: [],
            DocumentType.SHIPPING_GUIDE: [],
            DocumentType.PAYMENT_VOUCHER: [],
        }

        for doc_type, patterns in self.LEXICONS.items():
            for phrase in patterns["strong"]:
                if re.search(r"\b" + re.escape(phrase) + r"\b", normalized):
                    scores[doc_type] += 3.0
                    evidence[doc_type].append(phrase)

            for phrase in patterns["medium"]:
                if re.search(r"\b" + re.escape(phrase) + r"\b", normalized):
                    scores[doc_type] += 1.2
                    evidence[doc_type].append(phrase)

        total_score = sum(scores.values())
        if total_score <= 0.0:
            return ClassificationResult(doc_type=DocumentType.UNKNOWN, confidence=0.0)

        best_type = max(scores, key=lambda k: scores[k])
        best_score = scores[best_type]

        confidence = round(best_score / total_score, 2)
        if confidence < self.min_confidence or best_score < 3.0:
            return ClassificationResult(
                doc_type=DocumentType.UNKNOWN,
                confidence=confidence,
                evidence_tokens=evidence[best_type],
            )

        return ClassificationResult(
            doc_type=best_type,
            confidence=confidence,
            evidence_tokens=evidence[best_type],
        )
