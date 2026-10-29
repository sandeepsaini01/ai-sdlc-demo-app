from __future__ import annotations

from datetime import timedelta

import pytest

from invoice_app.domain.approval_service import ApprovalService
from invoice_app.domain.models import ApprovalDenied, InvoiceConflict, InvoiceNotFound, InvoiceStatus
from tests.support import FIXED, FakeInvoiceRepository, TickingClock, pending, snapshot


def service_for(*invoices, clock=None):
    repository = FakeInvoiceRepository(*invoices)
    return ApprovalService(repository, clock=clock), repository


def assert_unchanged(repository: FakeInvoiceRepository, before: dict, updates: int) -> None:
    current = repository.get_by_id(before["id"])
    assert current is not None
    assert snapshot(current) == before
    assert repository.updates == updates


class TestSubmit:
    def test_submit_moves_draft_to_pending(self):
        invoice = pending("100.00")
        invoice.status = InvoiceStatus.DRAFT
        service, _repository = service_for(invoice)

        result = service.submit("INV-1")

        assert result.status == InvoiceStatus.PENDING_APPROVAL

    def test_submit_rejects_invoice_that_is_not_a_draft_and_leaves_it(self):
        invoice = pending("100.00")
        invoice.status = InvoiceStatus.APPROVED
        invoice.decided_by = "demo.director"
        service, repository = service_for(invoice)
        before = snapshot(invoice)

        with pytest.raises(InvoiceConflict, match="only drafts can be submitted"):
            service.submit("INV-1")

        assert_unchanged(repository, before, updates=0)


class TestSingleApproverLimits:
    def test_manager_can_approve_up_to_50000(self):
        invoice = pending("50000.00")
        service, repository = service_for(invoice, clock=lambda: FIXED)

        result = service.approve("INV-1", "demo.manager", "Manager")

        assert result.status == InvoiceStatus.APPROVED
        assert result.decided_by == "demo.manager"
        assert result.decided_at == FIXED
        assert result.decision_note is None
        assert result.amount == invoice.amount
        assert [vote.username for vote in result.approvals] == ["demo.manager"]
        assert repository.updates == 1

    def test_manager_cannot_approve_one_cent_over_50000_and_invoice_is_unchanged(self):
        invoice = pending("50000.01")
        service, repository = service_for(invoice)
        before = snapshot(invoice)

        with pytest.raises(ApprovalDenied, match="50,000.00") as caught:
            service.approve("INV-1", "demo.manager", "Manager")

        assert "left unchanged" in str(caught.value)
        assert_unchanged(repository, before, updates=0)

    def test_manager_cannot_open_or_cast_a_vote_above_500000(self):
        invoice = pending("750000.00")
        service, repository = service_for(invoice)
        before = snapshot(invoice)

        with pytest.raises(ApprovalDenied, match="A manager may approve invoices up to 50,000.00"):
            service.approve("INV-1", "demo.manager", "Manager")

        assert_unchanged(repository, before, updates=0)
        assert repository.get_by_id("INV-1").approvals == []

    def test_director_can_approve_up_to_500000(self):
        invoice = pending("500000.00")
        service, _repository = service_for(invoice, clock=lambda: FIXED)

        result = service.approve("INV-1", "demo.director", "Director")

        assert result.status == InvoiceStatus.APPROVED
        assert result.decided_by == "demo.director"
        assert len(result.approvals) == 1

    def test_director_above_500000_records_a_first_vote_and_does_not_approve(self):
        invoice = pending("500000.01")
        clock = TickingClock()
        service, repository = service_for(invoice, clock=clock)

        result = service.approve("INV-1", "demo.director", "Director")

        assert result.status == InvoiceStatus.PENDING_APPROVAL
        assert result.decided_by is None
        assert result.decided_at is None
        assert result.decision_note is None
        assert [(vote.username, vote.role) for vote in result.approvals] == [
            ("demo.director", "Director")
        ]
        assert result.approvals[0].decided_at == FIXED + timedelta(minutes=1)
        assert repository.updates == 1

    def test_role_without_a_limit_cannot_approve_and_invoice_is_unchanged(self):
        invoice = pending("100.00")
        service, repository = service_for(invoice)
        before = snapshot(invoice)

        for role in ("Approver", "Admin"):
            with pytest.raises(ApprovalDenied, match=f"Role {role} cannot approve"):
                service.approve("INV-1", "someone", role)
            assert_unchanged(repository, before, updates=0)

    def test_denied_over_limit_attempt_still_allows_a_later_valid_approval(self):
        invoice = pending("75000.00")
        service, _repository = service_for(invoice, clock=lambda: FIXED)

        with pytest.raises(ApprovalDenied):
            service.approve("INV-1", "demo.manager", "Manager")

        result = service.approve("INV-1", "demo.director", "Director")

        assert result.status == InvoiceStatus.APPROVED
        assert result.decided_by == "demo.director"
        assert [vote.username for vote in result.approvals] == ["demo.director"]


class TestTwoApproverRule:
    def test_two_distinct_directors_approve_an_invoice_above_500000(self):
        invoice = pending("750000.00")
        service, repository = service_for(invoice, clock=TickingClock())

        first = service.approve("INV-1", "demo.director", "Director")
        assert first.status == InvoiceStatus.PENDING_APPROVAL

        second = service.approve("INV-1", "demo.director2", "Director")

        assert second.status == InvoiceStatus.APPROVED
        assert second.decided_by == "demo.director2"
        assert [vote.username for vote in second.approvals] == ["demo.director", "demo.director2"]
        assert second.amount == invoice.amount
        assert repository.updates == 2

    def test_same_user_cannot_be_both_approvers_and_invoice_is_unchanged(self):
        invoice = pending("750000.00")
        service, repository = service_for(invoice, clock=TickingClock())
        service.approve("INV-1", "demo.director", "Director")
        recorded = snapshot(repository.get_by_id("INV-1"))
        updates = repository.updates

        with pytest.raises(ApprovalDenied, match="same user may never count as both approvers"):
            service.approve("INV-1", "demo.director", "Director")

        assert_unchanged(repository, recorded, updates)
        assert repository.get_by_id("INV-1").status == InvoiceStatus.PENDING_APPROVAL

    def test_same_user_cannot_vote_twice_by_padding_their_username(self):
        invoice = pending("750000.00")
        service, repository = service_for(invoice, clock=TickingClock())
        service.approve("INV-1", "demo.director", "Director")
        recorded = snapshot(repository.get_by_id("INV-1"))
        updates = repository.updates

        with pytest.raises(ApprovalDenied, match="same user"):
            service.approve("INV-1", "  demo.director  ", "Director")

        assert_unchanged(repository, recorded, updates)

    def test_second_approver_must_be_a_director_and_invoice_is_unchanged(self):
        invoice = pending("750000.00")
        service, repository = service_for(invoice, clock=TickingClock())
        service.approve("INV-1", "demo.director", "Director")
        recorded = snapshot(repository.get_by_id("INV-1"))
        updates = repository.updates

        with pytest.raises(ApprovalDenied, match="second approver on invoice INV-1 must be a director"):
            service.approve("INV-1", "demo.manager", "Manager")

        assert_unchanged(repository, recorded, updates)
        assert [vote.username for vote in repository.get_by_id("INV-1").approvals] == ["demo.director"]

    def test_a_different_director_can_finish_after_a_refused_second_vote(self):
        invoice = pending("750000.00")
        service, _repository = service_for(invoice, clock=TickingClock())
        service.approve("INV-1", "demo.director", "Director")
        with pytest.raises(ApprovalDenied):
            service.approve("INV-1", "demo.director", "Director")
        with pytest.raises(ApprovalDenied):
            service.approve("INV-1", "demo.manager", "Manager")

        result = service.approve("INV-1", "demo.director2", "Director")

        assert result.status == InvoiceStatus.APPROVED
        assert [vote.username for vote in result.approvals] == ["demo.director", "demo.director2"]

    def test_approver_role_cannot_be_the_second_vote(self):
        invoice = pending("750000.00")
        service, repository = service_for(invoice, clock=TickingClock())
        service.approve("INV-1", "demo.director", "Director")
        recorded = snapshot(repository.get_by_id("INV-1"))
        updates = repository.updates

        with pytest.raises(ApprovalDenied, match="must be a director"):
            service.approve("INV-1", "demo.approver", "Approver")

        assert_unchanged(repository, recorded, updates)


class TestLifecycleGuards:
    def test_approve_rejects_a_draft_and_leaves_it(self):
        invoice = pending("100.00")
        invoice.status = InvoiceStatus.DRAFT
        service, repository = service_for(invoice)
        before = snapshot(invoice)

        with pytest.raises(InvoiceConflict, match="only pending invoices"):
            service.approve("INV-1", "demo.manager", "Manager")

        assert_unchanged(repository, before, updates=0)

    def test_second_decision_on_an_approved_invoice_does_not_replace_the_approver(self):
        invoice = pending("100.00")
        clock = TickingClock()
        service, repository = service_for(invoice, clock=clock)
        service.approve("INV-1", "demo.manager", "Manager")
        recorded = snapshot(repository.get_by_id("INV-1"))
        updates = repository.updates

        with pytest.raises(InvoiceConflict, match="only pending invoices"):
            service.approve("INV-1", "demo.director", "Director")

        assert_unchanged(repository, recorded, updates)
        assert recorded["decided_by"] == "demo.manager"

    def test_approve_unknown_invoice(self):
        service, _repository = service_for()

        with pytest.raises(InvoiceNotFound, match="INV-404"):
            service.approve("INV-404", "demo.manager", "Manager")

    def test_reject_records_reason_and_approver(self):
        invoice = pending("100.00")
        service, _repository = service_for(invoice, clock=lambda: FIXED)

        result = service.reject("INV-1", "demo.manager", "Duplicate invoice")

        assert result.status == InvoiceStatus.REJECTED
        assert result.decision_note == "Duplicate invoice"
        assert result.decided_by == "demo.manager"
        assert result.decided_at == FIXED

    def test_reject_requires_a_reason_and_leaves_the_invoice(self):
        invoice = pending("100.00")
        service, repository = service_for(invoice)
        before = snapshot(invoice)

        with pytest.raises(ValueError, match="reason is required"):
            service.reject("INV-1", "demo.manager", "   ")

        assert_unchanged(repository, before, updates=0)

    def test_reject_after_a_first_high_value_vote_keeps_that_vote_as_history(self):
        invoice = pending("750000.00")
        service, _repository = service_for(invoice, clock=TickingClock())
        service.approve("INV-1", "demo.director", "Director")

        result = service.reject("INV-1", "demo.manager", "Vendor dispute")

        assert result.status == InvoiceStatus.REJECTED
        assert result.decision_note == "Vendor dispute"
        assert [vote.username for vote in result.approvals] == ["demo.director"]
        assert result.amount == invoice.amount
