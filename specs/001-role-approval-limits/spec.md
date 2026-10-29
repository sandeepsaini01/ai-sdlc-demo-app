# Specification: approval limits by role

Status: implemented in Python against the workshop invoice-approval demo.

The reference service approves or rejects a whole pending invoice with no regard to amount or role. This feature adds the limits below. The reference repository is https://github.com/NITIN1670/ai-sdlc-demo-app.git. This workspace reimplements that service in Python because the assignment allows any language.

## Actors

- Manager. Sole-approval ceiling: 50,000.00.
- Director. Sole-approval ceiling: 500,000.00. Also the only role that may vote on an invoice above 500,000.00.
- Approver and Admin remain in the demo. Neither may approve. Admin may still delete.

## Rules

1. A manager may approve invoices up to 50,000.00, inclusive.
2. A director may approve invoices up to 500,000.00, inclusive, in one vote.
3. Anything above 500,000.00 needs two distinct approvers, and the second approver must be a director. In this service both votes must be directors, because a manager is already over the 50,000.00 ceiling and cannot cast either vote.
4. The same user may never count as both approvers on one invoice.
5. A rejected attempt returns a clear reason, and nothing about the invoice changes.

Amounts are decimal cents. "Up to" includes the boundary. One cent over takes the next rule.

## Judgement calls

- A director's first vote above 500,000.00 is stored and the invoice stays `PendingApproval`. It is not a refusal. `decidedBy` stays empty until the second director votes. Refusal is reserved for attempts that must not write.
- A manager cannot be the first of the two approvers. "A manager may approve invoices up to 50,000" is a hard cap, not a hint that only applies to sole approval.
- The second-approver check is still explicit. A manager, approver, or admin who tries to cast the second vote is refused with "must be a director", and the first vote stays.
- Usernames are trimmed, then compared exactly. `demo.director` and `  demo.director  ` are the same user.
- The role is taken from the signed-in session. A role in the JSON body is ignored.
- Rejecting an invoice is not an approval. Amount limits do not apply. A rejection after a first high-value vote keeps that vote as history and sets the status to `Rejected`.
- HTTP 400 carries the refusal reason. HTTP 409 is only for "this invoice is not awaiting that action".

## Acceptance scenarios

### Manager ceiling

- Given a pending invoice for 50,000.00, when a manager approves, then the invoice is Approved and the manager is the approver.
- Given a pending invoice for 50,000.01, when a manager approves, then the response explains the 50,000.00 ceiling and the invoice is byte-for-byte unchanged: status, amount, approver, time, note, and votes.

### Director ceiling

- Given a pending invoice for 500,000.00, when a director approves, then the invoice is Approved.
- Given a pending invoice for 500,000.01, when a director approves, then the invoice stays PendingApproval, one director vote is recorded, and `decidedBy` is empty.

### Two approvers

- Given a pending invoice for 750,000.00 and one recorded director vote, when a different director approves, then the invoice is Approved and both usernames are stored.
- Given that same first vote, when the same director approves again, then the response says the same user may never count as both approvers, and the recorded vote is unchanged.
- Given that same first vote, when a manager approves, then the response says the second approver must be a director, and the recorded vote is unchanged.
- Given a pending invoice for 750,000.00 and no votes, when a manager approves, then the response cites the 50,000.00 ceiling and no vote is recorded.

### Other roles and lifecycle

- Given a pending invoice for 100.00, when an approver or an admin approves, then the response says that role cannot approve and the invoice is unchanged.
- Given a refused over-limit attempt, when a director later approves an invoice of 75,000.00, then that later approval succeeds.
- Given a draft, when someone approves, then the invoice stays a draft.
- Given an approved invoice, when a second person approves, then the original approver and time stay.
- Given a pending invoice, when someone rejects with a blank reason, then the invoice is unchanged.
- Given a pending invoice, when someone rejects with a reason, then the invoice is Rejected and the reason is stored.

## Out of scope

Bulk approval, partial amounts, email, persistence beyond process memory, and production authentication.

## Tasks

See [tasks.md](tasks.md).
