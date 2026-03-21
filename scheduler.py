import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

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

        # ── Load Company State (the company's living memory) ──
        try:
            from engines.company_state import get_company_state
            company_state = get_company_state()
            state_context = company_state.get_agent_context()
            logger.info(f"Company State loaded ({len(state_context)} chars context)")
        except Exception as e:
            logger.warning(f"Company State load failed (continuing without): {e}")
            company_state = None
            state_context = ""

        # Store context for phases to use
        self._current_state_context = state_context
        self._company_state = company_state

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

        # ── Generate Cycle Summary (dual layer) ──
        try:
            from engines.cycle_summary import generate_full_summary
            summary = await generate_full_summary(
                cycle_result,
                company_state.state if company_state else None,
            )
            cycle_result["summary"] = summary

            # ── Update Company State with cycle results ──
            if company_state:
                narrative = summary.get("narrative", "")
                op = summary.get("operational", {})
                company_state.add_cycle_snapshot(
                    cycle=self.current_cycle,
                    summary=narrative[:300] if narrative else str(op.get("highlights", ""))[:300],
                    actions_taken=op.get("actions", {}).get("total", 0),
                    decisions_made=1 if cycle_result["phases"].get("decision", {}).get("status") == "done" else 0,
                )
                company_state.update_status(
                    health=op.get("health", "unknown"),
                )
                logger.info(f"Company State updated after cycle {self.current_cycle}")
        except Exception as e:
            logger.warning(f"Cycle summary generation failed: {e}")

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

            # Inject Company State context into briefing
            state_context = getattr(self, "_current_state_context", "")
            base_context = (
                "You are the CEO of a sovereign AI company running on SVOS. "
                "The system has 9 C-suite agents, 4 execution tools, and runs autonomous cycles."
            )
            if state_context:
                full_context = f"{base_context}\n\n=== COMPANY STATE ===\n{state_context}"
            else:
                full_context = base_context

            ceo = ceo_cls()
            result = await ceo.think(
                task="Generate a morning briefing. "
                "Review the company state, summarize what happened recently, "
                "identify pending priorities, and recommend focus areas for today. "
                "Be specific based on the company context provided.",
                context=full_context,
            )
            return {"status": "done", "summary": str(result)[:500], "version": settings.app_version}
        except Exception as e:
            logger.error(f"Briefing phase error: {e}")
            return {"status": "error", "error": str(e)}

    async def _phase_market_scan(self) -> dict:
        logger.info("[Phase 2] Market Scan")
        try:
            from engines.gravity_engine import GravityEngine

            # Use blueprint context for domain-specific scan
            scan_query = "Saudi Arabia digital transformation SME automation AI solutions 2026"
            company_state = getattr(self, "_company_state", None)
            if company_state:
                identity = company_state.state.get("identity", {})
                industry = identity.get("industry", "")
                goal = identity.get("goal", "")
                company = identity.get("company_name", "")
                if industry and industry != "general":
                    scan_query = f"{industry} market trends opportunities {goal} Saudi Arabia 2026"
                    if company:
                        scan_query = f"{company} {scan_query}"

            engine = GravityEngine()
            result = await engine.find_demand_gravity(scan_query)
            return {"status": "done", "opportunities": str(result)[:500], "query": scan_query}
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

            # Add company context to decision
            state_context = getattr(self, "_current_state_context", "")
            if state_context:
                context["company_state"] = state_context

            decision_prompt = (
                "Based on today's briefing and market scan, "
                "what is the single most impactful action to take today? "
                "Be specific to the company's industry and current priorities."
            )
            result = await engine.should_proceed(decision_prompt, context)
            decision_text = str(result)[:500]

            # Record decision in Company State
            company_state = getattr(self, "_company_state", None)
            if company_state:
                company_state.record_decision(
                    decision=decision_text[:300],
                    agent="CEO",
                    expected_outcome="Improve performance based on today's analysis",
                )

            return {"status": "done", "decision": decision_text}
        except Exception as e:
            logger.error(f"Decision phase error: {e}")
            return {"status": "error", "error": str(e)}

    async def _phase_execution(self, previous_phases: dict) -> dict:
        logger.info("[Phase 4] Execution")
        try:
            decision = previous_phases.get("decision", {})
            decision_text = str(decision.get("decision", ""))
            actions_taken = []

            # ── Auto-execute safe actions based on decision keywords ──
            # Content generation (safe, no external side effects)
            if any(kw in decision_text.lower() for kw in ["content", "marketing", "blog", "social", "محتوى", "تسويق"]):
                try:
                    from engines.digital_factory import DigitalFactory
                    factory = DigitalFactory()
                    result = await factory.produce_content(
                        topic="AI-powered business automation in Saudi Arabia",
                        business="SVOS Digital Company",
                        platforms=["linkedin", "twitter"],
                        tone="professional",
                        language="ar",
                    )
                    actions_taken.append({
                        "action": "content_produced",
                        "status": "done",
                        "platforms": ["linkedin", "twitter"],
                        "summary": str(result)[:300],
                    })
                except Exception as e:
                    actions_taken.append({"action": "content_production", "status": "error", "error": str(e)})

            # Market scan (safe, read-only)
            if any(kw in decision_text.lower() for kw in ["market", "opportunity", "scan", "سوق", "فرص"]):
                try:
                    from engines.gravity_engine import GravityEngine
                    engine = GravityEngine()
                    result = await engine.find_demand_gravity(
                        "SME digital transformation Saudi Arabia 2026"
                    )
                    actions_taken.append({
                        "action": "market_scan_deep",
                        "status": "done",
                        "summary": str(result)[:300],
                    })
                except Exception as e:
                    actions_taken.append({"action": "market_scan_deep", "status": "error", "error": str(e)})

            # Landing page generation (safe, generates file only)
            if any(kw in decision_text.lower() for kw in ["landing", "page", "website", "صفحة", "موقع"]):
                try:
                    from tools.landing_page_tool import LandingPageTool
                    lp_tool = LandingPageTool()
                    result = await lp_tool.execute(
                        company_name="SVOS Auto-Generated",
                        headline="Transform Your Business with AI",
                        subheadline="Autonomous digital operations for Saudi SMEs",
                        benefits=["Lower cost than hiring", "24/7 operations", "AI-powered decisions"],
                        cta_text="Start Free",
                    )
                    actions_taken.append({
                        "action": "landing_page_generated",
                        "status": "done",
                        "summary": str(result)[:300],
                    })
                except Exception as e:
                    actions_taken.append({"action": "landing_page", "status": "error", "error": str(e)})

            # Daily report generation (always)
            try:
                briefing = previous_phases.get("briefing", {}).get("summary", "No briefing")
                market = previous_phases.get("market_scan", {}).get("opportunities", "No scan")
                report_content = (
                    f"SVOS Daily Execution Report - Cycle {self.current_cycle}\n"
                    f"Briefing: {briefing[:200]}\n"
                    f"Market: {market[:200]}\n"
                    f"Decision: {decision_text[:200]}\n"
                    f"Actions: {len(actions_taken)} executed\n"
                )
                report_dir = Path("workspace/daily_reports")
                report_dir.mkdir(parents=True, exist_ok=True)
                report_file = report_dir / f"cycle_{self.current_cycle}.txt"
                report_file.write_text(report_content, encoding="utf-8")
                actions_taken.append({
                    "action": "daily_report_saved",
                    "status": "done",
                    "file": str(report_file),
                })
            except Exception as e:
                actions_taken.append({"action": "daily_report", "status": "error", "error": str(e)})

            return {
                "status": "done",
                "actions_taken": actions_taken,
                "total_actions": len(actions_taken),
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

