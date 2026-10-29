# Tasks: approval limits by role

## Step 1 — Single-approver ceilings

- Allow a manager to sole-approve up to 50,000.00 and a director up to 500,000.00.
- Refuse every other role, and refuse an amount above the role ceiling, with a reason.
- On refusal, assign no fields and do not call `update`.
- Tests cover both boundaries and assert the invoice is unchanged.

## Step 2 — Two approvers above 500,000.00

Not in this commit. A later commit records the first director vote, requires a different director for the second vote, and rejects a repeated user without changing the invoice.

## Step 3 — End-to-end proof and write-up

Not in this commit. A later commit adds the Playwright refusal test and the assignment write-up.
