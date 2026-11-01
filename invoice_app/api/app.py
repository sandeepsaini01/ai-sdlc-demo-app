from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from invoice_app.api.auth import APPROVAL_ACTORS, DEMO_USERS, Session, SessionStore
from invoice_app.api.repository import InMemoryInvoiceRepository
from invoice_app.api.schemas import CreateInvoiceRequest, LoginRequest, RejectRequest
from invoice_app.domain.approval_service import ApprovalService
from invoice_app.domain.models import (
    ApprovalDenied,
    Invoice,
    InvoiceConflict,
    InvoiceNotFound,
    InvoiceStatus,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def to_out(invoice: Invoice) -> dict:
    return {
        "id": invoice.id,
        "customerName": invoice.customer_name,
        "amount": format(invoice.amount, "f"),
        "status": invoice.status.value,
        "createdAt": invoice.created_at.isoformat(),
        "decidedBy": invoice.decided_by,
        "decidedAt": invoice.decided_at.isoformat() if invoice.decided_at else None,
        "decisionNote": invoice.decision_note,
        "approvals": [
            {
                "username": vote.username,
                "role": vote.role,
                "decidedAt": vote.decided_at.isoformat(),
            }
            for vote in invoice.approvals
        ],
    }


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def create_app(repository: InMemoryInvoiceRepository | None = None) -> FastAPI:
    app = FastAPI(title="Invoice Approvals")
    app.state.repository = repository or InMemoryInvoiceRepository()
    app.state.sessions = SessionStore()

    def service() -> ApprovalService:
        return ApprovalService(app.state.repository)

    def current_session(authorization: str | None = Header(default=None)) -> Session:
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[len("Bearer ") :]
        session = app.state.sessions.get(token)
        if session is None:
            raise _AuthError("Sign in is required.")
        return session

    def approval_actor(session: Session = Depends(current_session)) -> Session:
        if session.role not in APPROVAL_ACTORS:
            raise _Forbidden("You cannot approve or reject invoices.")
        return session

    @app.exception_handler(_AuthError)
    def unauthorized(_request: Request, exc: _AuthError) -> JSONResponse:
        return _error(401, str(exc))

    @app.exception_handler(_Forbidden)
    def forbidden(_request: Request, exc: _Forbidden) -> JSONResponse:
        return _error(403, str(exc))

    @app.exception_handler(InvoiceNotFound)
    def missing(_request: Request, exc: InvoiceNotFound) -> JSONResponse:
        return _error(404, str(exc))

    @app.exception_handler(InvoiceConflict)
    def conflict(_request: Request, exc: InvoiceConflict) -> JSONResponse:
        return _error(409, str(exc))

    @app.exception_handler(ApprovalDenied)
    def denied(_request: Request, exc: ApprovalDenied) -> JSONResponse:
        return _error(400, str(exc))

    @app.exception_handler(ValueError)
    def bad_request(_request: Request, exc: ValueError) -> JSONResponse:
        return _error(400, str(exc))

    @app.exception_handler(RequestValidationError)
    def invalid(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(400, _validation_message(exc))

    @app.post("/api/auth/login")
    def login(body: LoginRequest) -> JSONResponse:
        user = DEMO_USERS.get(body.username)
        if user is None or user["password"] != body.password:
            return _error(401, "Invalid username or password.")
        token = app.state.sessions.create(Session(body.username, user["role"]))
        return JSONResponse(
            content={"token": token, "username": body.username, "role": user["role"]}
        )

    @app.post("/api/auth/logout")
    def logout(authorization: str | None = Header(default=None)) -> Response:
        if authorization and authorization.startswith("Bearer "):
            app.state.sessions.remove(authorization[len("Bearer ") :])
        return Response(status_code=204)

    @app.get("/api/invoices")
    def list_invoices(
        status: str | None = None,
        _session: Session = Depends(current_session),
    ) -> JSONResponse:
        invoices = app.state.repository.get_all()
        if status:
            try:
                parsed = InvoiceStatus(status)
            except ValueError:
                return _error(400, f"Unknown status '{status}'.")
            invoices = [invoice for invoice in invoices if invoice.status == parsed]
        return JSONResponse(content=[to_out(invoice) for invoice in invoices])

    @app.get("/api/invoices/{invoice_id}")
    def get_invoice(invoice_id: str, _session: Session = Depends(current_session)) -> JSONResponse:
        invoice = app.state.repository.get_by_id(invoice_id)
        if invoice is None:
            return _error(404, f"Invoice {invoice_id} was not found.")
        return JSONResponse(content=to_out(invoice))

    @app.post("/api/invoices")
    def create_invoice(
        body: CreateInvoiceRequest,
        _session: Session = Depends(current_session),
    ) -> JSONResponse:
        invoice = app.state.repository.add(
            Invoice(id="", customer_name=body.customer_name, amount=body.amount)
        )
        return JSONResponse(
            status_code=201,
            content=to_out(invoice),
            headers={"Location": f"/api/invoices/{invoice.id}"},
        )

    @app.post("/api/invoices/{invoice_id}/submit")
    def submit_invoice(
        invoice_id: str,
        _session: Session = Depends(current_session),
    ) -> JSONResponse:
        return JSONResponse(content=to_out(service().submit(invoice_id)))

    @app.delete("/api/invoices/{invoice_id}")
    def delete_invoice(invoice_id: str, session: Session = Depends(current_session)) -> JSONResponse:
        if session.role != "Admin":
            return _error(403, "Only an admin can delete an invoice.")
        if not app.state.repository.remove(invoice_id):
            return _error(404, f"Invoice {invoice_id} was not found.")
        return Response(status_code=204)

    @app.post("/api/approvals/{invoice_id}/approve")
    def approve_invoice(
        invoice_id: str,
        session: Session = Depends(approval_actor),
    ) -> JSONResponse:
        # Role comes from the server session. The request body cannot raise it.
        invoice = service().approve(invoice_id, session.username, session.role)
        return JSONResponse(content=to_out(invoice))

    @app.post("/api/approvals/{invoice_id}/reject")
    def reject_invoice(
        invoice_id: str,
        body: RejectRequest,
        session: Session = Depends(approval_actor),
    ) -> JSONResponse:
        invoice = service().reject(invoice_id, session.username, body.reason)
        return JSONResponse(content=to_out(invoice))

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
    return app


class _AuthError(Exception):
    pass


class _Forbidden(Exception):
    pass


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Request was invalid."
    error = errors[0]
    context = error.get("ctx") or {}
    reason = context.get("error")
    if isinstance(reason, Exception):
        return str(reason)
    message = str(error.get("msg", "Request was invalid."))
    prefix = "Value error, "
    if message.startswith(prefix):
        return message[len(prefix) :]
    return message


app = create_app()
