from __future__ import annotations
import abc, base64, os, tempfile
from typing import Any
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from engine.core.models import ApplyResult, ApplyStatus, Profile, Question
from engine.core.recorder import RunRecorder
HEADED = os.getenv("HEADED", "0") == "1"
SLOW_MO = int(os.getenv("SLOW_MO", "0"))
ALLOW_LIVE_SUBMIT = os.getenv("ALLOW_LIVE_SUBMIT", "1") != "0"
class ATSAdapter(abc.ABC):
    ats_name = "unknown"
    def __init__(self, run_id: str, recorder: RunRecorder): self.run_id, self.recorder = run_id, recorder
    @property
    def allow_live_submit(self): return ALLOW_LIVE_SUBMIT
    async def apply(self, job_url: str, profile: Profile, resume_pdf: bytes, extra_answers: dict[str, Any] | None = None) -> ApplyResult:
        answers = dict(profile.answers_bank); answers.update(extra_answers or {})
        async with async_playwright() as pw:
            browser, context, page = await self._launch(pw); self.recorder.record_event("browser_launched", self.ats_name)
            try:
                await self.recorder.start_trace(context)
                result = await self._run(job_url, profile, resume_pdf, answers, page, context)
                await self.recorder.stop_trace(context); return result
            except Exception as exc:
                shot = await self.recorder.capture_failure_screenshot(page); await self.recorder.stop_trace(context)
                return ApplyResult(status=ApplyStatus.FAILED, run_id=self.run_id, reason=str(exc), step="unhandled_exception", screenshot_b64=shot)
            finally: await context.close(); await browser.close()
    @abc.abstractmethod
    async def _run(self, job_url, profile, resume_pdf, answers, page, context): ...
    async def _launch(self, pw):
        browser = await pw.chromium.launch(headless=not HEADED, slow_mo=SLOW_MO, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(viewport={"width": 1280, "height": 900}); return browser, context, await context.new_page()
    async def _safe_fill(self, page, selector, value):
        try: await page.locator(selector).first.fill(str(value), timeout=5000); return True
        except Exception: return False
    async def _upload_file(self, page, selector, data):
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f: f.write(data); path = f.name
            await page.locator(selector).first.set_input_files(path); return True
        except Exception: return False
        finally:
            if path:
                try: os.unlink(path)
                except OSError: pass
    async def _submit_form(self, page, selector):
        self.recorder.record_event("submit_click"); await page.locator(selector).first.click(); await page.wait_for_timeout(1500)
        text = (await page.locator("body").text_content() or "").strip(); self.recorder.record_event("submitted", text[:300]); return text[:300] or "Application submitted."
