# Invoice approval limits

Python implementation of the workshop invoice-approval demo, with role limits.

A manager may sole-approve up to 50,000. A director may sole-approve up to 500,000. Above 500,000, two different directors must approve. A refused approval explains why and does not change the invoice.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn invoice_app.api.app:app --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000. Demo password for every account: `ChangeMe123!`

| User | Role |
| --- | --- |
| `demo.manager` | Manager, ceiling 50,000 |
| `demo.director` | Director, ceiling 500,000 |
| `demo.director2` | Second director for invoices above 500,000 |
| `demo.approver` | No approval authority |
| `demo.admin` | Can delete, cannot approve |

These are local demo accounts, not real credentials.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
cd e2e
npm install
npx playwright install chromium
npm test
```

The specification is in `specs/001-role-approval-limits/`. Agent rules are in `AGENTS.md`.
