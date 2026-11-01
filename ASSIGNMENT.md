# Assignment write-up

## What was asked

Take the invoice approval service from a written specification to a reviewed change, and keep the evidence around the feature: context an agent can use, tests that catch a real mistake, and a verdict on every review finding.

The reference application is the .NET demo at https://github.com/NITIN1670/ai-sdlc-demo-app.git. It lets any approver approve a pending invoice for any amount. This workspace implements that service in Python, which the assignment allows, and adds the role limits.

## The rules

- A manager may sole-approve an invoice up to 50,000.00, inclusive.
- A director may sole-approve an invoice up to 500,000.00, inclusive.
- Above 500,000.00, two different directors must approve. The first vote leaves the invoice pending. The second vote approves it.
- The same user never counts as both approvers. Trimming spaces does not create a second user.
- A refused approval returns a reason, and the invoice does not change: status, amount, approver, time, note, and recorded votes.

The last two rules are the ones a generated implementation is most likely to get almost right. The tests are written around them.

## Judgement calls

- A director's first vote above 500,000.00 is a successful write, not a refusal. The invoice stays `PendingApproval` and `decidedBy` stays empty until a second director votes.
- A manager cannot cast either vote above 50,000.00. The 50,000 ceiling is a hard cap. The "second approver must be a director" check is still separate, and a manager who tries to cast the second vote gets that reason. The first vote is left in place.
- The role comes from the signed-in session. A role in the request body is ignored.
- Rejection is not approval. Amount limits do not apply. If someone rejects an invoice that already has one high-value vote, the status becomes Rejected and that vote stays as history.
- Money is `decimal.Decimal`. The create API refuses a JSON number so a binary float cannot round the cents.

## What is in the repository

- `invoice_app/domain/approval_service.py` holds the rules. The next state is calculated before any field is assigned.
- `invoice_app/api` is the HTTP layer and the in-memory store. The screen is in `invoice_app/static`. It shows the server's reason and does not re-decide the limit.
- `specs/001-role-approval-limits/` is the specification and the task split: ceilings first, then the two-approver rule.
- `AGENTS.md`, `.cursor/skills/`, and `.cursor/agents/` are the context for a later agent.
- `.cursor/hooks/log_interaction.py` appends one JSON object per agent event to `ai-interaction-log.jsonl`. Passwords and bearer tokens are redacted.
- `tests/test_approval_service.py` covers every rule, including both negative rules.
- `e2e/tests/rejected-over-limit.spec.ts` is the Playwright test: a manager creates 50,000.01, is refused, and the row stays pending at $50,000.01.

## Tests

Unit and API tests, 21 October 2026:

```text
29 passed, 1 warning in 1.53s
```

The warning is from FastAPI's test client noting that `httpx` is deprecated in favor of `httpx2`. The tests passed.

Playwright, Chromium, against the running app:

```text
ok 1 [chromium] › tests\rejected-over-limit.spec.ts › a manager is refused above 50000 and the invoice stays pending (4.4s)
1 passed (9.1s)
```

## Mutation sample

`mutmut` 3.8.0 refuses to run on native Windows (`To run mutmut on Windows, please use the WSL`). WSL did not start a usable session here. Stryker, as named in the assignment, targets the .NET demo.

Four mutants of `approval_service.py` were applied one at a time, the file was restored afterward (`restored True`), and pytest was run twice for each: the old lifecycle tests only, then the full suite.

```text
director > flipped to >=
  before (lifecycle tests only): SURVIVED
  after (full suite): KILLED | test_director_can_approve_up_to_500000
manager <= flipped to <
  before (lifecycle tests only): SURVIVED
  after (full suite): KILLED | test_manager_can_approve_up_to_50000
same-user check disabled
  before (lifecycle tests only): SURVIVED
  after (full suite): KILLED | test_a_different_director_can_finish_after_a_refused_second_vote
second-director check disabled
  before (lifecycle tests only): SURVIVED
  after (full suite): KILLED | test_approver_role_cannot_be_the_second_vote
SAMPLE before: 0/4 killed
SAMPLE after: 4/4 killed
```

The lifecycle tests that only check submit, reject, and "not pending" do not notice a broken ceiling or a missing second-approver check. The limit tests do.

## Pull request description

### Summary

- Managers sole-approve up to 50,000. Directors sole-approve up to 500,000.
- Above 500,000, two different directors are required. A repeated user does not count.
- A refusal explains why and leaves the invoice unchanged.

### Review findings

- Finding: A padded username could be treated as a second approver.
- Where: `approval_service.py`, same-user check
- Verdict: fixed
- Reason: Usernames are trimmed before they are compared. `test_same_user_cannot_vote_twice_by_padding_their_username` locks it.

- Finding: A refusal could change the in-memory invoice and then raise, so the store would keep the change.
- Where: `approve` in `approval_service.py`
- Verdict: fixed
- Reason: The next state is built first. Fields are assigned only after the decision is allowed. Refusal tests compare a snapshot and the update count.

- Finding: The first vote above 500,000 returns HTTP 200, which a client might treat as final approval.
- Where: approve response and the Approvals screen
- Verdict: fixed
- Reason: The body stays `PendingApproval` with an empty `decidedBy`. The screen keeps any pending invoice in the list, including one that already has a vote.

- Finding: The browser could send `"role": "Director"` and raise a manager's authority.
- Where: `POST /api/approvals/{id}/approve`
- Verdict: fixed
- Reason: The role is read from the server session. The API test posts a Director role as the manager and is still refused.

- Finding: A manager cannot be the first of the two approvers on a large invoice.
- Where: specification, judgement calls
- Verdict: dismissed
- Reason: "A manager may approve invoices up to 50,000" is a ceiling on every manager vote, not only on sole approval. A manager who tries the second vote is refused because the second approver must be a director, and the first vote stays.

- Finding: `decidedBy` stores the director who completed the decision, not both names.
- Where: `Invoice.decided_by` and `approvals`
- Verdict: dismissed
- Reason: `decidedBy` is who completed the decision. Both usernames are stored on `approvals`, and the tests assert that list.

- Finding: Rejecting an invoice that already has one high-value vote keeps that vote.
- Where: `reject`
- Verdict: dismissed
- Reason: Rejection is a real decision, so the invoice is supposed to change. The status becomes Rejected, the reason is stored, and the earlier vote remains as history. A refused approval is the path that must change nothing.

- Finding: The original Approver account can no longer approve.
- Where: demo accounts
- Verdict: dismissed
- Reason: The specification names Manager and Director as the approval roles. `demo.approver` still signs in, and an approval attempt is refused with a clear reason.

- Finding: Demo passwords are stored in plain text.
- Where: `invoice_app/api/auth.py`
- Verdict: dismissed
- Reason: They are the workshop's local demo accounts, the same ones as `appsettings.json` in the reference app. They are not real credentials.

- Finding: Invoices disappear when the process stops.
- Where: `InMemoryInvoiceRepository`
- Verdict: dismissed
- Reason: The workshop app is in-memory so it runs with no database.

- Finding: The sentence on the Approvals tab repeats the ceilings and could drift from the domain constants.
- Where: `invoice_app/static/index.html`
- Verdict: deferred
- Reason: That sentence is instructions for the person at the screen. The enforced numbers and the tests live in the domain.

- Finding: Playwright does not click through the two-director path.
- Where: `e2e/tests/rejected-over-limit.spec.ts`
- Verdict: deferred
- Reason: The assignment asks for one end-to-end test of a refused over-limit approval. The two-director rule is covered by the unit and API tests.

- Finding: There is no full-file mutation score from mutmut or Stryker.
- Where: tooling
- Verdict: deferred
- Reason: mutmut 3.8.0 will not run on native Windows, and Stryker in the assignment targets .NET. The four-mutant sample above is the measurement that was actually run.

## Demo script for the video

Record 8 to 10 minutes with something running, not a file reading.

1. Start the app and open http://127.0.0.1:5000.
2. Sign in as `demo.manager`. Approve Cedar Ridge Schools, INV-1006, for 75,000. Show the reason and show that the invoice is still pending.
3. Sign out. Sign in as `demo.director` and approve INV-1006. It becomes Approved.
4. As `demo.director`, approve Northwind District, INV-1007, for 750,000. It stays pending and shows one recorded vote. Approve it again and show the same-user reason. The vote is still the one director.
5. Sign in as `demo.director2` and approve INV-1007. It becomes Approved, with both directors listed.
6. In a terminal, run `.\.venv\Scripts\python.exe -m pytest`.
7. In `e2e`, run `npx playwright test` and show the passing over-limit test.

```text
Video: https://nagarro-my.sharepoint.com/:v:/r/personal/sandeep_saini01_nagarro_com/Documents/3183943_sandeep_saini_ai_in_sdlc.mp4?d=wb543e4df5e5a4364bb339b586b7c7fd9&csf=1&web=1&nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=17MzUf
```

## Commits on this branch

1. Add single-approver ceilings for managers and directors.
2. Require two different directors above 500,000.
3. Add the end-to-end refusal test and this write-up.

The pull request description is the "Pull request description" section above. The demo video link is in the section above.
