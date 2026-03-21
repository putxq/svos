"""
SVOS Blueprint Engine — The Company Configurator.

Takes: industry, goal, business description
Produces: a full Business Blueprint that shapes every agent's behavior

The Blueprint is NOT a config file — it's the company's operating contract.
It defines how agents think, what workflows run, what KPIs matter.

Two modes:
1. AI-Generated: LLM builds a custom blueprint from business description
2. Seed-Enhanced: starts from curated industry template, then AI customizes

Storage: workspace/tenants/{customer_id}/blueprint.json
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("svos.blueprint")


# =====================================================================
# INDUSTRY SEED TEMPLATES — Top 5 domains (curated starting points)
# =====================================================================
INDUSTRY_SEEDS = {
    "restaurant": {
        "domain_context": (
            "This is a restaurant/F&B business. Key challenges: food cost management, "
            "staff retention, local competition, online reviews and reputation, delivery optimization. "
            "Success depends on: customer experience, consistent quality, local marketing, and repeat visits."
        ),
        "kpis": ["daily_covers", "average_ticket", "food_cost_percentage", "google_rating",
                 "repeat_customer_rate", "delivery_orders", "social_followers"],
        "content_strategy": {
            "platforms": ["instagram", "tiktok", "google_business"],
            "content_types": ["menu_highlights", "behind_scenes", "customer_reviews", "offers"],
            "frequency": "daily",
            "tone": "warm, visual, appetizing",
        },
        "workflows": {
            "weekly_content": {"active": True, "description": "3 social posts per week (menu + behind scenes + offer)"},
            "monthly_review": {"active": True, "description": "Review: covers, revenue, food cost, ratings"},
            "lead_nurturing": {"active": True, "description": "New contact → welcome offer within 24h"},
            "review_monitoring": {"active": True, "description": "Track and respond to online reviews"},
        },
        "challenges": ["food cost inflation", "staff turnover", "seasonal demand", "delivery competition"],
        "terminology": ["covers", "ticket size", "food cost", "table turnover", "footfall"],
    },

    "consulting": {
        "domain_context": (
            "This is a consulting/professional services business. Key challenges: lead generation, "
            "thought leadership, proposal win rate, utilization rate, client retention. "
            "Success depends on: expertise positioning, network building, and delivering measurable client outcomes."
        ),
        "kpis": ["leads_generated", "proposals_sent", "win_rate", "revenue_per_consultant",
                 "client_retention_rate", "linkedin_engagement", "speaking_invitations"],
        "content_strategy": {
            "platforms": ["linkedin", "blog", "email_newsletter"],
            "content_types": ["thought_leadership", "case_studies", "industry_insights", "frameworks"],
            "frequency": "2-3x per week",
            "tone": "authoritative, analytical, actionable",
        },
        "workflows": {
            "weekly_content": {"active": True, "description": "1 LinkedIn article + 3 short insights per week"},
            "monthly_review": {"active": True, "description": "Review: pipeline, win rate, utilization, revenue"},
            "lead_nurturing": {"active": True, "description": "New lead → case study + booking link within 24h"},
            "thought_leadership": {"active": True, "description": "Monthly industry analysis + trend report"},
        },
        "challenges": ["long sales cycles", "differentiating from competitors", "scaling without diluting quality"],
        "terminology": ["engagement", "deliverable", "utilization", "pipeline", "retainer", "SOW"],
    },

    "ecommerce": {
        "domain_context": (
            "This is an e-commerce/online retail business. Key challenges: customer acquisition cost, "
            "conversion rate optimization, inventory management, shipping logistics, cart abandonment. "
            "Success depends on: product-market fit, digital marketing efficiency, and customer lifetime value."
        ),
        "kpis": ["monthly_revenue", "conversion_rate", "cart_abandonment_rate", "customer_acquisition_cost",
                 "average_order_value", "return_rate", "customer_lifetime_value"],
        "content_strategy": {
            "platforms": ["instagram", "tiktok", "email", "google_ads"],
            "content_types": ["product_showcases", "customer_testimonials", "offers", "unboxing"],
            "frequency": "daily",
            "tone": "engaging, benefit-focused, urgent",
        },
        "workflows": {
            "weekly_content": {"active": True, "description": "Daily social + 2 email campaigns per week"},
            "monthly_review": {"active": True, "description": "Review: revenue, CAC, conversion, AOV"},
            "lead_nurturing": {"active": True, "description": "Abandoned cart → reminder email within 2h"},
            "product_launch": {"active": False, "description": "New product → teaser → launch → review cycle"},
        },
        "challenges": ["rising ad costs", "logistics delays", "price competition", "seasonal demand"],
        "terminology": ["AOV", "CAC", "LTV", "conversion rate", "SKU", "fulfillment"],
    },

    "technology": {
        "domain_context": (
            "This is a technology/SaaS business. Key challenges: product-market fit, user acquisition, "
            "churn reduction, feature prioritization, technical debt. "
            "Success depends on: solving a real pain point, fast iteration, and building a loyal user base."
        ),
        "kpis": ["MRR", "churn_rate", "user_signups", "activation_rate",
                 "NPS_score", "feature_adoption", "support_tickets"],
        "content_strategy": {
            "platforms": ["linkedin", "twitter", "blog", "product_hunt"],
            "content_types": ["product_updates", "tutorials", "industry_trends", "founder_insights"],
            "frequency": "3-4x per week",
            "tone": "innovative, clear, developer-friendly",
        },
        "workflows": {
            "weekly_content": {"active": True, "description": "2 blog posts + daily social + changelog"},
            "monthly_review": {"active": True, "description": "Review: MRR, churn, signups, NPS"},
            "lead_nurturing": {"active": True, "description": "Signup → onboarding email sequence (5 emails)"},
            "product_feedback": {"active": True, "description": "Collect and analyze user feedback weekly"},
        },
        "challenges": ["feature creep", "scaling infrastructure", "competitive pressure", "funding"],
        "terminology": ["MRR", "ARR", "churn", "activation", "retention", "sprint"],
    },

    "education": {
        "domain_context": (
            "This is an education/training business. Key challenges: student acquisition, "
            "course completion rates, content quality, instructor management, certification value. "
            "Success depends on: learning outcomes, reputation, and student satisfaction."
        ),
        "kpis": ["enrollments", "completion_rate", "student_satisfaction", "revenue_per_course",
                 "referral_rate", "instructor_rating", "certification_holders"],
        "content_strategy": {
            "platforms": ["youtube", "linkedin", "instagram", "email"],
            "content_types": ["educational_snippets", "student_stories", "free_workshops", "tips"],
            "frequency": "3x per week",
            "tone": "educational, encouraging, credible",
        },
        "workflows": {
            "weekly_content": {"active": True, "description": "2 educational posts + 1 student spotlight"},
            "monthly_review": {"active": True, "description": "Review: enrollments, completion, satisfaction"},
            "lead_nurturing": {"active": True, "description": "Inquiry → free resource + webinar invite"},
            "course_feedback": {"active": True, "description": "Post-course survey → improvement cycle"},
        },
        "challenges": ["content piracy", "student engagement", "market saturation", "accreditation"],
        "terminology": ["enrollment", "completion rate", "LMS", "cohort", "curriculum", "certification"],
    },
}

# Default for unknown industries
DEFAULT_SEED = {
    "domain_context": "This is a business focused on growth and operational efficiency.",
    "kpis": ["revenue", "leads", "customer_satisfaction", "content_produced", "conversion_rate"],
    "content_strategy": {
        "platforms": ["linkedin", "twitter", "email"],
        "content_types": ["insights", "updates", "thought_leadership"],
        "frequency": "2-3x per week",
        "tone": "professional",
    },
    "workflows": {
        "weekly_content": {"active": True, "description": "2-3 content pieces per week"},
        "monthly_review": {"active": True, "description": "Monthly performance review"},
        "lead_nurturing": {"active": True, "description": "New lead → follow-up within 24h"},
    },
    "challenges": ["market competition", "resource constraints", "growth sustainability"],
    "terminology": [],
}


# =====================================================================
# BLUEPRINT GENERATION
# =====================================================================

def _get_seed(industry: str) -> dict:
    """Get the closest industry seed template."""
    industry_lower = industry.lower().strip()

    # Direct match
    if industry_lower in INDUSTRY_SEEDS:
        return INDUSTRY_SEEDS[industry_lower]

    # Fuzzy matching
    aliases = {
        "food": "restaurant", "f&b": "restaurant", "مطعم": "restaurant",
        "مطاعم": "restaurant", "cafe": "restaurant", "كافيه": "restaurant",
        "استشارات": "consulting", "advisory": "consulting",
        "متجر": "ecommerce", "تجارة": "ecommerce", "store": "ecommerce",
        "retail": "ecommerce", "shop": "ecommerce",
        "saas": "technology", "tech": "technology", "تقنية": "technology",
        "software": "technology", "app": "technology",
        "تعليم": "education", "training": "education", "courses": "education",
        "تدريب": "education",
    }
    matched = aliases.get(industry_lower)
    if matched:
        return INDUSTRY_SEEDS[matched]

    return DEFAULT_SEED


async def generate_blueprint(
    industry: str,
    goal: str,
    company_name: str = "",
    company_description: str = "",
    mission: str = "",
    vision: str = "",
    values: list[str] = None,
    country: str = "Saudi Arabia",
    risk_appetite: str = "moderate",
    llm_provider=None,
) -> dict:
    """
    Generate a full Business Blueprint.
    Uses industry seed as base, then AI customizes for the specific business.
    """
    seed = _get_seed(industry)
    values = values or ["quality", "innovation", "trust"]

    # ── Build the blueprint structure ──
    blueprint = {
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "company_name": company_name,
        "industry": industry,
        "country": country,
        "goal": goal,
        "risk_appetite": risk_appetite,

        # Domain context — injected into every agent prompt
        "domain_context": seed["domain_context"],

        # Identity
        "identity": {
            "mission": mission,
            "vision": vision,
            "values": values,
        },

        # KPIs to track
        "kpis": seed["kpis"],

        # Content & marketing strategy
        "content_strategy": seed["content_strategy"],

        # Active workflows
        "workflows": seed["workflows"],

        # Domain challenges
        "challenges": seed["challenges"],

        # Domain terminology
        "terminology": seed.get("terminology", []),

        # Operations rhythm
        "rhythm": {
            "daily": True,
            "weekly_review_day": "sunday",  # Sunday for Saudi work week
            "monthly_review_day": 1,
        },
    }

    # ── AI Enhancement: customize blueprint for specific business ──
    if company_description and llm_provider:
        try:
            enhanced = await _ai_enhance_blueprint(
                blueprint, company_description, goal, llm_provider
            )
            if enhanced:
                blueprint.update(enhanced)
                blueprint["ai_enhanced"] = True
                logger.info(f"Blueprint AI-enhanced for {company_name}")
        except Exception as e:
            logger.warning(f"AI enhancement failed, using seed blueprint: {e}")
            blueprint["ai_enhanced"] = False
    else:
        blueprint["ai_enhanced"] = False

    return blueprint


async def _ai_enhance_blueprint(
    base_blueprint: dict,
    company_description: str,
    goal: str,
    llm_provider,
) -> dict | None:
    """Use AI to customize the blueprint for a specific business."""

    system = (
        "You are a business strategy AI. Given a company description and goal, "
        "generate a customized domain_context paragraph that will be injected into "
        "every AI agent's prompt. The context must be specific, actionable, and "
        "include: industry challenges specific to this business, key success factors, "
        "competitive landscape hints, and recommended focus areas.\n\n"
        "Also suggest 3 top priorities for the first month.\n\n"
        "Return ONLY valid JSON with these fields:\n"
        "- domain_context: string (2-3 paragraphs, specific to this business)\n"
        "- top_priorities: list of 3 strings\n"
        "- additional_kpis: list of 0-3 additional KPI names specific to this business\n"
        "Reply in the same language as the business description."
    )

    user = (
        f"Company: {base_blueprint.get('company_name', '')}\n"
        f"Industry: {base_blueprint.get('industry', '')}\n"
        f"Country: {base_blueprint.get('country', '')}\n"
        f"Description: {company_description}\n"
        f"Goal: {goal}\n"
        f"Current domain context: {base_blueprint.get('domain_context', '')}\n"
        f"Mission: {base_blueprint.get('identity', {}).get('mission', '')}\n"
    )

    schema = {
        "type": "object",
        "properties": {
            "domain_context": {"type": "string"},
            "top_priorities": {"type": "array", "items": {"type": "string"}},
            "additional_kpis": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["domain_context", "top_priorities"],
    }

    result = await llm_provider.complete_structured(system, user, schema)

    if result.get("_parse_error"):
        return None

    enhanced = {}
    if result.get("domain_context"):
        enhanced["domain_context"] = result["domain_context"]
    if result.get("top_priorities"):
        enhanced["top_priorities"] = result["top_priorities"][:3]
    if result.get("additional_kpis"):
        # Merge with existing KPIs
        existing = base_blueprint.get("kpis", [])
        enhanced["kpis"] = existing + [k for k in result["additional_kpis"] if k not in existing]

    return enhanced if enhanced else None


# =====================================================================
# STORAGE
# =====================================================================

def save_blueprint(customer_id: str, blueprint: dict) -> Path:
    """Save blueprint to tenant workspace."""
    from core.tenant import get_tenant_dir
    path = get_tenant_dir(customer_id) / "blueprint.json"
    path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Blueprint saved for {customer_id} at {path}")
    return path


def load_blueprint(customer_id: str) -> dict | None:
    """Load blueprint from tenant workspace."""
    from core.tenant import get_tenant_dir
    path = get_tenant_dir(customer_id) / "blueprint.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception as e:
        logger.warning(f"Failed to load blueprint for {customer_id}: {e}")
        return None


def apply_blueprint_to_state(customer_id: str, blueprint: dict):
    """
    Apply blueprint to Company State — populates identity and controls.
    Called once after blueprint generation (during onboarding).
    """
    from engines.company_state import get_company_state

    state = get_company_state(customer_id)

    # Update identity from blueprint
    state.update_identity(
        company_name=blueprint.get("company_name", ""),
        industry=blueprint.get("industry", "general"),
        goal=blueprint.get("goal", ""),
        mission=blueprint.get("identity", {}).get("mission", ""),
        vision=blueprint.get("identity", {}).get("vision", ""),
        values=blueprint.get("identity", {}).get("values", []),
        domain_context=blueprint.get("domain_context", ""),
    )

    # Set initial priorities if available
    priorities = blueprint.get("top_priorities", [])
    if priorities:
        state.update_status(top_priorities=priorities[:3])

    # Set initial phase
    state.update_status(phase="startup")

    logger.info(f"Blueprint applied to Company State for {customer_id}")


async def generate_and_save_blueprint(
    customer_id: str,
    industry: str,
    goal: str,
    company_name: str = "",
    company_description: str = "",
    mission: str = "",
    vision: str = "",
    values: list[str] = None,
    country: str = "Saudi Arabia",
    risk_appetite: str = "moderate",
    use_ai: bool = True,
) -> dict:
    """Full flow: generate → save → apply to state."""
    llm = None
    if use_ai:
        try:
            from core.llm_provider import LLMProvider
            llm = LLMProvider()
        except Exception as e:
            logger.warning(f"LLM not available for blueprint AI enhancement: {e}")

    blueprint = await generate_blueprint(
        industry=industry,
        goal=goal,
        company_name=company_name,
        company_description=company_description,
        mission=mission,
        vision=vision,
        values=values,
        country=country,
        risk_appetite=risk_appetite,
        llm_provider=llm,
    )

    save_blueprint(customer_id, blueprint)
    apply_blueprint_to_state(customer_id, blueprint)

    return blueprint
