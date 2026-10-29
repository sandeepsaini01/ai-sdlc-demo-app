from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from invoice_app.domain.models import Invoice, InvoiceStatus

FIXED = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)


def pending(amount: str, invoice_id: str = "INV-1") -> Invoice:
    return Invoice(
        id=invoice_id,
        customer_name="Test School",
        amount=Decimal(amount),
        status=InvoiceStatus.PENDING_APPROVAL,
        created_at=FIXED,
    )


class TickingClock:
    def __init__(self) -> None:
        self.now = FIXED

    def __call__(self) -> datetime:
        self.now += timedelta(minutes=1)
        return self.now


class FakeInvoiceRepository:
    def __init__(self, *invoices: Invoice) -> None:
        self.invoices = list(invoices)
        self.updates = 0

    def transaction(self):
        return nullcontext()

    def get_all(self) -> list[Invoice]:
        return list(self.invoices)

    def get_by_id(self, invoice_id: str) -> Invoice | None:
        return next((invoice for invoice in self.invoices if invoice.id == invoice_id), None)

    def add(self, invoice: Invoice) -> Invoice:
        self.invoices.append(invoice)
        return invoice

    def update(self, invoice: Invoice) -> None:
        self.updates += 1
        for index, existing in enumerate(self.invoices):
            if existing.id == invoice.id:
                self.invoices[index] = invoice
                return

    def remove(self, invoice_id: str) -> bool:
        before = len(self.invoices)
        self.invoices = [invoice for invoice in self.invoices if invoice.id != invoice_id]
        return len(self.invoices) != before


def snapshot(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "customer_name": invoice.customer_name,
        "amount": invoice.amount,
        "status": invoice.status,
        "created_at": invoice.created_at,
        "decided_by": invoice.decided_by,
        "decided_at": invoice.decided_at,
        "decision_note": invoice.decision_note,
        "approvals": list(invoice.approvals),
    }
