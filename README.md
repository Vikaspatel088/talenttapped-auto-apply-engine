# Auto-Apply Engine — TalentTapped Intern Assignment

A service that takes a job posting URL, auto-fills the application from a candidate profile, batches any missing required fields into a single user-facing question, then resumes and submits.

## Architecture

- FastAPI backend with `POST /apply`, resume, run status, and SSE events.
- ApplyEngine detects the ATS and manages run state.
- Separate Playwright adapters for Greenhouse, Lever, Ashby, and Workable.
- React/Vite frontend consumes push events and displays questions, receipts, and notifications.

## Supported ATSes

| ATS | Host pattern | Status |
| --- | --- | --- |
| Lever | `jobs.lever.co` | Full submit (demo board) |
| Ashby | `jobs.ashbyhq.com` | Full submit |
| Greenhouse | `job-boards.greenhouse.io` | Full submit |
| Workable | `apply.workable.com` | Full submit |

## Quick Start

Prerequisites: Python 3.11+, Node 18+, and Playwright Chromium.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
cd frontend
npm install
cd ..
```

Start the backend in one terminal:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

Open `http://127.0.0.1:5174/`.

## API

`POST /apply` accepts `job_url`, a canonical `profile`, and base64 PDF resume bytes. It immediately returns `PENDING`; the final result is pushed over `/events`.

`POST /apply/{run_id}/resume` accepts an `answers` object and continues a paused run.

Terminal results are `SUBMITTED` with a receipt, `NEEDS_INPUT` with all missing questions, or `FAILED` with reason, step, and optional screenshot.

## Evidence

Each run records field screenshots, `fill_log.json`, `receipt.json`, and a Playwright trace under `recordings/<run_id>/`. The frontend receives terminal status through Server-Sent Events and shows toast and notification-center entries. The engine does not send email or other messages itself.

## Submission

See [SUBMISSION.md](SUBMISSION.md) for the complete requirements checklist, test URLs, evidence map, and demo instructions.

All adapters submit by default after required fields are filled. Set `ALLOW_LIVE_SUBMIT=0` for an explicit fill-only dry run against a live board.
