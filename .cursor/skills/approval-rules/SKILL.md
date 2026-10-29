---
name: approval-rules
description: >-
  Use when editing invoice approval, role limits, the approval API, or tests
  of approve/reject. States the manager and director ceilings, the two-director
  rule, and the requirement that a refusal leaves the invoice unchanged.
---

# Approval rules

Read `specs/001-role-approval-limits/spec.md` before changing approval behavior.

- Manager sole ceiling: 50,000.00 inclusive. A manager never votes above that, including on invoices above 500,000.00.
- Director sole ceiling: 500,000.00 inclusive.
- Above 500,000.00: two different directors. The first vote stays pending. The second completes approval.
- Same username, after trimming, cannot vote twice.
- Build the next state in memory. Assign fields and call `update` only after the decision is allowed.
- Money uses `decimal.Decimal`.
- The UI displays the server reason. It does not re-implement the ceilings.
- Tests for a refusal must snapshot the invoice and assert the repository update count did not change.
