# Tasks: approval limits by role

The work is split so the single-approver ceilings land before the two-approver rule. Each step should be its own commit. Do not ask an agent for the whole feature in one prompt.

## Step 1 — Single-approver ceilings

- Add `Manager` and `Director` to the demo accounts.
- In the domain, allow a manager to sole-approve up to 50,000.00 and a director up to 500,000.00.
- Refuse every other role, and refuse a manager above 50,000.00, with a reason.
- On refusal, assign no fields and do not call `update`.
- Tests: 50,000.00 passes; 50,000.01 is refused and the snapshot matches; a later director approval of 75,000.00 still works; approver and admin are refused.
- Map the domain refusal to HTTP 400 `{"error": "..."}`. The UI shows that text.

## Step 2 — Two approvers above 500,000.00

- A director vote above 500,000.00 records one vote and leaves the invoice pending.
- A second, different director approves it.
- The same user, including a space-padded username, is refused and the first vote stays.
- A non-director second vote is refused with "must be a director" and the first vote stays.
- A manager cannot open the two-approver invoice.
- Tests cover both negative rules and a successful pair of directors.

## Step 3 — Proof around the rules

- One Playwright test: sign in as the manager, create 50,000.01, submit, approve, see the refusal, and see the invoice still pending with the same amount.
- Extend `AGENTS.md` so a cold agent sees the rules, the layers, the test command, and the review format.
- Log agent interactions as one JSON object per line.

## Done when

- `pytest` passes.
- The Playwright test passes against the running app.
- A refusal cannot change status, amount, approver, time, note, or recorded votes.
