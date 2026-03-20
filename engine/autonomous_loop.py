import asyncio
import json
from datetime import datetime

from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json
from core.logger import log_decision
from sovereign_kernel.confidence_engine import ConfidenceEngine
from sovereign_kernel.trust_safety import TrustSafetyKernel


class AutonomousLoop:
    """
    الحلقة المستقلة — تشغّل الشركة الرقمية 24/7 بدون تدخل بشري.

    الدورة اليومية (مثل دورة تسلا Autopilot):
    1. الصحيان — إحاطة صباحية
    2. الرصد — مسح السوق والمنافسين
    3. التحليل — تقييم الفرص والمخاطر
    4. القرار — ماذا نفعل اليوم
    5. التنفيذ — تشغيل المهام
    6. التقرير — ملخص اليوم
    7. التعلم — ما نجح وما فشل
    """

    def __init__(self):
        self.llm = LLMProvider()
        self.confidence = ConfidenceEngine()
        self.safety = TrustSafetyKernel()
        self.cycle_count = 0
        self.is_running = False
        self.daily_log = []

    async def morning_briefing(self, company_profile: dict) -> dict:
        """الخطوة 1: إحاطة صباحية — ما الوضع الحالي؟"""
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
        """الخطوة 2: نبضة السوق — ماذا يحدث الآن؟"""
        from engines.gravity_engine import GravityEngine

        gravity = GravityEngine()
        description = company_profile.get('description', 'digital services')
        return await gravity.find_demand_gravity(description)

    async def daily_decision(self, briefing: dict, market: dict, company_profile: dict) -> dict:
        """الخطوة 3: قرار اليوم — ماذا نفعل؟"""
        system_prompt = (
            "You are the CEO making today's key decision. "
            "Based on the morning briefing and market data, decide ONE key action for today. "
            "Be specific and actionable. Return ONLY valid JSON."
        )

        user_msg = (
            f"Morning briefing: {json.dumps(briefing, ensure_ascii=False)[:500]}\n"
            f"Market opportunities: {len(market.get('opportunities', []))}\n"
            f"Company goal: {company_profile.get('goal', '')}\n\n"
            "Return JSON: {\"action\": str, \"assigned_to\": str, \"priority\": str, "
            "\"expected_outcome\": str, \"confidence\": float}"
        )

        raw = await self.llm.complete(system_prompt, user_msg, max_tokens=1000)
        return parse_llm_json(raw)

    async def execute_action(self, decision: dict) -> dict:
        """الخطوة 4: تنفيذ القرار"""
        # فحص أمان أولاً
        safety_check = self.safety.evaluate_action(
            action=decision.get("action", ""),
            agent_name=decision.get("assigned_to", "CEO"),
            action_type="general",
        )

        if not safety_check.safe:
            return {"executed": False, "reason": "blocked_by_safety", "flags": safety_check.flags}

        system_prompt = (
            f"You are the {decision.get('assigned_to', 'CEO')}. "
            "Execute this action and report what was done. "
            "Be specific about results. Return ONLY valid JSON."
        )

        user_msg = (
            f"Action: {decision.get('action', '')}\n"
            f"Expected outcome: {decision.get('expected_outcome', '')}\n\n"
            "Return JSON: {\"executed\": true, \"result\": str, \"next_step\": str, \"success\": bool}"
        )

        raw = await self.llm.complete(system_prompt, user_msg, max_tokens=1000)
        return parse_llm_json(raw)

    async def daily_report(self, briefing, market, decision, execution) -> dict:
        """الخطوة 5: تقرير اليوم"""
        return {
            "cycle": self.cycle_count,
            "timestamp": datetime.now().isoformat(),
            "briefing_priorities": briefing.get("priorities", []),
            "market_opportunities": len(market.get("opportunities", [])),
            "decision": decision.get("action", ""),
            "assigned_to": decision.get("assigned_to", ""),
            "executed": execution.get("executed", False),
            "result": execution.get("result", ""),
            "success": execution.get("success", False),
        }

    async def run_one_cycle(self, company_profile: dict) -> dict:
        """تشغيل دورة واحدة كاملة"""
        self.cycle_count += 1

        print(f"\n{'='*50}")
        print(f" SVOS Autonomous Cycle #{self.cycle_count}")
        print(f" {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*50}")

        print("\n [1/5] Morning briefing...", end=" ", flush=True)
        briefing = await self.morning_briefing(company_profile)
        print(f"OK - Focus: {briefing.get('focus_today', '?')[:60]}")

        print(" [2/5] Market pulse...", end=" ", flush=True)
        market = await self.market_pulse(company_profile)
        print(f"OK - {len(market.get('opportunities', []))} opportunities")

        print(" [3/5] Daily decision...", end=" ", flush=True)
        decision = await self.daily_decision(briefing, market, company_profile)
        print(f"OK - {decision.get('action', '?')[:60]}")

        print(" [4/5] Executing...", end=" ", flush=True)
        execution = await self.execute_action(decision)
        print(f"OK - Success: {execution.get('success', '?')}")

        print(" [5/5] Report...", end=" ", flush=True)
        report = await self.daily_report(briefing, market, decision, execution)
        self.daily_log.append(report)
        print("OK")

        # حفظ التقرير
        import os

        os.makedirs("workspace/daily_reports", exist_ok=True)
        report_path = f"workspace/daily_reports/cycle_{self.cycle_count}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        log_decision("AutonomousLoop", "run_one_cycle", 100.0 if report.get("success") else 50.0, "success")

        print(f"\n Report saved: {report_path}")
        return report

    async def run_continuous(self, company_profile: dict, cycles: int = 3, interval_seconds: int = 60):
        """تشغيل مستمر — عدة دورات"""
        self.is_running = True

        for i in range(cycles):
            if not self.is_running:
                print(" Loop stopped by user.")
                break

            report = await self.run_one_cycle(company_profile)

            if i < cycles - 1:
                print(f"\n Next cycle in {interval_seconds}s... (Ctrl+C to stop)")
                await asyncio.sleep(interval_seconds)

        print(f"\n Completed {self.cycle_count} cycles.")

    def stop(self):
        self.is_running = False
