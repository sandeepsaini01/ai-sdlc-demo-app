# Invoice approval limits

Python invoice approval service added alongside the workshop demo.

A manager may sole-approve up to 50,000. A director may sole-approve up to 500,000. A refused approval explains why and does not change the invoice.

## Run the Python app

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
| `demo.approver` | No approval authority |
| `demo.admin` | Can delete, cannot approve |

These are local demo accounts, not real credentials.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The original .NET demo is still under `backend/` and runs with `dotnet run --project backend/src/InvoiceApp.Api`.
