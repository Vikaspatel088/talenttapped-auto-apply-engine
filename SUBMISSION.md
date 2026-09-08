# TalentTapped Assignment Submission

## Requirements Checklist

- [x] Detect and route supported Greenhouse, Lever, Ashby, and Workable URLs.
- [x] Open forms with Playwright and walk the adapter-specific form fields.
- [x] Fill profile data, resume uploads, and known structured answers.
- [x] Collect all currently unfillable required fields into one `NEEDS_INPUT` batch.
- [x] Persist the run, profile, PDF, pending questions, supplied answers, and fields filled before a pause.
- [x] Resume the same run with one answer batch and continue to submission.
- [x] Record field values, sources, timestamps, screenshots, browser traces, and submission receipts per run.
- [x] Isolate ATS behavior behind separate adapters.
- [x] Return `SUBMITTED`, `NEEDS_INPUT`, or `FAILED` results through the API and SSE event flow.
- [x] Default EEO/demographic questions to `Decline to self-identify` when that option exists.
- [x] Submit every supported ATS form after all required fields are filled; set `ALLOW_LIVE_SUBMIT=0` only for an explicit fill-only dry run.
- [x] Ask profile questions in plain language; return dropdown options and default EEO questions to `Decline to self-identify` when verifiable.
- [x] Notify the user through push events and UI notifications instead of polling or sending messages from the engine.
- [x] Keep the run asynchronous so browser work can pause indefinitely at `NEEDS_INPUT`.

## Demo

Backend:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

Open `http://127.0.0.1:5174/` and use the Lever demo URL:

`https://jobs.lever.co/leverdemo/18c23ab2-ac77-473b-b2aa-ba13e0d52164`

For the batch-question demonstration, use:

`https://apply.workable.com/webuild-ai/j/5010161777/apply/`

## Test Job Links

- Lever: `jobs.lever.co`
- Ashby: `jobs.ashbyhq.com`
- Greenhouse: `job-boards.greenhouse.io`
- Workable: `apply.workable.com`

## Event-Driven Notifications

The worker emits `NEEDS_INPUT`, `SUBMITTED`, and `FAILED` through the event bus. `GET /events` exposes Server-Sent Events. The React frontend listens with `EventSource`, displays a toast, and adds a notification-center entry. The engine never sends email, SMS, or other messages.

## Requirement-to-Evidence Map

| Requirement | Evidence |
| --- | --- |
| Apply contract | `engine/core/engine.py` |
| ATS detection and isolation | `engine/core/engine.py` and `engine/adapters/` |
| Batch questions | `Question` objects returned as `NEEDS_INPUT` |
| Pause/resume | persisted `runs/<run_id>.json` |
| Receipt and field history | `recordings/<run_id>/receipt.json` and `fill_log.json` |
| Replay evidence | screenshots and Playwright trace |
| Push notifications | `engine/core/event_bus.py`, `api/main.py`, `frontend/src/hooks/useSSE.ts` |
| Tests | `tests/test_engine_contract.py` |

## Validation

```powershell
python -m unittest discover -s tests -v
python -m compileall -q engine api tests
cd frontend
npm run build
```

## Submission Contact

Replace these before final submission:

- Repository URL: `https://github.com/Vikaspatel088/talenttapped-auto-apply-engine`
- Name: `ADD_YOUR_NAME`
- Email: `ADD_YOUR_EMAIL`
- Recording link: `ADD_LOOM_OR_GOOGLE_DRIVE_LINK`

## Submission Mode

All adapters submit by default after required fields are filled. For a fill-only dry run:

```powershell
$env:ALLOW_LIVE_SUBMIT="0"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```
