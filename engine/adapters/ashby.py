from __future__ import annotations
from engine.adapters.base import ATSAdapter
from engine.core.models import ApplyResult, ApplyStatus, Question
class AshbyAdapter(ATSAdapter):
    ats_name = "ashby"
    async def _run(self, job_url, profile, resume_pdf, answers, page, context):
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000); receipt = {}; missing = []
        if await self._upload_file(page, "input[type='file']", resume_pdf): receipt["resume"] = "resume.pdf"; await self.recorder.record_field(page, "resume", "resume.pdf")
        for label in await page.locator("label").all():
            text = (await label.text_content() or "").strip(); clean = text.replace("*", "").strip(); key = clean.lower().replace(" ", "_")[:60]
            inp = page.locator(f"#{await label.get_attribute('for')}").first if await label.get_attribute('for') else label.locator("xpath=following-sibling::*[1]").locator("input,textarea,select").first
            if not await inp.count(): continue
            value = answers.get(key) or ({"name": profile.full_name, "email": profile.email, "phone": profile.phone}.get(clean.lower(), ""))
            tag = await inp.evaluate("e => e.tagName.toLowerCase()")
            if value and tag in ("input", "textarea"): await inp.fill(str(value)); receipt[key] = value
            elif "*" in text: missing.append(Question(key, clean, "text"))
        if missing: return ApplyResult(status=ApplyStatus.NEEDS_INPUT, run_id=self.run_id, questions=missing, receipt=receipt)
        text = await self._submit_form(page, "button[type='submit']:visible"); self.recorder.save_receipt(receipt, text); return ApplyResult(status=ApplyStatus.SUBMITTED, run_id=self.run_id, receipt=receipt, confirmation_text=text)
