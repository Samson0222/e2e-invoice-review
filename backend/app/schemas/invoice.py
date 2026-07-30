"""Pydantic data model for Azure Document Intelligence's prebuilt-invoice output."""

from datetime import date

from azure.ai.documentintelligence.models import AnalyzedDocument, DocumentField
from pydantic import BaseModel

from app.schemas.common import (
    Address,
    Money,
    field_address,
    field_array,
    field_date,
    field_money,
    field_number,
    field_object,
    field_string,
)


class InvoiceTaxDetail(BaseModel):
    amount: Money | None = None
    rate: str | None = None

    @classmethod
    def from_fields(cls, fields: dict[str, DocumentField]) -> "InvoiceTaxDetail":
        return cls(
            amount=field_money(fields.get("Amount")),
            rate=field_string(fields.get("Rate")),
        )


class InvoiceLineItem(BaseModel):
    description: str | None = None
    product_code: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: Money | None = None
    amount: Money | None = None
    item_date: date | None = None
    tax: Money | None = None
    tax_rate: str | None = None

    @classmethod
    def from_fields(cls, fields: dict[str, DocumentField]) -> "InvoiceLineItem":
        return cls(
            description=field_string(fields.get("Description")),
            product_code=field_string(fields.get("ProductCode")),
            quantity=field_number(fields.get("Quantity")),
            unit=field_string(fields.get("Unit")),
            unit_price=field_money(fields.get("UnitPrice")),
            amount=field_money(fields.get("Amount")),
            item_date=field_date(fields.get("Date")),
            tax=field_money(fields.get("Tax")),
            tax_rate=field_string(fields.get("TaxRate")),
        )


class Invoice(BaseModel):
    doc_type: str
    confidence: float

    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    vendor_address: Address | None = None
    vendor_address_recipient: str | None = None

    customer_name: str | None = None
    customer_id: str | None = None
    customer_tax_id: str | None = None
    customer_address: Address | None = None
    customer_address_recipient: str | None = None

    billing_address: Address | None = None
    billing_address_recipient: str | None = None
    shipping_address: Address | None = None
    shipping_address_recipient: str | None = None
    remittance_address: Address | None = None
    remittance_address_recipient: str | None = None
    service_address: Address | None = None
    service_address_recipient: str | None = None
    service_start_date: date | None = None
    service_end_date: date | None = None

    invoice_id: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    purchase_order: str | None = None
    payment_term: str | None = None

    subtotal: Money | None = None
    total_discount: Money | None = None
    total_tax: Money | None = None
    invoice_total: Money | None = None
    amount_due: Money | None = None
    previous_unpaid_balance: Money | None = None

    tax_details: list[InvoiceTaxDetail] = []
    items: list[InvoiceLineItem] = []

    @classmethod
    def from_document(cls, document: AnalyzedDocument) -> "Invoice":
        fields = document.fields or {}
        return cls(
            doc_type=document.doc_type,
            confidence=document.confidence,
            vendor_name=field_string(fields.get("VendorName")),
            vendor_tax_id=field_string(fields.get("VendorTaxId")),
            vendor_address=field_address(fields.get("VendorAddress")),
            vendor_address_recipient=field_string(fields.get("VendorAddressRecipient")),
            customer_name=field_string(fields.get("CustomerName")),
            customer_id=field_string(fields.get("CustomerId")),
            customer_tax_id=field_string(fields.get("CustomerTaxId")),
            customer_address=field_address(fields.get("CustomerAddress")),
            customer_address_recipient=field_string(fields.get("CustomerAddressRecipient")),
            billing_address=field_address(fields.get("BillingAddress")),
            billing_address_recipient=field_string(fields.get("BillingAddressRecipient")),
            shipping_address=field_address(fields.get("ShippingAddress")),
            shipping_address_recipient=field_string(fields.get("ShippingAddressRecipient")),
            remittance_address=field_address(fields.get("RemittanceAddress")),
            remittance_address_recipient=field_string(fields.get("RemittanceAddressRecipient")),
            service_address=field_address(fields.get("ServiceAddress")),
            service_address_recipient=field_string(fields.get("ServiceAddressRecipient")),
            service_start_date=field_date(fields.get("ServiceStartDate")),
            service_end_date=field_date(fields.get("ServiceEndDate")),
            invoice_id=field_string(fields.get("InvoiceId")),
            invoice_date=field_date(fields.get("InvoiceDate")),
            due_date=field_date(fields.get("DueDate")),
            purchase_order=field_string(fields.get("PurchaseOrder")),
            payment_term=field_string(fields.get("PaymentTerm")),
            subtotal=field_money(fields.get("SubTotal")),
            total_discount=field_money(fields.get("TotalDiscount")),
            total_tax=field_money(fields.get("TotalTax")),
            invoice_total=field_money(fields.get("InvoiceTotal")),
            amount_due=field_money(fields.get("AmountDue")),
            previous_unpaid_balance=field_money(fields.get("PreviousUnpaidBalance")),
            tax_details=[
                InvoiceTaxDetail.from_fields(field_object(item))
                for item in field_array(fields.get("TaxDetails"))
            ],
            items=[
                InvoiceLineItem.from_fields(field_object(item))
                for item in field_array(fields.get("Items"))
            ],
        )
