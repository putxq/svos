import json
from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json, extract_field


class RealityCompiler:
    """مُجمّع الواقع — يحوّل فكرة إلى أصول تنفيذية حقيقية"""

    def __init__(self):
        self.llm = LLMProvider()

    async def compile(self, idea: str, context: dict = None) -> dict:
        """
        يحوّل فكرة واحدة إلى حزمة أصول جاهزة للتنفيذ
        """
        if context is None:
            context = {}

        system_prompt = (
            "You are a startup execution expert. "
            "Given a business idea, produce a complete execution package. "
            "Be extremely specific and actionable - no fluff. "
            "Everything you write should be copy-paste ready. "
            "Respond in the same language as the idea. "
            "Return ONLY valid JSON, no markdown fences."
        )

        user_message = f"""Business idea: {idea}
Context: {json.dumps(context, ensure_ascii=False)}

Return JSON with ALL these keys:
{{
  "idea_summary": "one line summary",
  "prd": {{
    "product_name": "...",
    "problem": "what problem does this solve",
    "solution": "how we solve it",
    "target_customer": "who pays",
    "value_proposition": "why they pay us not competitors",
    "mvp_features": ["feature1", "feature2", "feature3"],
    "success_metrics": ["metric1", "metric2"]
  }},
  "landing_page": {{
    "headline": "main headline for the website",
    "subheadline": "supporting text",
    "cta_button": "call to action text",
    "benefits": ["benefit1", "benefit2", "benefit3"],
    "social_proof": "what to show as credibility",
    "pricing_hint": "how to present pricing"
  }},
  "sales_email": {{
    "subject": "email subject line",
    "body": "complete cold email body ready to send",
    "follow_up": "follow up email if no response"
  }},
  "launch_plan": {{
    "week_1": ["action1", "action2", "action3"],
    "week_2": ["action1", "action2"],
    "week_3": ["action1", "action2"],
    "week_4": ["action1", "action2"]
  }},
  "budget_estimate": {{
    "setup_cost": "...",
    "monthly_cost": "...",
    "break_even": "when"
  }},
  "risks": ["risk1", "risk2", "risk3"],
  "competitive_edge": "why we win"
}}"""

        raw = await self.llm.complete(system_prompt, user_message, temperature=0.7, max_tokens=4000)
        parsed = parse_llm_json(raw)

        return {
            "idea": idea,
            "prd": extract_field(parsed, "prd", default={}),
            "landing_page": extract_field(parsed, "landing_page", default={}),
            "sales_email": extract_field(parsed, "sales_email", default={}),
            "launch_plan": extract_field(parsed, "launch_plan", default={}),
            "budget_estimate": extract_field(parsed, "budget_estimate", default={}),
            "risks": extract_field(parsed, "risks", default=[]),
            "competitive_edge": extract_field(parsed, "competitive_edge", default=""),
            "idea_summary": extract_field(parsed, "idea_summary", default=idea),
        }

    async def compile_and_save(self, idea: str, output_dir: str = "workspace/compiled", context: dict = None) -> str:
        """يجمّع ويحفظ كل الأصول كملفات"""
        import os

        result = await self.compile(idea, context)
        os.makedirs(output_dir, exist_ok=True)

        with open(f"{output_dir}/full_package.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        if result.get("prd"):
            with open(f"{output_dir}/prd.md", "w", encoding="utf-8") as f:
                prd = result["prd"]
                f.write(f"# {prd.get('product_name', 'Product')}\n\n")
                f.write(f"## Problem\n{prd.get('problem', '')}\n\n")
                f.write(f"## Solution\n{prd.get('solution', '')}\n\n")
                f.write(f"## Target Customer\n{prd.get('target_customer', '')}\n\n")
                f.write("## MVP Features\n")
                for feat in prd.get("mvp_features", []):
                    f.write(f"- {feat}\n")

        if result.get("sales_email"):
            with open(f"{output_dir}/sales_email.md", "w", encoding="utf-8") as f:
                email = result["sales_email"]
                f.write(f"Subject: {email.get('subject', '')}\n\n")
                f.write(f"{email.get('body', '')}\n\n---\n\n")
                f.write(f"Follow-up:\n{email.get('follow_up', '')}\n")

        return output_dir

