from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

RECORDINGS_ROOT = Path(os.getenv("RECORDINGS_DIR", "recordings"))

class RunRecorder:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.run_dir = RECORDINGS_ROOT / run_id
        self.screenshots_dir = self.run_dir / "screenshots"
        self.trace_dir = self.run_dir / "trace"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)
        self.trace_dir.mkdir(exist_ok=True)
        self._log: list[dict] = []
        self._step = 0
        log_path = self.run_dir / "fill_log.json"
        if log_path.exists():
            try:
                self._log = json.loads(log_path.read_text())
                self._step = max((entry.get("step", 0) for entry in self._log), default=0)
            except (OSError, ValueError, TypeError): pass

    async def record_field(self, page, field: str, value: Any, source: str = "profile") -> None:
        self._step += 1
        screenshot_path = self.screenshots_dir / f"{self._step:03d}_{field[:40]}.png"
        try: await page.screenshot(path=str(screenshot_path), full_page=False)
        except Exception: screenshot_path = None
        self._log.append({"step": self._step, "field": field, "value": value, "source": source, "timestamp": time.time(), "screenshot": str(screenshot_path) if screenshot_path else None})
        self._flush_log()

    def record_event(self, event: str, detail: Any = None) -> None:
        self._step += 1
        self._log.append({"step": self._step, "event": event, "detail": detail, "timestamp": time.time()})
        self._flush_log()

    def _flush_log(self) -> None:
        with open(self.run_dir / "fill_log.json", "w") as handle: json.dump(self._log, handle, indent=2, default=str)

    def save_receipt(self, receipt: dict, confirmation_text: str = "") -> None:
        with open(self.run_dir / "receipt.json", "w") as handle: json.dump({"receipt": receipt, "confirmation_text": confirmation_text}, handle, indent=2, default=str)

    async def start_trace(self, context) -> None:
        try: await context.tracing.start(screenshots=True, snapshots=True, sources=False)
        except Exception: pass

    async def stop_trace(self, context) -> None:
        try: await context.tracing.stop(path=str(self.trace_dir / "trace.zip"))
        except Exception: pass

    async def capture_failure_screenshot(self, page) -> str | None:
        try:
            data = await page.screenshot(full_page=False)
            (self.run_dir / "failure.png").write_bytes(data)
            return base64.b64encode(data).decode()
        except Exception: return None
