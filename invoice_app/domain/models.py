from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Protocol


class InvoiceStatus(str, Enum):
    DRAFT = "Draft"
    PENDING_APPROVAL = "PendingApproval"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class Role(str, Enum):
    MANAGER = "Manager"
    DIRECTOR = "Director"
    APPROVER = "Approver"
    ADMIN = "Admin"


class InvoiceNotFound(Exception):
    """No invoice exists with the given id."""


class InvoiceConflict(Exception):
    """The invoice is not in the lifecycle state this action requires."""


class ApprovalDenied(Exception):
    """A business rule refused the approval. The invoice must stay as it was."""


@dataclass(frozen=True, eq=True)
class Approval:
    username: str
    role: str
    decided_at: datetime


@dataclass(eq=True)
class Invoice:
    id: str
    customer_name: str
    amount: Decimal
    status: InvoiceStatus = InvoiceStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None
    approvals: list[Approval] = field(default_factory=list)


class InvoiceRepository(Protocol):
    def transaction(self): ...

    def get_all(self) -> list[Invoice]: ...

    def get_by_id(self, invoice_id: str) -> Invoice | None: ...

    def add(self, invoice: Invoice) -> Invoice: ...

    def update(self, invoice: Invoice) -> None: ...

    def remove(self, invoice_id: str) -> bool: ...
