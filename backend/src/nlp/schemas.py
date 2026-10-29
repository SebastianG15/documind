from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class BoundingBox2D(BaseModel):
    ymin: int = Field(..., ge=0, le=1000)
    xmin: int = Field(..., ge=0, le=1000)
    ymax: int = Field(..., ge=0, le=1000)
    xmax: int = Field(..., ge=0, le=1000)

    @model_validator(mode="after")
    def validate_coordinates_order(self) -> "BoundingBox2D":
        if self.ymin > self.ymax:
            raise ValueError(f"ymin ({self.ymin}) no puede ser mayor que ymax ({self.ymax})")
        if self.xmin > self.xmax:
            raise ValueError(f"xmin ({self.xmin}) no puede ser mayor que xmax ({self.xmax})")
        return self


class LineItemExtraction(BaseModel):
    item_number: Optional[int] = None
    sku: Optional[str] = None
    description: str
    quantity: float = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)
    bbox: Optional[BoundingBox2D] = None

    @model_validator(mode="after")
    def validate_line_total(self) -> "LineItemExtraction":
        if self.quantity > 0 and self.unit_price > 0:
            expected = round(self.quantity * self.unit_price, 2)
            if abs(self.line_total - expected) > 0.05:
                raise ValueError(
                    f"Inconsistencia en total de linea: {self.quantity} * {self.unit_price} = {expected}, pero se indico {self.line_total}"
                )
        return self


class InvoiceExtraction(BaseModel):
    supplier_ruc: str
    supplier_name: str
    invoice_number: str
    issue_date: date
    currency: str = "PEN"
    subtotal: float = Field(..., ge=0)
    tax_amount: float = Field(..., ge=0)
    total_amount: float = Field(..., ge=0)
    line_items: List[LineItemExtraction] = Field(default_factory=list)
    header_bbox: Optional[BoundingBox2D] = None

    @field_validator("supplier_ruc")
    @classmethod
    def validate_ruc(cls, value: str) -> str:
        clean = value.strip()
        if not clean.isdigit() or len(clean) != 11:
            raise ValueError("El RUC debe estar compuesto exactamente por 11 digitos numericos")
        if not clean.startswith(("10", "15", "17", "20")):
            raise ValueError("El RUC debe comenzar con un prefijo valido (10, 15, 17 o 20)")
        return clean

    @model_validator(mode="after")
    def validate_totals(self) -> "InvoiceExtraction":
        expected_total = round(self.subtotal + self.tax_amount, 2)
        if abs(self.total_amount - expected_total) > 0.05:
            raise ValueError(
                f"Inconsistencia en montos totales: subtotal ({self.subtotal}) + impuesto ({self.tax_amount}) = {expected_total}, pero total es {self.total_amount}"
            )
        return self


class ShippingGuideExtraction(BaseModel):
    guide_number: str
    sender_ruc: str
    recipient_ruc: str
    issue_date: date
    dispatch_date: Optional[date] = None
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    items: List[LineItemExtraction] = Field(default_factory=list)
    bbox: Optional[BoundingBox2D] = None

    @field_validator("sender_ruc", "recipient_ruc")
    @classmethod
    def validate_ruc(cls, value: str) -> str:
        clean = value.strip()
        if not clean.isdigit() or len(clean) != 11:
            raise ValueError("El RUC debe contener 11 digitos numericos")
        return clean


class PaymentVoucherExtraction(BaseModel):
    bank_name: str
    operation_number: str
    source_account: Optional[str] = None
    destination_account: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = "PEN"
    payment_date: date
    bbox: Optional[BoundingBox2D] = None
