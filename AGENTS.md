# Project conventions for AI agents

Invoice approval demo, implemented in Python. Business rules live in the domain package. The web layer only maps HTTP.

## Approval rules

These are the rules. Do not soften them in the UI or the controller.

- A manager may sole-approve an invoice up to 50,000.00, inclusive.
- A director may sole-approve an invoice up to 500,000.00, inclusive.
- An amount above 500,000.00 needs two approvals from two different directors. The first vote stays pending. The second vote, from a different director, approves the invoice.
- A manager cannot vote on an invoice above 50,000.00, including as the first or second vote on an invoice above 500,000.00.
- The same user may never count as both approvers. Trimming spaces does not make a second username.
- A refused approval returns a clear reason and writes nothing. Status, amount, approver, timestamp, note, and recorded votes stay as they were.
- Approver and Admin are not approval authorities. Admin may delete an invoice. Rejection is separate from approval and does not use the amount limits.
- The approver's role comes from the server session. Ignore any role sent in the request body.

A first director vote on an invoice above 500,000.00 is a successful write: one recorded vote, status still `PendingApproval`, `decidedBy` still empty. That is not a refusal.

## Layout

- `invoice_app/domain`: invoice lifecycle and approval limits. No FastAPI, no storage.
- `invoice_app/api`: sign-in, in-memory repository, HTTP mapping, and the static UI.
- `invoice_app/static`: the web UI. It displays the server's reason. It does not re-decide the limit.
- `tests`: pytest. `test_approval_service.py` covers every approval rule, including both negative rules.
- `e2e`: one Playwright test for a manager refused on an invoice of 50,000.01.
- `specs/001-role-approval-limits`: the specification and the task breakdown.
- `.cursor/skills`: approval rules and the review-verdict format.
- `.cursor/agents`: implementer, test author, and reviewer.
- `.cursor/hooks`: appends a structured JSON line to `ai-interaction-log.jsonl`.

## Conventions

- Money is `decimal.Decimal`. Do not compare approval limits with `float`.
- Build the next approval state before assigning any field. A refusal must raise before `update`.
- Controllers return `{"error": "..."}` for a refusal. 400 is a refused approval or a missing rejection reason. 409 is a lifecycle conflict. 404 is a missing invoice.
- Every new rule needs a unit test that saves a snapshot and asserts the invoice is unchanged on refusal.
- End-to-end tests use page objects and role-based locators (`getByRole`, `getByLabel`).

## Commands

- Install: `python -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- Run the app: `.\.venv\Scripts\python.exe -m uvicorn invoice_app.api.app:app --host 127.0.0.1 --port 5000`
- Run the unit tests: `.\.venv\Scripts\python.exe -m pytest`
- Run the end-to-end test: `cd e2e; npm install; npx playwright install chromium; npm test`

## Demo accounts

These are local demo accounts, not real credentials. Password for each is `ChangeMe123!`.

- `demo.manager` — Manager
- `demo.director` — Director
- `demo.director2` — Director, so a second person can finish a high-value invoice
- `demo.approver` — Approver, cannot approve under the limit rules
- `demo.admin` — Admin, can delete, cannot approve

## Review expectations

Review the diff against the rules above, not against style nits. For every finding use one verdict: `fixed`, `dismissed`, or `deferred`, and give the reason. The format is in `.cursor/skills/review-verdicts/SKILL.md`.

## Never

- Do not commit real credentials, tokens, or customer data.
- Do not put approval limits in `app.py` or in `app.js`.
- Do not treat HTTP 200 as final approval. Read `status`.
