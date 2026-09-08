from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

try:
    import fitz
except Exception:
    fitz = None
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


def _normalize_url(value: str, kind: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    if kind == "linkedin": return "https://linkedin.com/in/" + value.lstrip("/")
    if kind == "github": return "https://github.com/" + value.lstrip("/")
    return value


def extract_resume_text(pdf_bytes: bytes) -> str:
    parts: list[str] = []
    if fitz is not None:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text = page.get_text("text")
                if text: parts.append(text)
            if parts: return "\n".join(parts)
        except Exception: pass
    if PdfReader is not None:
        try:
            reader = PdfReader(pdf_bytes)
            for page in reader.pages:
                text = page.extract_text() or ""
                if text: parts.append(text)
            if parts: return "\n".join(parts)
        except Exception: pass
    raw = pdf_bytes.decode("latin-1", errors="ignore")
    matches = re.findall(r"\(([^)]*)\)", raw)
    return "\n".join(matches) if matches else raw


@dataclass
class Profile:
    full_name: str
    email: str
    phone: str
    address: str
    summary: str
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    skills: list[dict] = field(default_factory=list)
    certifications: list[dict] = field(default_factory=list)
    languages: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    answers_bank: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        if not d: return cls("", "", "", "", "")
        info = d.get("personalInfo", {})
        profiles = {str(p.get("network", p.get("label", ""))).lower(): p.get("url", "") for p in info.get("profiles", []) if p.get("network") or p.get("label")}
        return cls(info.get("fullName", ""), info.get("email", ""), info.get("phone", ""), info.get("address", ""), info.get("summary", ""), profiles.get("linkedin", ""), profiles.get("github", ""), profiles.get("portfolio", ""), d.get("experience", []), d.get("education", []), d.get("skills", []), d.get("certifications", []), d.get("languages", []), d.get("projects", []), d.get("preferences", {}), d.get("answers_bank", {}))

    @classmethod
    def from_resume_pdf(cls, pdf_bytes: bytes) -> "Profile":
        text = extract_resume_text(pdf_bytes)
        lines = [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]
        joined = "\n".join(lines)
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", joined, re.I)
        phone_match = re.search(r"(?:\+?\d[\d()\- .]{7,}\d)", joined)
        full_name = lines[0] if lines else ""
        if len(full_name.split()) < 2:
            full_name = next((candidate for candidate in lines[1:5] if len(candidate.split()) >= 2), full_name)
        github = re.search(r"https?://github\.com/[^\s]+|github\.com/[^\s]+", joined, re.I)
        linkedin = re.search(r"https?://linkedin\.com/in/[^\s]+|linkedin\.com/in/[^\s]+", joined, re.I)
        keywords = [k for k in ["Python", "FastAPI", "React", "TypeScript", "JavaScript", "SQL", "PostgreSQL", "Node.js", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Java", "C#", "Go", "Rust", "Django", "Flask", "MongoDB", "Redis", "CI/CD", "Terraform"] if re.search(rf"\b{re.escape(k)}\b", joined, re.I)]
        return cls(full_name, email_match.group(0) if email_match else "", phone_match.group(0).strip() if phone_match else "", "", " ".join(lines[1:7]), _normalize_url(linkedin.group(0) if linkedin else "", "linkedin"), _normalize_url(github.group(0) if github else "", "github"), skills=[{"category": "Skills", "keywords": keywords}] if keywords else [])


class ATSPlatform(str, Enum):
    LEVER = "lever"
    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    WORKABLE = "workable"
    UNKNOWN = "unknown"

ATS_HOST_MAP = {"jobs.lever.co": ATSPlatform.LEVER, "job-boards.greenhouse.io": ATSPlatform.GREENHOUSE, "jobs.ashbyhq.com": ATSPlatform.ASHBY, "apply.workable.com": ATSPlatform.WORKABLE}

class ApplyStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    NEEDS_INPUT = "NEEDS_INPUT"
    FAILED = "FAILED"

@dataclass
class Question:
    field: str
    label: str
    type: str
    options: list[str] = field(default_factory=list)
    required: bool = True
    def to_dict(self) -> dict:
        d = {"field": self.field, "label": self.label, "type": self.type, "required": self.required}
        if self.options: d["options"] = self.options
        return d

@dataclass
class ApplyResult:
    status: ApplyStatus
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    receipt: dict[str, Any] = field(default_factory=dict)
    confirmation_text: str = ""
    questions: list[Question] = field(default_factory=list)
    reason: str = ""
    step: str = ""
    screenshot_b64: Optional[str] = None
    def to_dict(self) -> dict:
        d = {"status": self.status.value, "run_id": self.run_id}
        if self.status == ApplyStatus.SUBMITTED: d.update(receipt=self.receipt, confirmation_text=self.confirmation_text)
        elif self.status == ApplyStatus.NEEDS_INPUT: d["questions"] = [q.to_dict() for q in self.questions]
        elif self.status == ApplyStatus.FAILED:
            d.update(reason=self.reason, step=self.step)
            if self.screenshot_b64: d["screenshot"] = self.screenshot_b64
        return d

@dataclass
class RunState:
    run_id: str
    job_url: str
    ats: ATSPlatform
    profile: dict
    resume_pdf_b64: str
    status: ApplyStatus = ApplyStatus.NEEDS_INPUT
    pending_questions: list[dict] = field(default_factory=list)
    supplied_answers: dict[str, Any] = field(default_factory=dict)
    filled_fields: dict[str, Any] = field(default_factory=dict)
    confirmation_text: str = ""
