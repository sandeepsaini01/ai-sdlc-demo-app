from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from invoice_app.domain.models import (
    Approval,
    ApprovalDenied,
    Invoice,
    InvoiceConflict,
    InvoiceNotFound,
    InvoiceRepository,
    InvoiceStatus,
    Role,
)

# "Up to" is inclusive. An amount one cent over the limit is not a sole approval.
MANAGER_LIMIT = Decimal("50000")
DIRECTOR_LIMIT = Decimal("500000")

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class _Decision:
    """The next approval state. Built before the invoice is touched."""

    approvals: tuple[Approval, ...]
    status: InvoiceStatus
    decided_by: str | None
    decided_at: datetime | None


def format_amount(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01')):,.2f}"


class ApprovalService:
    """Invoice lifecycle and single-approver role ceilings.

    A manager may sole-approve an invoice up to 50,000.
    A director may sole-approve an invoice up to 500,000.
    A refused vote leaves the invoice unchanged.
    """

    def __init__(self, repository: InvoiceRepository, clock: Clock | None = None) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def submit(self, invoice_id: str) -> Invoice:
        with self._lock():
            invoice = self._find(invoice_id)
            if invoice.status != InvoiceStatus.DRAFT:
                raise InvoiceConflict(
                    f"Invoice {invoice_id} is {invoice.status.value}; only drafts can be submitted."
                )
            invoice.status = InvoiceStatus.PENDING_APPROVAL
            self._repository.update(invoice)
            return invoice

    def approve(self, invoice_id: str, username: str, role: str) -> Invoice:
        with self._lock():
            invoice = self._find(invoice_id)
            self._ensure_pending(invoice)
            approver = self._required_username(invoice, username)
            parsed_role = self._parse_role(invoice, role)
            # The decision is pure. A refusal raises before any field is assigned.
            decision = self._decide(invoice, approver, parsed_role)
            self._apply(invoice, decision)
            self._repository.update(invoice)
            return invoice

    def reject(self, invoice_id: str, username: str, reason: str) -> Invoice:
        if reason is None or not str(reason).strip():
            raise ValueError("A reason is required to reject an invoice.")
        with self._lock():
            invoice = self._find(invoice_id)
            self._ensure_pending(invoice)
            now = self._clock()
            invoice.status = InvoiceStatus.REJECTED
            invoice.decided_by = username.strip()
            invoice.decided_at = now
            invoice.decision_note = str(reason).strip()
            self._repository.update(invoice)
            return invoice

    def _decide(self, invoice: Invoice, username: str, role: Role) -> _Decision:
        self._ensure_sole_allowed(invoice, role)
        return self._completed(username, role, tuple(invoice.approvals))

    def _ensure_sole_allowed(self, invoice: Invoice, role: Role) -> None:
        if role == Role.MANAGER and invoice.amount <= MANAGER_LIMIT:
            return
        if role == Role.DIRECTOR and invoice.amount <= DIRECTOR_LIMIT:
            return
        raise ApprovalDenied(self._opening_vote_denied(invoice, role))

    def _opening_vote_denied(self, invoice: Invoice, role: Role) -> str:
        if role == Role.MANAGER:
            return (
                f"A manager may approve invoices up to {format_amount(MANAGER_LIMIT)}. "
                f"Invoice {invoice.id} is {format_amount(invoice.amount)}, so this approval "
                "was rejected and the invoice was left unchanged."
            )
        if role == Role.DIRECTOR:
            return (
                f"A director may approve invoices up to {format_amount(DIRECTOR_LIMIT)}. "
                f"Invoice {invoice.id} is {format_amount(invoice.amount)}, so this approval "
                "was rejected and the invoice was left unchanged."
            )
        return (
            f"Role {role.value} cannot approve invoice {invoice.id}. "
            "The invoice was left unchanged."
        )

    def _completed(self, username: str, role: Role, existing: tuple[Approval, ...]) -> _Decision:
        vote = Approval(username=username, role=role.value, decided_at=self._clock())
        return _Decision(
            approvals=existing + (vote,),
            status=InvoiceStatus.APPROVED,
            decided_by=username,
            decided_at=vote.decided_at,
        )

    def _apply(self, invoice: Invoice, decision: _Decision) -> None:
        invoice.approvals = list(decision.approvals)
        invoice.status = decision.status
        invoice.decided_by = decision.decided_by
        invoice.decided_at = decision.decided_at

    def _find(self, invoice_id: str) -> Invoice:
        invoice = self._repository.get_by_id(invoice_id)
        if invoice is None:
            raise InvoiceNotFound(f"Invoice {invoice_id} was not found.")
        return invoice

    def _ensure_pending(self, invoice: Invoice) -> None:
        if invoice.status != InvoiceStatus.PENDING_APPROVAL:
            raise InvoiceConflict(
                f"Invoice {invoice.id} is {invoice.status.value}; only pending invoices can be decided."
            )

    def _required_username(self, invoice: Invoice, username: str) -> str:
        cleaned = (username or "").strip()
        if not cleaned:
            raise ApprovalDenied(
                f"An approver is required. Invoice {invoice.id} was left unchanged."
            )
        return cleaned

    def _parse_role(self, invoice: Invoice, role: str) -> Role:
        try:
            return Role(role)
        except ValueError:
            raise ApprovalDenied(
                f"Role {role} cannot approve invoice {invoice.id}. The invoice was left unchanged."
            ) from None

    def _lock(self) -> AbstractContextManager[None]:
        return self._repository.transaction()
