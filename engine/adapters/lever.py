from __future__ import annotations
import re
from engine.adapters.base import ATSAdapter
from engine.core.models import ApplyResult, ApplyStatus, Question
class LeverAdapter(ATSAdapter):
    ats_name = "lever"
    async def _run(self, job_url, profile, resume_pdf, answers, page, context):
        url = job_url.rstrip("/") + ("" if job_url.rstrip("/").endswith("/apply") else "/apply"); await page.goto(url, wait_until="domcontentloaded", timeout=30000); receipt = {}; missing = []
        for selector, value, key in [("input[name='name']", profile.full_name, "full_name"), ("input[name='email']", profile.email, "email"), ("input[name='phone']", profile.phone, "phone")]:
            if value and await self._safe_fill(page, selector, value): receipt[key] = value; await self.recorder.record_field(page, key, value)
        if await self._upload_file(page, "input[type='file']", resume_pdf): receipt["resume"] = "resume.pdf"; await self.recorder.record_field(page, "resume", "resume.pdf")
        for item in await page.locator("li.application-question, .application-question").all():
            label = (await item.locator("label").first.text_content() or "").replace("*", "").strip()
            if not label: continue
            key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:60]; value = answers.get(key) or answers.get(label)
            select = item.locator("select").first
            if await select.count():
                options = [(await o.text_content() or "").strip() for o in await select.locator("option").all() if (await o.text_content() or "").strip()]
                if value: await select.select_option(label=str(value)); receipt[key] = value
                elif "*" in (await item.text_content() or ""): missing.append(Question(key, label, "select", options))
            else:
                inp = item.locator("input, textarea").first
                if await inp.count() and value: await inp.fill(str(value)); receipt[key] = value
                elif await inp.count() and "*" in (await item.text_content() or ""): missing.append(Question(key, label, "text"))
        if missing: return ApplyResult(status=ApplyStatus.NEEDS_INPUT, run_id=self.run_id, questions=missing, receipt=receipt)
        text = await self._submit_form(page, "#btn-submit:visible, button[type='submit']:visible, input[type='submit']:visible"); self.recorder.save_receipt(receipt, text); return ApplyResult(status=ApplyStatus.SUBMITTED, run_id=self.run_id, receipt=receipt, confirmation_text=text)
