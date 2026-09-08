from __future__ import annotations
from engine.adapters.base import ATSAdapter
from engine.core.models import ApplyResult, ApplyStatus, Question
class GreenhouseAdapter(ATSAdapter):
    ats_name = "greenhouse"
    async def _run(self, job_url, profile, resume_pdf, answers, page, context):
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000); form = page; receipt = {}; missing = []
        for selector, value, key in [("#first_name", profile.full_name.split()[0] if profile.full_name else "", "first_name"), ("#last_name", profile.full_name.split()[-1] if profile.full_name else "", "last_name"), ("#email", profile.email, "email"), ("#phone", profile.phone, "phone")]:
            if value and await form.locator(selector).count(): await form.locator(selector).fill(value); receipt[key] = value
        if await self._upload_file(form, "input[type='file']", resume_pdf): receipt["resume"] = "resume.pdf"; await self.recorder.record_field(page, "resume", "resume.pdf")
        for wrapper in await form.locator(".field--wrapper, .custom-question, .form-field").all():
            label = (await wrapper.locator("label").first.text_content() or "").strip(); clean = label.replace("*", "").strip(); key = clean.lower().replace(" ", "_")[:60]; value = answers.get(key)
            select = wrapper.locator("select").first; inp = wrapper.locator("input[type='text'], input[type='number'], textarea").first
            if await select.count():
                opts = [(await o.text_content() or "").strip() for o in await select.locator("option").all() if (await o.text_content() or "").strip()]
                if value: await select.select_option(label=str(value)); receipt[key] = value
                elif "*" in label: missing.append(Question(key, clean, "select", opts))
            elif await inp.count():
                if value: await inp.fill(str(value)); receipt[key] = value
                elif "*" in label: missing.append(Question(key, clean, "text"))
        if missing: return ApplyResult(status=ApplyStatus.NEEDS_INPUT, run_id=self.run_id, questions=missing, receipt=receipt)
        text = await self._submit_form(page, "button[type='submit']:visible, input[type='submit']:visible"); self.recorder.save_receipt(receipt, text); return ApplyResult(status=ApplyStatus.SUBMITTED, run_id=self.run_id, receipt=receipt, confirmation_text=text)
