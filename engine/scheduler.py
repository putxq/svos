import asyncio
import json
import logging
import traceback
from datetime import datetime, timedelta
from typing import Any

from engine.autonomous_loop import AutonomousLoop
from tools.email_tool import EmailTool
from core.json_parser import parse_llm_json

logger = logging.getLogger("svos.scheduler")


class SVOSScheduler:
    """
    ط§ظ„ظ…ط¬ط¯ظˆظگظ„ â€” ظٹط´ط؛ظ‘ظ„ ط§ظ„ط­ظ„ظ‚ط© ط§ظ„ظ…ط³طھظ‚ظ„ط© ط¹ظ„ظ‰ ط¬ط¯ظˆظ„ ط²ظ…ظ†ظٹ ط­ظ‚ظٹظ‚ظٹ.
    ظٹط¯ط¹ظ…: ط¯ظˆط±ط© ظƒظ„ X ط³ط§ط¹ط§طھ + طھظ‚ط§ط±ظٹط± ط¨ط§ظ„ط¥ظٹظ…ظٹظ„ + self-healing.
    """

    def __init__(self):
        self.loop = AutonomousLoop()
        self.email = EmailTool()
        self.is_running = False
        self.task: asyncio.Task | None = None
        self.company_profile: dict = {}
        self.founder_email: str = ""
        self.interval_hours: float = 6.0
        self.max_retries: int = 3
        self.history: list[dict] = []
        self.errors: list[dict] = []
        self.started_at: str | None = None
        self.last_cycle_at: str | None = None
        self.next_cycle_at: str | None = None

    def configure(
        self,
        company_profile: dict,
        founder_email: str = "",
        interval_hours: float = 6.0,
    ):
        """ط¥ط¹ط¯ط§ط¯ ط§ظ„ظ…ط¬ط¯ظˆظگظ„."""
        self.company_profile = company_profile
        self.founder_email = founder_email
        self.interval_hours = max(0.5, interval_hours)  # minimum 30 min

    async def _run_cycle_safe(self) -> dict:
        """ظٹط´ط؛ظ‘ظ„ ط¯ظˆط±ط© ظˆط§ط­ط¯ط© ظ…ط¹ self-healing."""
        for attempt in range(1, self.max_retries + 1):
            try:
                report = await self.loop.run_one_cycle(self.company_profile)
                report["attempt"] = attempt
                report["error"] = None
                return report
            except Exception as e:
                error_info = {
                    "cycle": self.loop.cycle_count + 1,
                    "attempt": attempt,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                self.errors.append(error_info)
                logger.error(f"Cycle failed (attempt {attempt}/{self.max_retries}): {e}")

                if attempt < self.max_retries:
                    wait = 30 * attempt  # 30s, 60s, 90s
                    logger.info(f"Retrying in {wait}s...")
                    await asyncio.sleep(wait)

        # All retries failed
        return {
            "cycle": self.loop.cycle_count,
            "success": False,
            "executed": False,
            "error": f"Failed after {self.max_retries} attempts",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _send_report_email(self, report: dict):
        """ظٹط±ط³ظ„ طھظ‚ط±ظٹط± ط§ظ„ط¯ظˆط±ط© ط¨ط§ظ„ط¥ظٹظ…ظٹظ„ ظ„ظ„ظ…ط¤ط³ط³."""
        if not self.founder_email:
            return

        cycle = report.get("cycle", 0)
        success = report.get("success", False)
        status = "ظ†ط¬ط­طھ" if success else "طھط­طھط§ط¬ ظ…ط±ط§ط¬ط¹ط©"

        subject = f"[SVOS] طھظ‚ط±ظٹط± ط§ظ„ط¯ظˆط±ط© #{cycle} â€” {status}"

        body_lines = [
            f"طھظ‚ط±ظٹط± ط§ظ„ط¯ظˆط±ط© ط§ظ„ظ…ط³طھظ‚ظ„ط© #{cycle}",
            f"ط§ظ„ظˆظ‚طھ: {report.get('timestamp', 'â€”')}",
            f"ط§ظ„ط­ط§ظ„ط©: {status}",
            "",
            f"ط§ظ„ظ‚ط±ط§ط±: {report.get('decision', 'â€”')}",
            f"ط§ظ„ظ…ظƒظ„ظ‘ظپ: {report.get('assigned_to', 'â€”')}",
            f"ط§ظ„ظ†طھظٹط¬ط©: {report.get('result', 'â€”')}",
            f"ظ†ظڈظپظ‘ط°: {'ظ†ط¹ظ…' if report.get('executed') else 'ظ„ط§'}",
            "",
            f"ط£ظˆظ„ظˆظٹط§طھ ط§ظ„ظٹظˆظ…: {', '.join(report.get('briefing_priorities', [])[:3])}",
            f"ظپط±طµ ط§ظ„ط³ظˆظ‚: {report.get('market_opportunities', 0)}",
            "",
            "---",
            "SVOS â€” Sovereign Ventures Operating System",
        ]
        body = "\n".join(body_lines)

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;direction:rtl">
            <div style="background:linear-gradient(135deg,#0a0a1a,#1a1a3e);padding:24px;border-radius:12px 12px 0 0">
                <h1 style="color:#00d4ff;margin:0;font-size:20px">SVOS â€” طھظ‚ط±ظٹط± ط§ظ„ط¯ظˆط±ط© #{cycle}</h1>
                <p style="color:#64748b;margin:8px 0 0">{'âœ… ظ†ط¬ط­طھ' if success else 'âڑ ï¸ڈ طھط­طھط§ط¬ ظ…ط±ط§ط¬ط¹ط©'}</p>
            </div>
            <div style="background:#111128;padding:20px;color:#e2e8f0">
                <div style="background:#1a1a3e;padding:16px;border-radius:8px;margin-bottom:12px">
                    <strong style="color:#00d4ff">ط§ظ„ظ‚ط±ط§ط±:</strong>
                    <p style="margin:8px 0 0">{report.get('decision', 'â€”')}</p>
                </div>
                <div style="background:#1a1a3e;padding:16px;border-radius:8px;margin-bottom:12px">
                    <strong style="color:#10b981">ط§ظ„ظ†طھظٹط¬ط©:</strong>
                    <p style="margin:8px 0 0">{report.get('result', 'â€”')}</p>
                </div>
                <div style="display:flex;gap:12px;flex-wrap:wrap">
                    <div style="background:#1a1a3e;padding:12px;border-radius:8px;flex:1;text-align:center">
                        <div style="color:#00d4ff;font-size:24px;font-weight:bold">{report.get('market_opportunities', 0)}</div>
                        <div style="color:#64748b;font-size:12px">ظپط±طµ ط§ظ„ط³ظˆظ‚</div>
                    </div>
                    <div style="background:#1a1a3e;padding:12px;border-radius:8px;flex:1;text-align:center">
                        <div style="color:#10b981;font-size:24px;font-weight:bold">{'âœ…' if report.get('executed') else 'âڑ ï¸ڈ'}</div>
                        <div style="color:#64748b;font-size:12px">ط§ظ„طھظ†ظپظٹط°</div>
                    </div>
                </div>
            </div>
            <div style="background:#0a0a1a;padding:12px;text-align:center;border-radius:0 0 12px 12px">
                <p style="color:#64748b;font-size:11px;margin:0">SVOS â€” Sovereign Ventures Operating System</p>
            </div>
        </div>"""

        try:
            await self.email.execute(
                to=self.founder_email,
                subject=subject,
                body=body,
                html=html,
            )
            logger.info(f"Report email sent to {self.founder_email}")
        except Exception as e:
            logger.warning(f"Failed to send report email: {e}")

    async def _scheduler_loop(self):
        """ط§ظ„ط­ظ„ظ‚ط© ط§ظ„ط±ط¦ظٹط³ظٹط© â€” طھط¹ظ…ظ„ ط¨ظ„ط§ طھظˆظ‚ظپ."""
        self.started_at = datetime.utcnow().isoformat()
        logger.info(f"Scheduler started. Interval: {self.interval_hours}h")

        while self.is_running:
            self.last_cycle_at = datetime.utcnow().isoformat()
            next_time = datetime.utcnow() + timedelta(hours=self.interval_hours)
            self.next_cycle_at = next_time.isoformat()

            # Run cycle
            report = await self._run_cycle_safe()
            self.history.append(report)

            # Send email report
            await self._send_report_email(report)

            # Wait for next cycle
            if self.is_running:
                wait_seconds = self.interval_hours * 3600
                logger.info(f"Next cycle at {self.next_cycle_at}")
                await asyncio.sleep(wait_seconds)

    def start(self, company_profile: dict, founder_email: str = "", interval_hours: float = 6.0):
        """ظٹط¨ط¯ط£ ط§ظ„ظ…ط¬ط¯ظˆظگظ„ ظپظٹ ط§ظ„ط®ظ„ظپظٹط©."""
        if self.is_running:
            return {"status": "already_running", "cycles": self.loop.cycle_count}

        self.configure(company_profile, founder_email, interval_hours)
        self.is_running = True

        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self._scheduler_loop())

        return {
            "status": "started",
            "interval_hours": self.interval_hours,
            "founder_email": self.founder_email or "not set",
            "started_at": datetime.utcnow().isoformat(),
        }

    def stop(self):
        """ظٹظˆظ‚ظپ ط§ظ„ظ…ط¬ط¯ظˆظگظ„."""
        self.is_running = False
        self.loop.stop()

        if self.task and not self.task.done():
            self.task.cancel()

        return {
            "status": "stopped",
            "total_cycles": self.loop.cycle_count,
            "stopped_at": datetime.utcnow().isoformat(),
        }

    def get_status(self) -> dict:
        """ط­ط§ظ„ط© ط§ظ„ظ…ط¬ط¯ظˆظگظ„ ط§ظ„ط­ط§ظ„ظٹط©."""
        return {
            "is_running": self.is_running,
            "total_cycles": self.loop.cycle_count,
            "interval_hours": self.interval_hours,
            "started_at": self.started_at,
            "last_cycle_at": self.last_cycle_at,
            "next_cycle_at": self.next_cycle_at,
            "founder_email": self.founder_email or "not set",
            "recent_history": self.history[-5:],
            "recent_errors": self.errors[-5:],
        }

