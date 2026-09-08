from __future__ import annotations

import base64
import json
import asyncio
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from engine.adapters.ashby import AshbyAdapter
from engine.adapters.base import ATSAdapter
from engine.adapters.greenhouse import GreenhouseAdapter
from engine.adapters.lever import LeverAdapter
from engine.adapters.workable import WorkableAdapter
from engine.core import event_bus
from engine.core.models import ATS_HOST_MAP, ATSPlatform, ApplyResult, ApplyStatus, Profile, RunState
from engine.core.recorder import RunRecorder

RUNS_DIR = Path("runs")
RUNS_DIR.mkdir(exist_ok=True)

ADAPTER_MAP: dict[ATSPlatform, type[ATSAdapter]] = {
    ATSPlatform.LEVER: LeverAdapter,
    ATSPlatform.ASHBY: AshbyAdapter,
    ATSPlatform.GREENHOUSE: GreenhouseAdapter,
    ATSPlatform.WORKABLE: WorkableAdapter,
}


def detect_ats(job_url: str) -> ATSPlatform:
    host = urlparse(job_url).netloc.lower().removeprefix("www.")
    return ATS_HOST_MAP.get(host, ATSPlatform.UNKNOWN)


def _save_run(state: RunState) -> None:
    (RUNS_DIR / f"{state.run_id}.json").write_text(json.dumps(state.__dict__, default=str))


def _load_run(run_id: str) -> RunState | None:
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        return None
    state = RunState.__new__(RunState)
    state.__dict__.update(json.loads(path.read_text()))
    state.status = ApplyStatus(state.__dict__["status"])
    state.ats = ATSPlatform(state.__dict__["ats"])
    return state


async def _run_adapter(run_id: str, job_url: str, ats: ATSPlatform, profile: Profile, resume_pdf: bytes, extra_answers: dict[str, Any]) -> ApplyResult:
    if ats == ATSPlatform.UNKNOWN:
        return ApplyResult(status=ApplyStatus.FAILED, run_id=run_id, reason=f"Unsupported ATS for URL: {job_url}", step="ats_detection")
    recorder = RunRecorder(run_id)
    result = await ADAPTER_MAP[ats](run_id=run_id, recorder=recorder).apply(
        job_url=job_url, profile=profile, resume_pdf=resume_pdf, extra_answers=extra_answers
    )
    result.run_id = run_id
    return result


async def apply(job_url: str, profile: Profile, resume_pdf: bytes) -> ApplyResult:
    run_id = str(uuid.uuid4())
    raw_profile = {
        "personalInfo": {
            "fullName": profile.full_name, "email": profile.email, "phone": profile.phone,
            "address": profile.address, "summary": profile.summary,
            "profiles": [
                {"network": "LinkedIn", "url": profile.linkedin_url},
                {"network": "GitHub", "url": profile.github_url},
                {"network": "Portfolio", "url": profile.portfolio_url},
            ],
        },
        "experience": profile.experience, "education": profile.education, "skills": profile.skills,
        "certifications": profile.certifications, "languages": profile.languages,
        "projects": profile.projects, "preferences": profile.preferences, "answers_bank": profile.answers_bank,
    }
    state = RunState(run_id=run_id, job_url=job_url, ats=detect_ats(job_url), profile=raw_profile,
                     resume_pdf_b64=base64.b64encode(resume_pdf).decode(), status=ApplyStatus.PENDING)
    _save_run(state)
    asyncio.create_task(_complete_apply(state, profile, resume_pdf))
    return ApplyResult(status=ApplyStatus.PENDING, run_id=run_id)


async def _complete_apply(state: RunState, profile: Profile, resume_pdf: bytes) -> None:
    try:
        result = await _run_adapter(state.run_id, state.job_url, state.ats, profile, resume_pdf, state.supplied_answers)
    except Exception as exc:
        result = ApplyResult(status=ApplyStatus.FAILED, run_id=state.run_id, reason=str(exc), step="worker")
    state.status = result.status
    state.pending_questions = [q.to_dict() for q in result.questions] if result.status == ApplyStatus.NEEDS_INPUT else []
    if result.receipt:
        state.filled_fields.update(result.receipt)
    if result.confirmation_text:
        state.confirmation_text = result.confirmation_text
    _save_run(state)
    payload = result.to_dict()
    payload["job_url"] = state.job_url
    event_bus.emit(state.run_id, result.status.value, payload)


async def apply_resume(run_id: str, answers: dict[str, Any]) -> ApplyResult:
    state = _load_run(run_id)
    if state is None:
        return ApplyResult(status=ApplyStatus.FAILED, run_id=run_id, reason="Run not found", step="resume")
    if state.status != ApplyStatus.NEEDS_INPUT:
        return ApplyResult(status=ApplyStatus.FAILED, run_id=run_id, reason=f"Run is not waiting for input (status: {state.status.value})", step="resume")
    state.supplied_answers.update(answers)
    state.status = ApplyStatus.PENDING
    _save_run(state)
    profile = Profile.from_dict(state.profile)
    profile.answers_bank.update(state.supplied_answers)
    asyncio.create_task(_complete_apply(state, profile, base64.b64decode(state.resume_pdf_b64)))
    return ApplyResult(status=ApplyStatus.PENDING, run_id=run_id)


def get_run(run_id: str) -> RunState | None:
    return _load_run(run_id)
