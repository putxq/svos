import os
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path

from core.llm_provider import LLMProvider
from core.json_parser import parse_llm_json

logger = logging.getLogger("svos.landing_page")


class LandingPageTool:
    """يولّد صفحات هبوط HTML حقيقية جاهزة للعرض"""

    name = "create_landing_page"
    description = "Generate and publish a real HTML landing page"

    def __init__(self, pages_dir: str = "workspace/pages"):
        self.pages_dir = Path(pages_dir).resolve()
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.llm = LLMProvider()
        self.pages_index_path = self.pages_dir / "_index.json"
        self._load_index()

    def _load_index(self):
        if self.pages_index_path.exists():
            try:
                self.pages_index = json.loads(self.pages_index_path.read_text("utf-8"))
            except Exception:
                self.pages_index = []
        else:
            self.pages_index = []

    def _save_index(self):
        self.pages_index_path.write_text(
            json.dumps(self.pages_index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def execute(
        self,
        company_name: str,
        headline: str,
        subheadline: str = "",
        benefits: list[str] = None,
        cta_text: str = "ابدأ الآن",
        color_scheme: str = "blue",
        lang: str = "ar",
    ) -> dict:
        """يولّد صفحة هبوط HTML كاملة."""
        page_id = uuid.uuid4().hex[:10]
        benefits = benefits or ["سرعة", "جودة", "احترافية"]

        system = (
            "You are an expert landing page designer. "
            "Generate a COMPLETE, beautiful, production-ready HTML landing page. "
            "The page must be a single self-contained HTML file with inline CSS. "
            "Use modern design: gradients, shadows, smooth fonts, responsive layout. "
            "Include: hero section, benefits section, CTA button, footer. "
            "Make it visually stunning but professional. "
            "Return ONLY the raw HTML code. No markdown fences. No explanation. "
            "Start with <!doctype html> and end with </html>."
        )

        direction = "rtl" if lang == "ar" else "ltr"
        user = (
            f"Create a landing page with these specs:\n"
            f"- Company: {company_name}\n"
            f"- Headline: {headline}\n"
            f"- Subheadline: {subheadline}\n"
            f"- Benefits: {', '.join(benefits)}\n"
            f"- CTA button text: {cta_text}\n"
            f"- Color scheme: {color_scheme}\n"
            f"- Language direction: {direction}\n"
            f"- Language: {'Arabic' if lang == 'ar' else 'English'}\n"
            f"Return ONLY the complete HTML. No markdown."
        )

        try:
            html = await self.llm.complete(system, user, temperature=0.7, max_tokens=4000)

            # Clean markdown fences if any
            html = html.strip()
            if html.startswith("```"):
                html = html.split("\n", 1)[-1]
            if html.endswith("```"):
                html = html.rsplit("```", 1)[0]
            html = html.strip()

            # Ensure it starts with valid HTML
            if not html.lower().startswith("<!doctype") and not html.lower().startswith("<html"):
                start = html.lower().find("<!doctype")
                if start == -1:
                    start = html.lower().find("<html")
                if start >= 0:
                    html = html[start:]

            # Save file
            filename = f"{page_id}.html"
            filepath = self.pages_dir / filename
            filepath.write_text(html, encoding="utf-8")

            # Update index
            page_entry = {
                "id": page_id,
                "company": company_name,
                "headline": headline,
                "filename": filename,
                "created_at": datetime.utcnow().isoformat(),
                "size_bytes": len(html.encode("utf-8")),
            }
            self.pages_index.append(page_entry)
            self._save_index()

            logger.info(f"Landing page created: {page_id} for {company_name}")

            return {
                "success": True,
                "page_id": page_id,
                "filename": filename,
                "url": f"/pages/{page_id}",
                "size_bytes": len(html.encode("utf-8")),
                "company": company_name,
            }

        except Exception as e:
            logger.error(f"Landing page generation failed: {e}")
            return {"success": False, "error": str(e)}

    def get_page_path(self, page_id: str) -> Path | None:
        """يرجع مسار ملف الصفحة."""
        filepath = self.pages_dir / f"{page_id}.html"
        return filepath if filepath.exists() else None

    def list_pages(self) -> list[dict]:
        """قائمة كل الصفحات المولّدة."""
        self._load_index()
        return self.pages_index
