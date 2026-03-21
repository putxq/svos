import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("svos.scheduler")


class SVOSScheduler:
    """
    Autonomous Loop Scheduler with Self-Healing.
    Runs cycles: briefing -> market scan -> decision -> execution -> report
    Monitors agent health and auto-recovers from failures.
    """

    def __init__(self, cycle_hours: float = 12.0):
        self.cycle_hours = cycle_hours
        self.is_running = False
        self.current_cycle = 0
        self.last_cycle_time = None
        self.last_heartbeat = None
        self.cycle_history = []
        self.errors = []
        self.max_errors_before_pause = 3
        self.consecutive_errors = 0
        self._task = None
        logger.info(f"SVOSScheduler initialized | cycle every {cycle_hours}h")

    async def start(self):
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        self.is_running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Scheduler STARTED")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("Scheduler STOPPED")

    def get_status(self) -> dict:
        next_cycle = None
        if self.last_cycle_time:
            next_dt = self.last_cycle_time + timedelta(hours=self.cycle_hours)
            next_cycle = next_dt.isoformat()

        return {
            "is_running": self.is_running,
            "current_cycle": self.current_cycle,
            "cycle_interval_hours": self.cycle_hours,
            "last_cycle": self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            "next_cycle": next_cycle,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "consecutive_errors": self.consecutive_errors,
            "total_cycles_completed": len(self.cycle_history),
            "recent_errors": self.errors[-5:],
        }

    async def _loop(self):
        logger.info("Autonomous loop started")
        while self.is_running:
            try:
                await self._run_cycle()
                self.consecutive_errors = 0
                sleep_seconds = self.cycle_hours * 3600
                logger.info(f"Cycle complete. Next in {self.cycle_hours}h")
                await asyncio.sleep(sleep_seconds)
            except asyncio.CancelledError:
                logger.info("Loop cancelled")
                break
            except Exception as e:
                self.consecutive_errors += 1
                error_entry = {
                    "time": datetime.utcnow().isoformat(),
                    "cycle": self.current_cycle,
                    "error": str(e),
                    "consecutive": self.consecutive_errors,
                }
                self.errors.append(error_entry)
                logger.error(f"Cycle error #{self.consecutive_errors}: {e}")

                if self.consecutive_errors >= self.max_errors_before_pause:
                    logger.critical(
                        f"SELF-HEALING: {self.consecutive_errors} consecutive errors. "
                        f"Pausing for 1 hour before retry."
                    )
                    await self._notify_founder(
                        f"SVOS ALERT: {self.consecutive_errors} consecutive cycle failures. "
                        f"System paused for 1 hour. Last error: {str(e)[:200]}"
                    )
                    await asyncio.sleep(3600)
                    self.consecutive_errors = 0
                else:
                    backoff = min(300 * self.consecutive_errors, 1800)
                    logger.warning(f"Retrying in {backoff}s (backoff)")
                    await asyncio.sleep(backoff)

    async def _run_cycle(self):
        self.current_cycle += 1
        cycle_start = datetime.utcnow()
        self.last_cycle_time = cycle_start
        logger.info(f"=== CYCLE {self.current_cycle} START ===")

        cycle_result = {
            "cycle": self.current_cycle,
            "started": cycle_start.isoformat(),
            "phases": {},
            "success": False,
        }

        phase = await self._phase_briefing()
        cycle_result["phases"]["briefing"] = phase

        phase = await self._phase_market_scan()
        cycle_result["phases"]["market_scan"] = phase

        phase = await self._phase_decision(cycle_result["phases"])
        cycle_result["phases"]["decision"] = phase

        phase = await self._phase_execution(cycle_result["phases"])
        cycle_result["phases"]["execution"] = phase

        phase = await self._phase_report(cycle_result)
        cycle_result["phases"]["report"] = phase

        cycle_result["completed"] = datetime.utcnow().isoformat()
        cycle_result["duration_seconds"] = (datetime.utcnow() - cycle_start).total_seconds()
        cycle_result["success"] = True

        self.cycle_history.append(cycle_result)
        logger.info(f"=== CYCLE {self.current_cycle} COMPLETE ({cycle_result['duration_seconds']:.1f}s) ===")
        return cycle_result

    async def _phase_briefing(self) -> dict:
        logger.info("[Phase 1] Morning Briefing")
        try:
            from agents import AGENT_REGISTRY
            from core.config import settings

            ceo_cls = AGENT_REGISTRY.get("CEO")
            if not ceo_cls:
                return {"status": "skip", "reason": "CEO agent not found"}

            ceo = ceo_cls()
            result = await ceo.think(
                task="Generate a morning briefing for the SVOS system. "
                "Summarize system status, pending priorities, and recommended focus areas for today.",
                context="You are the CEO of a sovereign AI company called SVOS. "
                "The system has 9 C-suite agents, 4 execution tools, and runs autonomous cycles.",
            )
            return {"status": "done", "summary": str(result)[:500], "version": settings.app_version}
        except Exception as e:
            logger.error(f"Briefing phase error: {e}")
            return {"status": "error", "error": str(e)}

    async def _phase_market_scan(self) -> dict:
        logger.info("[Phase 2] Market Scan")
        try:
            from engines.gravity_engine import GravityEngine

            engine = GravityEngine()
            result = await engine.find_demand_gravity(
                "Saudi Arabia digital transformation SME automation AI solutions 2026"
            )
            return {"status": "done", "opportunities": str(result)[:500]}
        except Exception as e:
            logger.error(f"Market scan error: {e}")
            return {"status": "error", "error": str(e)}

    async def _phase_decision(self, previous_phases: dict) -> dict:
        logger.info("[Phase 3] Decision")
        try:
            from engines.time_engine import TimeEngine

            engine = TimeEngine()
            context = {
                "briefing": previous_phases.get("briefing", {}).get("summary", ""),
                "market": previous_phases.get("market_scan", {}).get("opportunities", ""),
            }
            decision_prompt = (
                "Based on today's briefing and market scan, "
                "what is the single most impactful action to take today?"
            )
            result = await engine.should_proceed(decision_prompt, context)
            return {"status": "done", "decision": str(result)[:500]}
        except Exception as e:
            logger.error(f"Decision phase error: {e}")
            return {"status": "error", "error": str(e)}

    async def _phase_execution(self, previous_phases: dict) -> dict:
        logger.info("[Phase 4] Execution")
        try:
            _ = previous_phases.get("decision", {})
            return {
                "status": "done",
                "actions_taken": [],
                "note": "Execution phase ready - tools registered but awaiting founder approval for real-world actions",
            }
        except Exception as e:
            logger.error(f"Execution phase error: {e}")
            return {"status": "error", "error": str(e)}

    async def _phase_report(self, cycle_result: dict) -> dict:
        logger.info("[Phase 5] Daily Report")
        try:
            report = {
                "cycle": cycle_result["cycle"],
                "started": cycle_result["started"],
                "phases_completed": len([p for p in cycle_result["phases"].values() if p.get("status") == "done"]),
                "phases_errored": len([p for p in cycle_result["phases"].values() if p.get("status") == "error"]),
                "total_phases": len(cycle_result["phases"]),
            }
            await self._notify_founder(
                f"SVOS Daily Report - Cycle {report['cycle']}: "
                f"{report['phases_completed']}/{report['total_phases']} phases completed"
            )
            return {"status": "done", "report": report}
        except Exception as e:
            logger.error(f"Report phase error: {e}")
            return {"status": "error", "error": str(e)}

    async def _notify_founder(self, message: str):
        logger.info(f"[FOUNDER NOTIFICATION] {message}")
        try:
            from tool_registry import build_registry

            registry = build_registry()
            registry.execute(
                "email",
                "CEO",
                "send",
                to="founder@svos.local",
                subject="SVOS System Notification",
                body=message,
            )
            registry.execute(
                "whatsapp",
                "CEO",
                "send",
                to="+966500000000",
                body=message,
            )
        except Exception as e:
            logger.warning(f"Founder notification failed: {e}")

    async def heartbeat(self) -> dict:
        self.last_heartbeat = datetime.utcnow()
        health = {"timestamp": self.last_heartbeat.isoformat(), "checks": {}}

        health["checks"]["scheduler"] = "ok" if self.is_running else "stopped"

        if self.last_cycle_time:
            age_hours = (datetime.utcnow() - self.last_cycle_time).total_seconds() / 3600
            stale = age_hours > (self.cycle_hours * 2)
            health["checks"]["cycle_freshness"] = {
                "status": "stale" if stale else "ok",
                "hours_since_last": round(age_hours, 1),
                "threshold": self.cycle_hours * 2,
            }
            if stale and self.is_running:
                logger.warning("SELF-HEALING: Cycle is stale. Triggering immediate cycle.")
                health["checks"]["cycle_freshness"]["action"] = "triggered_immediate_cycle"
                asyncio.create_task(self._run_cycle())
        else:
            health["checks"]["cycle_freshness"] = {"status": "no_cycles_yet"}

        health["checks"]["error_rate"] = {
            "consecutive_errors": self.consecutive_errors,
            "status": "ok" if self.consecutive_errors < 2 else "warning",
        }

        try:
            from agents import AGENT_REGISTRY

            health["checks"]["agents"] = {"status": "ok", "count": len(AGENT_REGISTRY)}
        except Exception as e:
            health["checks"]["agents"] = {"status": "error", "error": str(e)}

        health["overall"] = "healthy" if all(
            c.get("status", c) == "ok" for c in health["checks"].values() if isinstance(c, dict)
        ) else "degraded"

        return health


_scheduler = None


def get_scheduler() -> SVOSScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = SVOSScheduler(cycle_hours=12.0)
    return _scheduler

