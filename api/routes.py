from __future__ import annotations

import base64
import json
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from engine.core import engine
from engine.core.models import Profile
from engine.core.recorder import RECORDINGS_ROOT

router = APIRouter()

class ApplyRequest(BaseModel):
    job_url: str
    profile: dict[str, Any]
    resume_pdf_b64: str

class ResumeRequest(BaseModel):
    answers: dict[str, Any]

@router.post("/apply")
async def start_apply(req: ApplyRequest):
    try:
        if not req.resume_pdf_b64: raise ValueError("resume_pdf_b64 is required")
        resume_pdf = base64.b64decode(req.resume_pdf_b64)
        if not resume_pdf.startswith(b"%PDF-"): raise ValueError("resume_pdf_b64 must contain a PDF file")
        profile = Profile.from_dict(req.profile) if req.profile else Profile.from_resume_pdf(resume_pdf)
        if not profile.full_name and not profile.email and not profile.phone: profile = Profile.from_resume_pdf(resume_pdf)
    except Exception as exc: raise HTTPException(status_code=400, detail=f"Bad request: {exc}")
    return (await engine.apply(req.job_url, profile, resume_pdf)).to_dict()

@router.post("/apply/{run_id}/resume")
async def resume_apply(run_id: str, req: ResumeRequest):
    return (await engine.apply_resume(run_id, req.answers)).to_dict()

@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    state = engine.get_run(run_id)
    if state is None: raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": state.run_id, "job_url": state.job_url, "ats": state.ats, "status": state.status, "pending_questions": state.pending_questions, "filled_fields": state.filled_fields, "confirmation_text": state.confirmation_text}

@router.get("/runs/{run_id}/log")
async def get_run_log(run_id: str):
    log_path = RECORDINGS_ROOT / run_id / "fill_log.json"
    if not log_path.exists(): raise HTTPException(status_code=404, detail="Fill log not found")
    try: entries = json.loads(log_path.read_text(encoding="utf-8"))
    except Exception as exc: raise HTTPException(status_code=500, detail=f"Could not read fill log: {exc}")
    return {"run_id": run_id, "steps": entries}
