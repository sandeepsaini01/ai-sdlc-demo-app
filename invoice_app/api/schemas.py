from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateInvoiceRequest(BaseModel):
    customer_name: str = Field(alias="customerName")
    amount: Decimal

    @field_validator("customer_name")
    @classmethod
    def customer_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Customer name is required.")
        return cleaned

    @field_validator("amount", mode="before")
    @classmethod
    def amount_from_input(cls, value: object) -> Decimal:
        if isinstance(value, float):
            raise ValueError("Amount must be sent as a decimal string, not a JSON number.")
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Amount must be a decimal number.") from exc
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        cents = amount.quantize(Decimal("0.01"))
        if amount != cents:
            raise ValueError("Amount must be in cents.")
        return cents


class RejectRequest(BaseModel):
    reason: str
