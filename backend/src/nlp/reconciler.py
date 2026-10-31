from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional
import unicodedata

from src.nlp.schemas import (
    InvoiceExtraction,
    PaymentVoucherExtraction,
    ShippingGuideExtraction,
)


class ReconciliationStatus(str, Enum):
    RECONCILED = "RECONCILED"
    DISCREPANCY_FOUND = "DISCREPANCY_FOUND"
    PENDING = "PENDING"


@dataclass
class ReconciliationReport:
    status: ReconciliationStatus
    math_valid: bool
    goods_matched: bool
    payment_matched: bool
    discrepancies: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    total_billed: float = 0.0
    total_paid: float = 0.0
    balance_pending: float = 0.0


def _normalize_string(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("utf-8")
    return re.sub(r"[^A-Z0-9\s]", "", ascii_text.upper()).strip()


class ThreeWayReconciler:
    """Motor de conciliacion contable de 3 vias (Factura vs. Guia de Remision vs. Voucher)."""

    def __init__(self, tolerance: float = 0.05) -> None:
        self.tolerance = tolerance

    def reconcile(
        self,
        invoice: InvoiceExtraction,
        shipping_guides: Optional[List[ShippingGuideExtraction]] = None,
        payment_vouchers: Optional[List[PaymentVoucherExtraction]] = None,
    ) -> ReconciliationReport:
        guides = shipping_guides or []
        vouchers = payment_vouchers or []
        discrepancies: List[Dict[str, Any]] = []

        # 1. Auditoria Matematica de la Factura
        math_valid = self._audit_invoice_math(invoice, discrepancies)

        # 2. Cotejo de Mercaderias (Factura vs. Guias de Remision)
        has_guides = len(guides) > 0
        goods_matched = False
        if has_guides:
            goods_matched = self._match_goods(invoice, guides, discrepancies)

        # 3. Cotejo de Pagos (Factura vs. Vouchers Bancarios)
        has_vouchers = len(vouchers) > 0
        payment_matched = False
        total_paid = 0.0
        balance_pending = invoice.total_amount

        if has_vouchers:
            payment_matched, total_paid, balance_pending = self._match_payments(invoice, vouchers, discrepancies)

        # 4. Determinacion de Estado Global
        if not has_guides and not has_vouchers:
            status = ReconciliationStatus.PENDING
            summary = "Expediente en espera: No se han adjuntado guias de remision ni comprobantes de pago."
        elif discrepancies:
            status = ReconciliationStatus.DISCREPANCY_FOUND
            summary = f"Discrepancia detectada: Se encontraron {len(discrepancies)} diferencias en el cotejo de 3 vias."
        else:
            status = ReconciliationStatus.RECONCILED
            summary = "Cotejo de 3 vias exitoso: Todos los bienes, importes y pagos estan 100% conciliados."

        return ReconciliationReport(
            status=status,
            math_valid=math_valid,
            goods_matched=goods_matched,
            payment_matched=payment_matched,
            discrepancies=discrepancies,
            summary=summary,
            total_billed=invoice.total_amount,
            total_paid=total_paid,
            balance_pending=balance_pending,
        )

    def _audit_invoice_math(self, invoice: InvoiceExtraction, discrepancies: List[Dict[str, Any]]) -> bool:
        valid = True

        # Verificar suma de items si existen
        if invoice.line_items:
            sum_items = round(sum(item.line_total for item in invoice.line_items), 2)
            if abs(sum_items - invoice.subtotal) > self.tolerance:
                discrepancies.append(
                    {
                        "type": "MATH_SUBTOTAL_MISMATCH",
                        "expected_subtotal": sum_items,
                        "declared_subtotal": invoice.subtotal,
                        "difference": round(abs(sum_items - invoice.subtotal), 2),
                    }
                )
                valid = False

        # Verificar subtotal + impuestos == total
        expected_total = round(invoice.subtotal + invoice.tax_amount, 2)
        if abs(expected_total - invoice.total_amount) > self.tolerance:
            discrepancies.append(
                {
                    "type": "MATH_TOTAL_MISMATCH",
                    "expected_total": expected_total,
                    "declared_total": invoice.total_amount,
                    "difference": round(abs(expected_total - invoice.total_amount), 2),
                }
            )
            valid = False

        return valid

    def _match_goods(
        self,
        invoice: InvoiceExtraction,
        guides: List[ShippingGuideExtraction],
        discrepancies: List[Dict[str, Any]],
    ) -> bool:
        if not invoice.line_items:
            return True

        # Consolidar todos los items recibidos de las guias
        received_items: List[Dict[str, Any]] = []
        for guide in guides:
            for item in guide.items:
                received_items.append(
                    {
                        "description": item.description,
                        "normalized": _normalize_string(item.description),
                        "quantity": item.quantity,
                        "guide_number": guide.guide_number,
                    }
                )

        all_matched = True

        for item in invoice.line_items:
            norm_desc = _normalize_string(item.description)
            # Buscar coincidencia en items recibidos
            matched_qty = 0.0
            for r_item in received_items:
                # Verificacion de similitud por tokens de texto
                if norm_desc in r_item["normalized"] or r_item["normalized"] in norm_desc:
                    matched_qty += r_item["quantity"]

            if matched_qty < item.quantity - self.tolerance:
                diff = round(item.quantity - matched_qty, 2)
                discrepancies.append(
                    {
                        "type": "QUANTITY_SHORTAGE",
                        "item_description": item.description,
                        "billed_quantity": item.quantity,
                        "received_quantity": matched_qty,
                        "shortage": diff,
                    }
                )
                all_matched = False
            elif matched_qty > item.quantity + self.tolerance:
                diff = round(matched_qty - item.quantity, 2)
                discrepancies.append(
                    {
                        "type": "QUANTITY_SURPLUS",
                        "item_description": item.description,
                        "billed_quantity": item.quantity,
                        "received_quantity": matched_qty,
                        "surplus": diff,
                    }
                )
                all_matched = False

        return all_matched

    def _match_payments(
        self,
        invoice: InvoiceExtraction,
        vouchers: List[PaymentVoucherExtraction],
        discrepancies: List[Dict[str, Any]],
    ) -> tuple[bool, float, float]:
        # Validar consistencia de monedas
        for voucher in vouchers:
            if voucher.currency.upper() != invoice.currency.upper():
                discrepancies.append(
                    {
                        "type": "CURRENCY_MISMATCH",
                        "invoice_currency": invoice.currency,
                        "voucher_currency": voucher.currency,
                        "operation_number": voucher.operation_number,
                    }
                )
                return False, round(sum(v.amount for v in vouchers), 2), invoice.total_amount

        total_paid = round(sum(v.amount for v in vouchers), 2)
        balance_pending = round(invoice.total_amount - total_paid, 2)

        if abs(balance_pending) <= self.tolerance:
            return True, total_paid, 0.0

        if balance_pending > self.tolerance:
            discrepancies.append(
                {
                    "type": "UNDERPAID_BALANCE",
                    "billed_total": invoice.total_amount,
                    "paid_total": total_paid,
                    "balance_pending": balance_pending,
                }
            )
            return False, total_paid, balance_pending

        # Pago mayor al total facturado
        overpaid = round(total_paid - invoice.total_amount, 2)
        discrepancies.append(
            {
                "type": "OVERPAID_BALANCE",
                "billed_total": invoice.total_amount,
                "paid_total": total_paid,
                "overpaid": overpaid,
            }
        )
        return False, total_paid, 0.0
