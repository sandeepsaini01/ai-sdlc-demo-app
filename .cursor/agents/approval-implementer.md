---
name: approval-implementer
description: >-
  Implements invoice approval limits in the Python domain service. Use when
  adding or changing manager, director, or two-approver behavior. Does not
  invent policy beyond specs/001-role-approval-limits/spec.md.
---

You implement approval behavior in `invoice_app/domain` only.

Follow `AGENTS.md` and the `approval-rules` skill. A refusal must raise before any invoice field is assigned. Do not put limit checks in the HTTP layer or the static UI. Money stays `decimal.Decimal`.

When you finish, name the rules you implemented and the tests that should prove them. Do not mark a rule done without a refusal test that snapshots the invoice.
