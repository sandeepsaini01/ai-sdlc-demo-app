# Project conventions for AI agents

Invoice approval demo. The assignment solution is the Python service in `invoice_app`. The original .NET app remains in `backend` for reference.

## Approval rules in this step

Single-approver ceilings only. Do not add the two-approver rule in this step.

- A manager may sole-approve an invoice up to 50,000.00, inclusive.
- A director may sole-approve an invoice up to 500,000.00, inclusive.
- Above either ceiling, the approval is refused.
- Approver and Admin are not approval authorities.
- A refused approval returns a clear reason and writes nothing. Status, amount, approver, timestamp, note, and recorded votes stay as they were.
- The approver's role comes from the server session. Ignore any role sent in the request body.

## Layout

- `invoice_app/domain`: invoice lifecycle and approval ceilings. No FastAPI, no storage.
- `invoice_app/api`: sign-in, in-memory repository, HTTP mapping, and the static UI.
- `invoice_app/static`: the web UI. It displays the server's reason. It does not re-decide the limit.
- `tests`: pytest for the ceiling rules and for a refusal that leaves the invoice unchanged.
- `specs/001-role-approval-limits`: the specification and the task breakdown.

## Conventions

- Money is `decimal.Decimal`. Do not compare approval limits with `float`.
- Build the next approval state before assigning any field. A refusal must raise before `update`.
- Controllers return `{"error": "..."}` for a refusal. 400 is a refused approval or a missing rejection reason. 409 is a lifecycle conflict. 404 is a missing invoice.
- Every new rule needs a unit test that saves a snapshot and asserts the invoice is unchanged on refusal.

## Commands

- Install: `python -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- Run the app: `.\.venv\Scripts\python.exe -m uvicorn invoice_app.api.app:app --host 127.0.0.1 --port 5000`
- Run the unit tests: `.\.venv\Scripts\python.exe -m pytest`

## Demo accounts

These are local demo accounts, not real credentials. Password for each is `ChangeMe123!`.

- `demo.manager` — Manager
- `demo.director` — Director
- `demo.director2` — Director
- `demo.approver` — Approver, cannot approve
- `demo.admin` — Admin, can delete, cannot approve

## Never

- Do not commit real credentials, tokens, or customer data.
- Do not put approval limits in `app.py` or in `app.js`.
- Do not treat HTTP 200 as final approval. Read `status`.
