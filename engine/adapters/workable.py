from __future__ import annotations
import re
from engine.adapters.base import ATSAdapter
from engine.core.models import ApplyResult, ApplyStatus, Question
class WorkableAdapter(ATSAdapter):
    ats_name = "workable"
    async def _run(self, job_url, profile, resume_pdf, answers, page, context):
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000); receipt = {}; missing = []
        for selector, value, key in [("#firstname, input[name='firstname']", profile.full_name.split()[0] if profile.full_name else "", "first_name"), ("#lastname, input[name='lastname']", profile.full_name.split()[-1] if profile.full_name else "", "last_name"), ("#email, input[name='email']", profile.email, "email"), ("input[name='phone'], input[type='tel']", profile.phone, "phone")]:
            if value and await self._safe_fill(page, selector, value): receipt[key] = value
        if await self._upload_file(page, "input[type='file']", resume_pdf): receipt["resume"] = "resume.pdf"; await self.recorder.record_field(page, "resume", "resume.pdf")
        for group in await page.locator("[data-ui='field'], div[class*='field']").all():
            label = (await group.locator("label").first.text_content() or "").strip(); clean = re.sub(r"\*|\(required\)", "", label).strip(); key = re.sub(r"[^a-z0-9]+", "_", clean.lower()).strip("_")[:60]; value = answers.get(key) or answers.get(clean)
            sel = group.locator("select").first; inp = group.locator("input[type='text'], input[type='number'], textarea").first
            if await sel.count():
                opts = [(await o.text_content() or "").strip() for o in await sel.locator("option").all() if (await o.text_content() or "").strip()]
                if value: await sel.select_option(label=str(value)); receipt[key] = value
                elif "*" in label: missing.append(Question(key, clean, "select", opts))
            elif await inp.count():
                if value: await inp.fill(str(value)); receipt[key] = value
                elif "*" in label: missing.append(Question(key, clean, "text"))
        if missing: return ApplyResult(status=ApplyStatus.NEEDS_INPUT, run_id=self.run_id, questions=missing, receipt=receipt)
        text = await self._submit_form(page, "button[type='submit']:visible, input[type='submit']:visible"); self.recorder.save_receipt(receipt, text); return ApplyResult(status=ApplyStatus.SUBMITTED, run_id=self.run_id, receipt=receipt, confirmation_text=text)
