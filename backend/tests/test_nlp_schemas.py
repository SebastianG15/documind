from datetime import date
import pytest
from pydantic import ValidationError

from src.nlp.schemas import (
    BoundingBox2D,
    InvoiceExtraction,
    LineItemExtraction,
    PaymentVoucherExtraction,
    ShippingGuideExtraction,
)


def test_bounding_box_validation():
    # Valid box [ymin, xmin, ymax, xmax] in [0, 1000]
    box = BoundingBox2D(ymin=100, xmin=150, ymax=200, xmax=350)
    assert box.ymin == 100
    assert box.xmin == 150
    assert box.ymax == 200
    assert box.xmax == 350

    # Inverted coordinates: ymin > ymax must raise ValidationError
    with pytest.raises(ValidationError):
        BoundingBox2D(ymin=300, xmin=150, ymax=200, xmax=350)

    # Out of [0, 1000] bounds must raise ValidationError
    with pytest.raises(ValidationError):
        BoundingBox2D(ymin=-10, xmin=0, ymax=100, xmax=200)

    with pytest.raises(ValidationError):
        BoundingBox2D(ymin=0, xmin=0, ymax=1050, xmax=200)


def test_line_item_extraction():
    item = LineItemExtraction(
        item_number=1,
        sku="VALV-001",
        description="VALVULA DE CONTROL 1/2 PULG",
        quantity=4.0,
        unit_price=120.00,
        line_total=480.00,
        bbox=BoundingBox2D(ymin=300, xmin=60, ymax=330, xmax=800),
    )
    assert item.item_number == 1
    assert item.quantity == 4.0
    assert item.unit_price == 120.00
    assert item.line_total == 480.00

    # Mismatch between qty * unit_price and line_total must raise ValidationError
    with pytest.raises(ValidationError):
        LineItemExtraction(
            item_number=1,
            description="VALVULA DE CONTROL",
            quantity=4.0,
            unit_price=100.00,
            line_total=500.00,  # 4 * 100 != 500
        )


def test_invoice_extraction_valid():
    invoice = InvoiceExtraction(
        supplier_ruc="20549812341",
        supplier_name="DISTRIBUIDORA INDUSTRIAL S.A.C.",
        invoice_number="F001-0008492",
        issue_date=date(2026, 10, 28),
        currency="PEN",
        subtotal=1630.00,
        tax_amount=293.40,
        total_amount=1923.40,
        line_items=[
            LineItemExtraction(
                item_number=1,
                description="VALVULA DE CONTROL",
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
            LineItemExtraction(
                item_number=3,
                description="FILTRO DE AIRE",
                quantity=10.0,
                unit_price=45.00,
                line_total=450.00,
            ),
        ],
    )
    assert invoice.supplier_ruc == "20549812341"
    assert invoice.total_amount == 1923.40
    assert len(invoice.line_items) == 3


def test_invoice_invalid_ruc():
    # RUC must be 11 numeric digits starting with 10 or 20
    with pytest.raises(ValidationError):
        InvoiceExtraction(
            supplier_ruc="12345",  # Too short
            supplier_name="PROVEEDOR TEST",
            invoice_number="F001-001",
            issue_date=date(2026, 10, 28),
            subtotal=100.0,
            tax_amount=18.0,
            total_amount=118.0,
        )

    with pytest.raises(ValidationError):
        InvoiceExtraction(
            supplier_ruc="30549812341",  # Starts with 30 (invalid prefix)
            supplier_name="PROVEEDOR TEST",
            invoice_number="F001-001",
            issue_date=date(2026, 10, 28),
            subtotal=100.0,
            tax_amount=18.0,
            total_amount=118.0,
        )


def test_invoice_math_integrity():
    # subtotal + tax_amount != total_amount
    with pytest.raises(ValidationError):
        InvoiceExtraction(
            supplier_ruc="20549812341",
            supplier_name="PROVEEDOR TEST",
            invoice_number="F001-001",
            issue_date=date(2026, 10, 28),
            subtotal=1000.00,
            tax_amount=180.00,
            total_amount=1500.00,  # 1000 + 180 != 1500
        )


def test_shipping_guide_extraction():
    guide = ShippingGuideExtraction(
        guide_number="T001-0004521",
        sender_ruc="20549812341",
        recipient_ruc="20100048291",
        issue_date=date(2026, 10, 27),
        origin_address="Av. Industrial 450, Lima",
        destination_address="Planta Trujillo Km 560",
        items=[
            LineItemExtraction(
                item_number=1,
                description="VALVULA DE CONTROL 1/2 PULG",
                quantity=4.0,
                unit_price=0.0,
                line_total=0.0,
            )
        ],
    )
    assert guide.guide_number == "T001-0004521"
    assert len(guide.items) == 1


def test_payment_voucher_extraction():
    voucher = PaymentVoucherExtraction(
        bank_name="BCP",
        operation_number="OP-98421045",
        source_account="193-4920194-0-45",
        destination_account="191-8849201-0-12",
        amount=1923.40,
        currency="PEN",
        payment_date=date(2026, 10, 29),
    )
    assert voucher.bank_name == "BCP"
    assert voucher.amount == 1923.40

    # Negative amount must raise ValidationError
    with pytest.raises(ValidationError):
        PaymentVoucherExtraction(
            bank_name="BCP",
            operation_number="OP-1234",
            amount=-50.0,
            currency="PEN",
            payment_date=date(2026, 10, 29),
        )
