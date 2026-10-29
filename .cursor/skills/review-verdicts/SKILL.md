---
name: review-verdicts
description: >-
  Use when reviewing an invoice-approval diff or writing the pull request
  description. Forces every finding into the same three-verdict format.
---

# Review verdicts

List every finding. Each finding uses this block and no other verdict words:

```text
- Finding: <one sentence>
- Where: <file or rule>
- Verdict: fixed | dismissed | deferred
- Reason: <why that verdict>
```

- `fixed` — the diff now matches the specification.
- `dismissed` — the note is not a defect. Say why.
- `deferred` — the note is real and out of scope for this feature. Say why it can wait.

Check these before style:

- Manager at 50,000.00 and at 50,000.01.
- Director at 500,000.00 and the first vote at 500,000.01.
- Same user twice, including a padded username.
- Second voter is not a director.
- A refusal leaves status, amount, approver, time, note, and votes unchanged.
- The client cannot supply a higher role.
