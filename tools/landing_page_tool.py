import os
import logging
import uuid
from datetime import datetime

logger = logging.getLogger("svos.tools.landing_page")

PAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace", "pages")


class LandingPageTool:
    """Generate real HTML landing pages for campaigns."""

    name = "landing_page"
    description = "Generate and save HTML landing pages for marketing campaigns"
    allowed_roles = ["CMO", "CEO", "CTO"]

    def __init__(self):
        os.makedirs(PAGES_DIR, exist_ok=True)
        logger.info(f"LandingPageTool ready | pages dir: {PAGES_DIR}")

    def generate(
        self,
        title: str,
        headline: str,
        sub_headline: str = "",
        cta_text: str = "Get Started",
        cta_link: str = "#",
        features: list[str] = None,
        color_primary: str = "#2563EB",
        color_bg: str = "#F9FAFB",
        logo_url: str = "",
        lang: str = "ar",
    ) -> dict:
        """
        Generate an HTML landing page and save it.
        Returns dict with file path and preview info.
        """
        page_id = uuid.uuid4().hex[:8]
        filename = f"page_{page_id}.html"
        filepath = os.path.join(PAGES_DIR, filename)
        direction = "rtl" if lang == "ar" else "ltr"

        features_html = ""
        if features:
            items = "".join(f'<div class="feature"><h3>{f}</h3></div>' for f in features)
            features_html = f'<section class="features">{items}</section>'

        logo_html = f'<img src="{logo_url}" alt="logo" class="logo">' if logo_url else ""

        html = f"""<!DOCTYPE html>
<html lang=\"{lang}\" dir=\"{direction}\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>{title}</title>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{font-family:'Segoe UI',Tahoma,sans-serif;background:{color_bg};color:#1a1a2e;direction:{direction}}}
    .hero{{text-align:center;padding:80px 20px;background:linear-gradient(135deg,{color_primary},#1e40af);color:#fff}}
    .hero h1{{font-size:2.8rem;margin-bottom:16px}}
    .hero p{{font-size:1.3rem;opacity:0.9;margin-bottom:32px}}
    .cta{{display:inline-block;padding:16px 48px;background:#fff;color:{color_primary};border-radius:8px;font-size:1.1rem;font-weight:700;text-decoration:none;transition:transform 0.2s}}
    .cta:hover{{transform:scale(1.05)}}
    .features{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:24px;padding:60px 40px;max-width:1000px;margin:0 auto}}
    .feature{{background:#fff;padding:32px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06)}}
    .feature h3{{color:{color_primary};margin-bottom:8px}}
    .logo{{max-height:48px;margin-bottom:24px}}
    footer{{text-align:center;padding:32px;color:#888;font-size:0.85rem}}
  </style>
</head>
<body>
  <div class=\"hero\">
    {logo_html}
    <h1>{headline}</h1>
    <p>{sub_headline}</p>
    <a href=\"{cta_link}\" class=\"cta\">{cta_text}</a>
  </div>
  {features_html}
  <footer>Powered by SVOS &mdash; {datetime.now().strftime('%Y-%m-%d')}</footer>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Landing page created: {filepath}")
        return {
            "status": "created",
            "page_id": page_id,
            "filepath": filepath,
            "filename": filename,
            "title": title,
        }
