from datetime import date
import pytest

from src.nlp.reconciler import ReconciliationStatus, ThreeWayReconciler
from src.nlp.schemas import (
    InvoiceExtraction,
    LineItemExtraction,
    PaymentVoucherExtraction,
    ShippingGuideExtraction,
)


@pytest.fixture
def sample_invoice() -> InvoiceExtraction:
    return InvoiceExtraction(
        supplier_ruc="20549812341",
        supplier_name="DISTRIBUIDORA INDUSTRIAL S.A.C.",
        invoice_number="F001-0008492",
        issue_date=date(2026, 10, 28),
        currency="PEN",
        subtotal=1180.00,
        tax_amount=212.40,
        total_amount=1392.40,
        line_items=[
            LineItemExtraction(
                item_number=1,
                description="VALVULA DE CONTROL 1/2 PULG",
                quantity=4.0,
                unit_price=120.00,
                line_total=480.00,
            ),
            LineItemExtraction(
                item_number=2,
                description="MANOMETRO DE PRESION",
                quantity=2.0,
                unit_price=350.00,
                line_total=700.00,
            ),
        ],
    )


@pytest.fixture
def sample_guide() -> ShippingGuideExtraction:
    return ShippingGuideExtraction(
        guide_number="T001-000452",
        sender_ruc="20549812341",
        recipient_ruc="20100454521",
        issue_date=date(2026, 10, 28),
        items=[
            LineItemExtraction(
                item_number=1,
                description="VALVULA DE CONTROL 1/2 PULG",
                quantity=4.0,
                unit_price=0.0,
                line_total=0.0,
            ),
            LineItemExtraction(
                item_number=2,
                description="MANOMETRO DE PRESION",
                quantity=2.0,
                unit_price=0.0,
                line_total=0.0,
            ),
        ],
    )


@pytest.fixture
def sample_voucher() -> PaymentVoucherExtraction:
    return PaymentVoucherExtraction(
        bank_name="BANCO DE CREDITO BCP",
        operation_number="88472910",
        amount=1392.40,
        currency="PEN",
        payment_date=date(2026, 10, 29),
    )


def test_reconcile_perfect_match(sample_invoice, sample_guide, sample_voucher):
    reconciler = ThreeWayReconciler()
    report = reconciler.reconcile(
        invoice=sample_invoice,
        shipping_guides=[sample_guide],
        payment_vouchers=[sample_voucher],
    )

    assert report.status == ReconciliationStatus.RECONCILED
    assert report.math_valid is True
    assert report.goods_matched is True
    assert report.payment_matched is True
    assert len(report.discrepancies) == 0
    assert report.balance_pending == 0.0


def test_reconcile_missing_goods_discrepancy(sample_invoice, sample_voucher):
    # Guia con faltante de 1 valvula (recibidas 3 de 4)
    short_guide = ShippingGuideExtraction(
        guide_number="T001-000452",
        sender_ruc="20549812341",
        recipient_ruc="20100454521",
        issue_date=date(2026, 10, 28),
        items=[
            LineItemExtraction(
                item_number=1,
                description="VALVULA DE CONTROL 1/2 PULG",
                quantity=3.0,  # Faltante de 1
                unit_price=0.0,
                line_total=0.0,
            ),
            LineItemExtraction(
                item_number=2,
                description="MANOMETRO DE PRESION",
                quantity=2.0,
                unit_price=0.0,
                line_total=0.0,
            ),
        ],
    )

    reconciler = ThreeWayReconciler()
    report = reconciler.reconcile(
        invoice=sample_invoice,
        shipping_guides=[short_guide],
        payment_vouchers=[sample_voucher],
    )

    assert report.status == ReconciliationStatus.DISCREPANCY_FOUND
    assert report.goods_matched is False
    assert any(d["type"] == "QUANTITY_SHORTAGE" for d in report.discrepancies)


def test_reconcile_underpaid_voucher_discrepancy(sample_invoice, sample_guide):
    # Voucher pago menor al total de la factura
    partial_voucher = PaymentVoucherExtraction(
        bank_name="BANCO DE CREDITO BCP",
        operation_number="88472910",
        amount=1000.00,  # Faltan 392.40
        currency="PEN",
        payment_date=date(2026, 10, 29),
    )

    reconciler = ThreeWayReconciler()
    report = reconciler.reconcile(
        invoice=sample_invoice,
        shipping_guides=[sample_guide],
        payment_vouchers=[partial_voucher],
    )

    assert report.status == ReconciliationStatus.DISCREPANCY_FOUND
    assert report.payment_matched is False
    assert report.balance_pending == 392.40
    assert any(d["type"] == "UNDERPAID_BALANCE" for d in report.discrepancies)


def test_reconcile_currency_mismatch_discrepancy(sample_invoice, sample_guide):
    # Voucher en USD para factura en PEN
    usd_voucher = PaymentVoucherExtraction(
        bank_name="BANCO DE CREDITO BCP",
        operation_number="88472910",
        amount=1392.40,
        currency="USD",
        payment_date=date(2026, 10, 29),
    )

    reconciler = ThreeWayReconciler()
    report = reconciler.reconcile(
        invoice=sample_invoice,
        shipping_guides=[sample_guide],
        payment_vouchers=[usd_voucher],
    )

    assert report.status == ReconciliationStatus.DISCREPANCY_FOUND
    assert report.payment_matched is False
    assert any(d["type"] == "CURRENCY_MISMATCH" for d in report.discrepancies)


def test_reconcile_pending_when_missing_documents(sample_invoice):
    # Sin guia ni voucher adjunto
    reconciler = ThreeWayReconciler()
    report = reconciler.reconcile(
        invoice=sample_invoice,
        shipping_guides=[],
        payment_vouchers=[],
    )

    assert report.status == ReconciliationStatus.PENDING
    assert report.goods_matched is False
    assert report.payment_matched is False


def test_reconcile_overpaid_balance_discrepancy(sample_invoice, sample_guide):
    overpaid_voucher = PaymentVoucherExtraction(
        bank_name="BANCO DE CREDITO BCP",
        operation_number="88472910",
        amount=1500.00,  # 1500 > 1392.40
        currency="PEN",
        payment_date=date(2026, 10, 29),
    )

    reconciler = ThreeWayReconciler()
    report = reconciler.reconcile(
        invoice=sample_invoice,
        shipping_guides=[sample_guide],
        payment_vouchers=[overpaid_voucher],
    )

    assert report.status == ReconciliationStatus.DISCREPANCY_FOUND
    assert report.payment_matched is False
    assert any(d["type"] == "OVERPAID_BALANCE" for d in report.discrepancies)


def test_reconcile_split_shipments_fulfillment(sample_invoice, sample_voucher):
    # Entrega parcial 1: 2 valvulas y 1 manometro
    guide_1 = ShippingGuideExtraction(
        guide_number="T001-0001",
        sender_ruc="20549812341",
        recipient_ruc="20100454521",
        issue_date=date(2026, 10, 26),
        items=[
            LineItemExtraction(item_number=1, description="VALVULA DE CONTROL 1/2 PULG", quantity=2.0, unit_price=0.0, line_total=0.0),
            LineItemExtraction(item_number=2, description="MANOMETRO DE PRESION", quantity=1.0, unit_price=0.0, line_total=0.0),
        ],
    )
    # Entrega parcial 2: las 2 valvulas y 1 manometro restantes
    guide_2 = ShippingGuideExtraction(
        guide_number="T001-0002",
        sender_ruc="20549812341",
        recipient_ruc="20100454521",
        issue_date=date(2026, 10, 27),
        items=[
            LineItemExtraction(item_number=1, description="VALVULA DE CONTROL 1/2 PULG", quantity=2.0, unit_price=0.0, line_total=0.0),
            LineItemExtraction(item_number=2, description="MANOMETRO DE PRESION", quantity=1.0, unit_price=0.0, line_total=0.0),
        ],
    )

    reconciler = ThreeWayReconciler()
    report = reconciler.reconcile(
        invoice=sample_invoice,
        shipping_guides=[guide_1, guide_2],
        payment_vouchers=[sample_voucher],
    )

    assert report.status == ReconciliationStatus.RECONCILED
    assert report.goods_matched is True
    assert len(report.discrepancies) == 0
