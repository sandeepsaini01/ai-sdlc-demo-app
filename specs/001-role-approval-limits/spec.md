# Specification: single-approver ceilings

This step adds role ceilings to the invoice approval service. The two-approver rule is a later step.

## Rules

1. A manager may approve invoices up to 50,000.00, inclusive.
2. A director may approve invoices up to 500,000.00, inclusive.
3. A refused approval returns a clear reason, and nothing about the invoice changes.

Approver and Admin cannot approve. Amounts are decimal cents.

## Acceptance scenarios

- Given a pending invoice for 50,000.00, when a manager approves, then the invoice is Approved.
- Given a pending invoice for 50,000.01, when a manager approves, then the response explains the 50,000.00 ceiling and the invoice is unchanged.
- Given a pending invoice for 500,000.00, when a director approves, then the invoice is Approved.
- Given a pending invoice for 500,000.01, when a director approves, then the response explains the 500,000.00 ceiling and the invoice is unchanged.
- Given a pending invoice for 100.00, when an approver or an admin approves, then the invoice is unchanged.
- Given a refused manager attempt on 75,000.00, when a director later approves, then the invoice is Approved.
