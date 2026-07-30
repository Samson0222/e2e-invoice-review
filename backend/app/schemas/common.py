"""Shared value objects and Azure Document Intelligence field-extraction helpers."""

from datetime import date, time

from azure.ai.documentintelligence.models import DocumentField
from pydantic import BaseModel


class Money(BaseModel):
    amount: float | None = None
    currency_code: str | None = None
    currency_symbol: str | None = None


class Address(BaseModel):
    house_number: str | None = None
    po_box: str | None = None
    road: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country_region: str | None = None
    street_address: str | None = None
    unit: str | None = None


def field_string(field: DocumentField | None) -> str | None:
    return field.value_string if field else None


def field_phone_number(field: DocumentField | None) -> str | None:
    return field.value_phone_number if field else None


def field_country_region(field: DocumentField | None) -> str | None:
    return field.value_country_region if field else None


def field_date(field: DocumentField | None) -> date | None:
    return field.value_date if field else None


def field_time(field: DocumentField | None) -> time | None:
    return field.value_time if field else None


def field_number(field: DocumentField | None) -> float | None:
    return field.value_number if field else None


def field_money(field: DocumentField | None) -> Money | None:
    if field is None or field.value_currency is None:
        return None
    value = field.value_currency
    return Money(
        amount=value.amount,
        currency_code=value.currency_code,
        currency_symbol=value.currency_symbol,
    )


def field_address(field: DocumentField | None) -> Address | None:
    if field is None or field.value_address is None:
        return None
    value = field.value_address
    return Address(
        house_number=value.house_number,
        po_box=value.po_box,
        road=value.road,
        city=value.city,
        state=value.state,
        postal_code=value.postal_code,
        country_region=value.country_region,
        street_address=value.street_address,
        unit=value.unit,
    )


def field_array(field: DocumentField | None) -> list[DocumentField]:
    return (field.value_array or []) if field else []


def field_object(field: DocumentField | None) -> dict[str, DocumentField]:
    return (field.value_object or {}) if field else {}
