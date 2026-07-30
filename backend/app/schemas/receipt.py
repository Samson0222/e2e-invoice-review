"""Pydantic data model for Azure Document Intelligence's prebuilt-receipt output."""

from datetime import date, time

from azure.ai.documentintelligence.models import AnalyzedDocument, DocumentField
from pydantic import BaseModel

from app.schemas.common import (
    Address,
    Money,
    field_address,
    field_array,
    field_country_region,
    field_date,
    field_money,
    field_number,
    field_object,
    field_phone_number,
    field_string,
    field_time,
)


class ReceiptTaxDetail(BaseModel):
    amount: Money | None = None
    rate: float | None = None
    net_amount: Money | None = None
    description: str | None = None

    @classmethod
    def from_fields(cls, fields: dict[str, DocumentField]) -> "ReceiptTaxDetail":
        return cls(
            amount=field_money(fields.get("Amount")),
            rate=field_number(fields.get("Rate")),
            net_amount=field_money(fields.get("NetAmount")),
            description=field_string(fields.get("Description")),
        )


class ReceiptLineItem(BaseModel):
    description: str | None = None
    product_code: str | None = None
    quantity: float | None = None
    quantity_unit: str | None = None
    price: Money | None = None
    total_price: Money | None = None

    @classmethod
    def from_fields(cls, fields: dict[str, DocumentField]) -> "ReceiptLineItem":
        return cls(
            description=field_string(fields.get("Description")),
            product_code=field_string(fields.get("ProductCode")),
            quantity=field_number(fields.get("Quantity")),
            quantity_unit=field_string(fields.get("QuantityUnit")),
            price=field_money(fields.get("Price")),
            total_price=field_money(fields.get("TotalPrice")),
        )


class Receipt(BaseModel):
    doc_type: str
    confidence: float

    receipt_type: str | None = None
    merchant_name: str | None = None
    merchant_phone_number: str | None = None
    merchant_address: Address | None = None
    country_region: str | None = None

    transaction_date: date | None = None
    transaction_time: time | None = None

    subtotal: Money | None = None
    total_tax: Money | None = None
    tip: Money | None = None
    total: Money | None = None

    tax_details: list[ReceiptTaxDetail] = []
    items: list[ReceiptLineItem] = []

    @classmethod
    def from_document(cls, document: AnalyzedDocument) -> "Receipt":
        fields = document.fields or {}
        return cls(
            doc_type=document.doc_type,
            confidence=document.confidence,
            receipt_type=field_string(fields.get("ReceiptType")),
            merchant_name=field_string(fields.get("MerchantName")),
            merchant_phone_number=field_phone_number(fields.get("MerchantPhoneNumber")),
            merchant_address=field_address(fields.get("MerchantAddress")),
            country_region=field_country_region(fields.get("CountryRegion")),
            transaction_date=field_date(fields.get("TransactionDate")),
            transaction_time=field_time(fields.get("TransactionTime")),
            subtotal=field_money(fields.get("Subtotal")),
            total_tax=field_money(fields.get("TotalTax")),
            tip=field_money(fields.get("Tip")),
            total=field_money(fields.get("Total")),
            tax_details=[
                ReceiptTaxDetail.from_fields(field_object(item))
                for item in field_array(fields.get("TaxDetails"))
            ],
            items=[
                ReceiptLineItem.from_fields(field_object(item))
                for item in field_array(fields.get("Items"))
            ],
        )
