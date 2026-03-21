"""
SVOS Quality Gate — Reviews outputs before they reach the external world.

Internal actions (analysis, reports) → pass through.
External actions (email, social, WhatsApp) → reviewed for quality.

Uses AI when available, rule-based fallback otherwise.
"""

import logging
import re
from typing import Any

logger = logging.getLogger("svos.quality_gate")

# Minimum quality standards
MIN_CONTENT_LENGTH = 50  # characters
MAX_CONTENT_LENGTH = 5000
BLOCKED_PATTERNS = [
    r"(?i)(test|placeholder|lorem ipsum|TODO|FIXME)",
    r"(?i)(fuck|shit|damn)",  # basic profanity
]


def check_quality(content: str, content_type: str = "general", language: str = "ar") -> dict:
    """
    Rule-based quality check. Fast, always works.
    Returns: {"passed": bool, "score": float, "issues": list}
    """
    issues = []
    score = 1.0

    if not content or not content.strip():
        return {"passed": False, "score": 0.0, "issues": ["Empty content"]}

    # Length check
    if len(content.strip()) < MIN_CONTENT_LENGTH:
        issues.append(f"Too short ({len(content)} chars, min {MIN_CONTENT_LENGTH})")
        score -= 0.3

    if len(content) > MAX_CONTENT_LENGTH:
        issues.append(f"Too long ({len(content)} chars, max {MAX_CONTENT_LENGTH})")
        score -= 0.1

    # Blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, content):
            issues.append(f"Contains blocked pattern: {pattern}")
            score -= 0.4

    # Repetition check (same sentence repeated)
    sentences = [s.strip() for s in content.split('.') if s.strip()]
    if len(sentences) > 2:
        unique = set(sentences)
        if len(unique) < len(sentences) * 0.5:
            issues.append("High repetition detected")
            score -= 0.3

    # Language consistency (basic)
    if language == "ar":
        arabic_ratio = len(re.findall(r'[\u0600-\u06FF]', content)) / max(len(content), 1)
        if arabic_ratio < 0.3 and len(content) > 100:
            issues.append("Expected Arabic content but found mostly non-Arabic text")
            score -= 0.2

    score = max(0.0, min(1.0, score))
    passed = score >= 0.6 and not any("blocked pattern" in i.lower() for i in issues)

    return {
        "passed": passed,
        "score": round(score, 2),
        "issues": issues,
        "content_length": len(content),
        "content_type": content_type,
    }


async def ai_quality_review(
    content: str,
    content_type: str = "general",
    company_context: str = "",
    llm_provider=None,
) -> dict:
    """
    AI-powered quality review. Deeper analysis.
    Falls back to rule-based if AI is unavailable.
    """
    # Always run rule-based first
    basic = check_quality(content, content_type)
    if not basic["passed"]:
        return basic  # Already failed basic checks

    if not llm_provider:
        return basic

    try:
        system = (
            "You are a quality reviewer for business content. "
            "Review the content and rate it 1-10 on: clarity, professionalism, relevance, accuracy. "
            "Return ONLY JSON: {\"score\": float 0-1, \"issues\": [list], \"suggestion\": str}\n"
            "Be strict. Business content must be professional and accurate."
        )
        user = f"Content type: {content_type}\n"
        if company_context:
            user += f"Company context: {company_context}\n"
        user += f"\nContent to review:\n{content[:2000]}"

        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "issues": {"type": "array", "items": {"type": "string"}},
                "suggestion": {"type": "string"},
            },
            "required": ["score", "issues"],
        }

        result = await llm_provider.complete_structured(system, user, schema)
        if result.get("_parse_error"):
            return basic

        ai_score = float(result.get("score", 0.7))
        if ai_score > 1.0:
            ai_score = ai_score / 10.0  # normalize 1-10 to 0-1

        # Combine basic and AI scores
        combined_score = (basic["score"] * 0.4) + (ai_score * 0.6)
        all_issues = basic["issues"] + result.get("issues", [])

        return {
            "passed": combined_score >= 0.6,
            "score": round(combined_score, 2),
            "basic_score": basic["score"],
            "ai_score": round(ai_score, 2),
            "issues": all_issues,
            "suggestion": result.get("suggestion", ""),
            "content_type": content_type,
            "content_length": len(content),
        }
    except Exception as e:
        logger.warning(f"AI quality review failed: {e}")
        return basic


def gate_action(tool: str, content: str = "", params: dict = None) -> dict:
    """
    Quick gate check for tool execution.
    Returns: {"allowed": bool, "reason": str}
    """
    # Safe tools always pass
    safe_tools = {"content", "market_scan", "analysis", "report"}
    if tool in safe_tools:
        return {"allowed": True, "reason": "safe_tool"}

    # External tools need content quality check
    if tool in {"email", "whatsapp", "social_post", "crm_outreach"}:
        body = content or (params or {}).get("body", "") or (params or {}).get("content", "")
        if body:
            quality = check_quality(body, content_type=tool)
            if not quality["passed"]:
                return {
                    "allowed": False,
                    "reason": f"Quality check failed: {', '.join(quality['issues'])}",
                    "quality": quality,
                }

    return {"allowed": True, "reason": "passed"}
