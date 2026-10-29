from __future__ import annotations

import threading
from datetime import datetime, timezone
from decimal import Decimal

from invoice_app.domain.models import Invoice, InvoiceStatus

SEEDED_AT = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


def _seed() -> list[Invoice]:
    return [
        Invoice(
            id="INV-1001",
            customer_name="Lakeside School District",
            amount=Decimal("4250.00"),
            status=InvoiceStatus.PENDING_APPROVAL,
            created_at=SEEDED_AT,
        ),
        Invoice(
            id="INV-1002",
            customer_name="Hilltop Academy",
            amount=Decimal("980.50"),
            status=InvoiceStatus.PENDING_APPROVAL,
            created_at=SEEDED_AT,
        ),
        Invoice(
            id="INV-1003",
            customer_name="Riverside Charter",
            amount=Decimal("12300.00"),
            status=InvoiceStatus.APPROVED,
            created_at=SEEDED_AT,
            decided_by="demo.director",
            decided_at=SEEDED_AT,
        ),
        Invoice(
            id="INV-1004",
            customer_name="Oakwood Independent",
            amount=Decimal("615.75"),
            status=InvoiceStatus.PENDING_APPROVAL,
            created_at=SEEDED_AT,
        ),
        Invoice(
            id="INV-1005",
            customer_name="Maple Grove Prep",
            amount=Decimal("310.00"),
            status=InvoiceStatus.DRAFT,
            created_at=SEEDED_AT,
        ),
        Invoice(
            id="INV-1006",
            customer_name="Cedar Ridge Schools",
            amount=Decimal("75000.00"),
            status=InvoiceStatus.PENDING_APPROVAL,
            created_at=SEEDED_AT,
        ),
        Invoice(
            id="INV-1007",
            customer_name="Northwind District",
            amount=Decimal("750000.00"),
            status=InvoiceStatus.PENDING_APPROVAL,
            created_at=SEEDED_AT,
        ),
    ]


class InMemoryInvoiceRepository:
    """Process-local store so the demo runs with no database."""

    def __init__(self, invoices: list[Invoice] | None = None, next_number: int = 1008) -> None:
        self._lock = threading.RLock()
        self._invoices = list(invoices) if invoices is not None else _seed()
        self._next_number = next_number

    def transaction(self):
        return self._lock

    def get_all(self) -> list[Invoice]:
        with self._lock:
            return list(self._invoices)

    def get_by_id(self, invoice_id: str) -> Invoice | None:
        with self._lock:
            return next((invoice for invoice in self._invoices if invoice.id == invoice_id), None)

    def add(self, invoice: Invoice) -> Invoice:
        with self._lock:
            invoice.id = f"INV-{self._next_number}"
            self._next_number += 1
            self._invoices.append(invoice)
            return invoice

    def update(self, invoice: Invoice) -> None:
        with self._lock:
            for index, existing in enumerate(self._invoices):
                if existing.id == invoice.id:
                    self._invoices[index] = invoice
                    return

    def remove(self, invoice_id: str) -> bool:
        with self._lock:
            before = len(self._invoices)
            self._invoices = [invoice for invoice in self._invoices if invoice.id != invoice_id]
            return len(self._invoices) != before
