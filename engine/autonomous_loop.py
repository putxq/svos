import asyncio
import json
import os
from datetime import datetime

from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json, extract_field
from core.logger import log_decision
from sovereign_kernel.confidence_engine import ConfidenceEngine
from sovereign_kernel.trust_safety import TrustSafetyKernel


class AutonomousLoop:
    """
    الحلقة المستقلة — تشغّل الشركة الرقمية 24/7.
    الآن مع تنفيذ حقيقي: إيميل، صفحات هبوط، بحث، ملفات.
    """

    def __init__(self):
        self.llm = LLMProvider()
        self.confidence = ConfidenceEngine()
        self.safety = TrustSafetyKernel()
        self.cycle_count = 0
        self.is_running = False
        self.daily_log = []

    async def morning_briefing(self, company_profile: dict) -> dict:
        system_prompt = (
            "You are a chief of staff preparing a morning briefing for the CEO. "
            "Be concise and actionable. Respond in the same language as the company description. "
            "Return ONLY valid JSON."
        )

        user_msg = (
            f"Company: {company_profile.get('description', '')}\n"
            f"Goal: {company_profile.get('goal', '')}\n"
            f"Budget: {company_profile.get('budget', '')}\n"
            f"Day number: {self.cycle_count + 1}\n\n"
            "Return JSON: {\"priorities\": [str], \"risks\": [str], \"opportunities\": [str], \"focus_today\": str}"
        )

        raw = await self.llm.complete(system_prompt, user_msg, max_tokens=1000)
        return parse_llm_json(raw)

    async def market_pulse(self, company_profile: dict) -> dict:
        from engines.gravity_engine import GravityEngine

        gravity = GravityEngine()
        description = company_profile.get('description', 'digital services')
        return await gravity.find_demand_gravity(description)

    async def daily_decision(self, briefing: dict, market: dict, company_profile: dict) -> dict:
        system_prompt = (
            "You are the CEO making today's key decision. "
            "Based on the briefing and market data, decide ONE key action. "
            "IMPORTANT: You have these REAL tools available:\n"
            "1. send_email — send a real email to someone\n"
            "2. create_landing_page — create a real HTML landing page\n"
            "3. web_search — search the internet for information\n"
            "4. compile_idea — turn an idea into a full execution package (PRD + page + email)\n"
            "5. write_report — write and save a strategy/analysis report\n\n"
            "Choose an action that uses one of these tools. Be specific.\n"
            "Return ONLY valid JSON."
        )

        user_msg = (
            f"Morning briefing: {json.dumps(briefing, ensure_ascii=False)[:500]}\n"
            f"Market opportunities: {json.dumps(market.get('opportunities', [])[:2], ensure_ascii=False)[:500]}\n"
            f"Competition: {market.get('competition_level', 'unknown')}\n"
            f"Company goal: {company_profile.get('goal', '')}\n"
            f"Company: {company_profile.get('description', '')}\n\n"
            "Choose ONE action from the available tools and return:\n"
            "{\"action\": str, \"tool\": str, \"tool_params\": {}, "
            "\"assigned_to\": str, \"priority\": str, \"expected_outcome\": str, \"confidence\": float}\n\n"
            "Example tools usage:\n"
            "- {\"tool\": \"create_landing_page\", \"tool_params\": {\"company_name\": \"X\", \"headline\": \"Y\", \"benefits\": [\"a\",\"b\",\"c\"]}}\n"
            "- {\"tool\": \"web_search\", \"tool_params\": {\"query\": \"competitors in market X\"}}\n"
            "- {\"tool\": \"write_report\", \"tool_params\": {\"title\": \"Market Analysis\", \"content\": \"...\"}}\n"
            "- {\"tool\": \"compile_idea\", \"tool_params\": {\"idea\": \"...\"}}\n"
        )

        raw = await self.llm.complete(system_prompt, user_msg, max_tokens=1500)
        return parse_llm_json(raw)

    async def execute_action(self, decision: dict, company_profile: dict) -> dict:
        """التنفيذ الحقيقي — يستدعي أدوات فعلية بناءً على القرار."""
        # Safety check first
        safety_check = self.safety.evaluate_action(
            action=decision.get("action", ""),
            agent_name=decision.get("assigned_to", "CEO"),
            action_type="general",
        )
        if not safety_check.safe:
            return {"executed": False, "result": "blocked_by_safety", "success": False, "tool": "none"}

        tool = decision.get("tool", "").lower().strip()
        params = decision.get("tool_params", {})

        # ---- REAL TOOL EXECUTION ----
        if tool == "create_landing_page":
            from tools.landing_page_tool import LandingPageTool

            lp_tool = LandingPageTool()
            result = await lp_tool.execute(
                company_name=params.get("company_name", company_profile.get("description", "SVOS")),
                headline=params.get("headline", decision.get("action", "Welcome")),
                subheadline=params.get("subheadline", ""),
                benefits=params.get("benefits", ["Speed", "Quality", "Results"]),
                cta_text=params.get("cta_text", "Get Started"),
                lang=params.get("lang", "en"),
            )
            return {
                "executed": True,
                "tool": "create_landing_page",
                "result": f"Landing page created: {result.get('url', '—')}",
                "success": result.get("success", False),
                "details": result,
            }

        elif tool == "web_search":
            from tools.web_search import WebSearchTool

            search = WebSearchTool()
            query = params.get("query", decision.get("action", "market research"))
            result = await search.execute(query, max_results=params.get("max_results", 5))
            return {
                "executed": True,
                "tool": "web_search",
                "result": f"Found {result.get('total', 0)} results for: {query}",
                "success": result.get("total", 0) > 0,
                "details": {
                    "query": query,
                    "total": result.get("total", 0),
                    "top_results": [
                        {"title": r.get("title", ""), "url": r.get("url", "")}
                        for r in result.get("results", [])[:3]
                    ],
                },
            }

        elif tool == "send_email":
            from tools.email_tool import EmailTool

            email_tool = EmailTool()
            result = await email_tool.execute(
                to=params.get("to", ""),
                subject=params.get("subject", "SVOS Update"),
                body=params.get("body", ""),
                html=params.get("html"),
            )
            return {
                "executed": True,
                "tool": "send_email",
                "result": f"Email {'sent' if result.get('sent') else 'failed'}: {result.get('to', '—')}",
                "success": result.get("sent", False),
                "details": result,
            }

        elif tool == "compile_idea":
            from engines.reality_compiler import RealityCompiler

            compiler = RealityCompiler()
            idea = params.get("idea", decision.get("action", ""))
            result = await compiler.compile(idea)
            # Also save it
            save_dir = await compiler.compile_and_save(idea)
            return {
                "executed": True,
                "tool": "compile_idea",
                "result": f"Idea compiled: {result.get('idea_summary', idea)[:100]}",
                "success": True,
                "details": {
                    "summary": result.get("idea_summary", ""),
                    "prd_name": result.get("prd", {}).get("product_name", ""),
                    "saved_to": save_dir,
                },
            }

        elif tool == "write_report":
            title = params.get("title", "SVOS Report")
            content = params.get("content", "")

            if not content:
                # Ask LLM to generate report content
                system = "Write a professional business report. Be detailed and actionable. Return plain text."
                user = f"Write a report titled: {title}\nContext: {json.dumps(params, ensure_ascii=False)}"
                content = await self.llm.complete(system, user, max_tokens=2000)

            os.makedirs("workspace/reports", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            safe_title = "".join(c if c.isalnum() or c in "_ -" else "_" for c in title)[:50]
            filepath = f"workspace/reports/{timestamp}_{safe_title}.md"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"*Generated by SVOS on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
                f.write(content)

            return {
                "executed": True,
                "tool": "write_report",
                "result": f"Report saved: {filepath}",
                "success": True,
                "details": {"filepath": filepath, "title": title, "size": len(content)},
            }

        else:
            # Fallback: unknown tool — try to do something useful anyway
            # Do a web search based on the action
            from tools.web_search import WebSearchTool

            search = WebSearchTool()
            query = decision.get("action", "business opportunity")[:100]
            result = await search.execute(query, max_results=3)
            return {
                "executed": True,
                "tool": "web_search_fallback",
                "result": f"No specific tool matched '{tool}'. Did web search instead: {result.get('total', 0)} results.",
                "success": result.get("total", 0) > 0,
                "details": {
                    "original_tool": tool,
                    "fallback_query": query,
                    "results_count": result.get("total", 0),
                },
            }

    async def daily_report(self, briefing, market, decision, execution) -> dict:
        return {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "briefing_priorities": briefing.get("priorities", []),
            "market_opportunities": len(market.get("opportunities", [])),
            "decision": decision.get("action", ""),
            "tool_used": execution.get("tool", "none"),
            "assigned_to": decision.get("assigned_to", ""),
            "executed": execution.get("executed", False),
            "result": execution.get("result", ""),
            "success": execution.get("success", False),
            "details": execution.get("details", {}),
        }

    async def run_one_cycle(self, company_profile: dict) -> dict:
        self.cycle_count += 1

        print(f"\n{'='*50}", flush=True)
        print(f" SVOS Autonomous Cycle #{self.cycle_count}")
        print(f" {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*50}")

        print("\n [1/5] Morning briefing...", end=" ", flush=True)
        briefing = await self.morning_briefing(company_profile)
        print(f"OK — Focus: {briefing.get('focus_today', '?')[:60]}")

        print(" [2/5] Market pulse...", end=" ", flush=True)
        market = await self.market_pulse(company_profile)
        print(f"OK — {len(market.get('opportunities', []))} opportunities")

        print(" [3/5] Daily decision...", end=" ", flush=True)
        decision = await self.daily_decision(briefing, market, company_profile)
        tool = decision.get("tool", "?")
        print(f"OK — Tool: {tool} | {decision.get('action', '?')[:50]}")

        print(" [4/5] Executing...", end=" ", flush=True)
        execution = await self.execute_action(decision, company_profile)
        status = "[OK]" if execution.get('success') else "[!!]"
        print(f"{status} -- {execution.get('result', '?')[:60]}")

        print(" [5/5] Report...", end=" ", flush=True)
        report = await self.daily_report(briefing, market, decision, execution)
        self.daily_log.append(report)
        print("OK")

        os.makedirs("workspace/daily_reports", exist_ok=True)
        report_path = f"workspace/daily_reports/cycle_{self.cycle_count}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        success_score = 100.0 if report.get("success") else 50.0
        log_decision("AutonomousLoop", "run_one_cycle", success_score, "success")

        print(f"\n Report saved: {report_path}")
        print(f" Tool used: {execution.get('tool', 'none')}")
        print(f" Result: {execution.get('result', '—')[:80]}")

        return report

    async def run_continuous(self, company_profile: dict, cycles: int = 3, interval_seconds: int = 60):
        self.is_running = True

        for i in range(cycles):
            if not self.is_running:
                print(" Loop stopped by user.")
                break

            await self.run_one_cycle(company_profile)

            if i < cycles - 1:
                print(f"\n Next cycle in {interval_seconds}s...")
                await asyncio.sleep(interval_seconds)

        print(f"\n Completed {self.cycle_count} cycles.")

    def stop(self):
        self.is_running = False
