import sys
import os
import io
# فرض UTF-8 على Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    os.system("chcp 65001 >nul 2>&1")

import asyncio
import json
import locale
import re
from datetime import datetime, UTC
from pathlib import Path

from core.llm_provider import LLMProvider
from sovereign_kernel.smart_constitution import SmartConstitution


def detect_language():
    """يكشف لغة نظام المستخدم ويختار اللغة المناسبة"""
    try:
        system_lang = locale.getdefaultlocale()[0] or "en"
    except Exception:
        system_lang = "en"

    if system_lang.startswith("ar"):
        return "ar"
    elif system_lang.startswith("fr"):
        return "fr"
    elif system_lang.startswith("es"):
        return "es"
    elif system_lang.startswith("de"):
        return "de"
    elif system_lang.startswith("zh"):
        return "zh"
    elif system_lang.startswith("ja"):
        return "ja"
    elif system_lang.startswith("ko"):
        return "ko"
    else:
        return "en"


TEXTS = {
    "ar": {
        "welcome": "أهلاً بك. سنبني شركتك الرقمية في 3 دقائق.",
        "step1": "ما اسم شركتك؟",
        "step2": "صِف نشاطك التجاري في سطر واحد",
        "step2_example": "مثال: شركة تسويق رقمي للمطاعم في السعودية",
        "step3": "ما هدفك الرئيسي؟",
        "goal1": "زيادة المبيعات والعملاء",
        "goal2": "تقليل التكاليف وتحسين الكفاءة",
        "goal3": "إطلاق منتج أو خدمة جديدة",
        "goal4": "التوسع في سوق جديد",
        "step4": "ما مستوى المخاطرة المقبول؟",
        "risk1": "محافظ — لا مخاطرة عالية",
        "risk2": "متوسط — مخاطرة محسوبة",
        "risk3": "جريء — مستعد للمخاطرة",
        "step5": "ما الميزانية الشهرية التقريبية؟",
        "building": "جاري بناء شركتك الرقمية...",
        "building_constitution": "بناء الدستور...",
        "building_team": "تعيين الفريق التنفيذي...",
        "building_decision": "الفريق يتخذ أول قرار...",
        "building_review": "التقييم الدستوري...",
        "building_save": "حفظ ملف الشركة...",
        "done": "شركتك الرقمية جاهزة!",
        "approved": "موافقة",
        "rejected": "مرفوض",
        "choose_number": "اختر رقم",
        "chat_mode": "هل تريد التحدث مع شركتك الآن؟ (y/n)",
        "chat_prompt": "تحدث مع فريقك (اكتب exit للخروج):",
        "chat_exit": "وداعاً!",
    },
    "en": {
        "welcome": "Welcome. We'll build your digital company in 3 minutes.",
        "step1": "What's your company name?",
        "step2": "Describe your business in one line",
        "step2_example": "Example: Digital marketing agency for restaurants in Dubai",
        "step3": "What's your main goal?",
        "goal1": "Increase sales and clients",
        "goal2": "Reduce costs and improve efficiency",
        "goal3": "Launch a new product or service",
        "goal4": "Expand into a new market",
        "step4": "What risk level is acceptable?",
        "risk1": "Conservative — no high risk",
        "risk2": "Moderate — calculated risk",
        "risk3": "Aggressive — willing to risk for higher returns",
        "step5": "What's the approximate monthly budget?",
        "building": "Building your digital company...",
        "building_constitution": "Writing constitution...",
        "building_team": "Hiring executive team...",
        "building_decision": "Team making first decision...",
        "building_review": "Constitutional review...",
        "building_save": "Saving company files...",
        "done": "Your digital company is ready!",
        "approved": "Approved",
        "rejected": "Rejected",
        "choose_number": "Choose number",
        "chat_mode": "Want to talk to your company now? (y/n)",
        "chat_prompt": "Talk to your team (type exit to quit):",
        "chat_exit": "Goodbye!",
    },
    "fr": {
        "welcome": "Bienvenue. Nous construirons votre entreprise digitale en 3 minutes.",
        "step1": "Quel est le nom de votre entreprise?",
        "step2": "Decrivez votre activite en une ligne",
        "step2_example": "Exemple: Agence de marketing digital pour restaurants a Paris",
        "step3": "Quel est votre objectif principal?",
        "goal1": "Augmenter les ventes et les clients",
        "goal2": "Reduire les couts et ameliorer l'efficacite",
        "goal3": "Lancer un nouveau produit ou service",
        "goal4": "Se developper sur un nouveau marche",
        "step4": "Quel niveau de risque est acceptable?",
        "risk1": "Conservateur",
        "risk2": "Modere",
        "risk3": "Agressif",
        "step5": "Quel est le budget mensuel approximatif?",
        "building": "Construction de votre entreprise digitale...",
        "building_constitution": "Redaction de la constitution...",
        "building_team": "Recrutement de l'equipe...",
        "building_decision": "L'equipe prend sa premiere decision...",
        "building_review": "Revue constitutionnelle...",
        "building_save": "Sauvegarde des fichiers...",
        "done": "Votre entreprise digitale est prete!",
        "approved": "Approuve",
        "rejected": "Rejete",
        "choose_number": "Choisissez un numero",
        "chat_mode": "Voulez-vous parler a votre entreprise? (y/n)",
        "chat_prompt": "Parlez a votre equipe (tapez exit pour quitter):",
        "chat_exit": "Au revoir!",
    },
}


def get_text(lang, key):
    return TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))


def clear_screen():
    pass


def safe_company_dir_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\- ]+", "", name or "company", flags=re.UNICODE)
    cleaned = cleaned.replace(" ", "_").strip("_")
    return cleaned or "company"


def print_banner(lang):
    t = lambda key: get_text(lang, key)
    print("=" * 60)
    print(" SVOS Wizard")
    print("=" * 60)
    print(f" {t('welcome')}")
    print()


def ask_questions(lang):
    t = lambda key: get_text(lang, key)
    print(f" {t('step1')}")
    company_name = input(" > ").strip() or "My Company"

    print(f"\n {t('step2')}")
    print(f" {t('step2_example')}")
    description = input(" > ").strip() or "Digital services"

    print(f"\n {t('step3')}")
    goals = [t('goal1'), t('goal2'), t('goal3'), t('goal4')]
    for i, g in enumerate(goals, 1):
        print(f" {i}. {g}")
    g_choice = input(f" {t('choose_number')} > ").strip() or "1"
    try:
        g_idx = max(1, min(4, int(g_choice))) - 1
    except ValueError:
        g_idx = 0
    goal = goals[g_idx]

    print(f"\n {t('step4')}")
    risks = [t('risk1'), t('risk2'), t('risk3')]
    for i, r in enumerate(risks, 1):
        print(f" {i}. {r}")
    r_choice = input(f" {t('choose_number')} > ").strip() or "2"
    try:
        r_idx = max(1, min(3, int(r_choice))) - 1
    except ValueError:
        r_idx = 1
    risk_appetite = ["conservative", "moderate", "aggressive"][r_idx]

    print(f"\n {t('step5')}")
    budgets = ["$1,000", "$5,000", "$10,000+"]
    for i, b in enumerate(budgets, 1):
        print(f" {i}. {b}")
    b_choice = input(f" {t('choose_number')} > ").strip() or "2"
    try:
        b_idx = max(1, min(3, int(b_choice))) - 1
    except ValueError:
        b_idx = 1
    budget = budgets[b_idx]

    return {
        "company_name": company_name,
        "description": description,
        "goal": goal,
        "risk_appetite": risk_appetite,
        "budget": budget,
        "lang": lang,
    }


async def build_company(profile):
    lang = profile.get("lang", "en")
    t = lambda key: get_text(lang, key)

    print(f"\n {t('building')}")
    print(f" - {t('building_constitution')}")
    print(f" - {t('building_team')}")
    print(f" - {t('building_decision')}")
    print(f" - {t('building_review')}")
    print(f" - {t('building_save')}")

    constitution = SmartConstitution()
    decision = f"Launch first pilot for {profile['company_name']}"
    verdict = await constitution.evaluate_decision(
        decision=decision,
        agent_name="Board",
        context={"source": "wizard"},
        business_profile={
            "mission": profile["description"],
            "values": ["quality", "transparency", "growth"],
            "constraints": [f"budget {profile['budget']}"],
            "risk_appetite": profile["risk_appetite"],
        },
    )

    company_dir = Path("companies") / safe_company_dir_name(profile["company_name"])
    company_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "profile": profile,
        "decision": decision,
        "verdict": verdict.model_dump(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    with open(company_dir / "company.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(company_dir), decision, verdict


def print_result(profile, company_dir, decision, verdict, lang):
    t = lambda key: get_text(lang, key)
    print("\n" + "=" * 60)
    print(f" {t('done')}")
    print("=" * 60)
    print(f" Company: {profile['company_name']}")
    print(f" Dir: {company_dir}")
    print(f" Decision: {decision}")
    print(f" Verdict: {t('approved') if verdict.approved else t('rejected')} ({verdict.confidence:.0%})")
    print()


async def chat_mode(profile, team, lang):
    llm = LLMProvider()
    t = lambda key: get_text(lang, key)

    print()
    answer = input(f" {t('chat_mode')} ").strip().lower()
    if answer not in ("y", "yes", "نعم", "oui"):
        return

    print()
    print(f" {t('chat_prompt')}")
    print()

    system_prompt = f"""You are the executive team of {profile['company_name']}.
Company: {profile['description']}
Goal: {profile['goal']}
Risk appetite: {profile['risk_appetite']}
Respond in the same language the user writes in.
Be concise, strategic, and actionable.
Sign your response with which executive is speaking (CEO, CFO, CMO, etc.)."""

    while True:
        try:
            user_input = input(" YOU > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("exit", "quit", "خروج"):
            print(f"\n {t('chat_exit')}")
            break

        try:
            response = await llm.complete(system_prompt, user_input)
            clean_response = response.encode("utf-8", errors="replace").decode("utf-8")
            print(f"\n SVOS > {clean_response}\n")
        except Exception as e:
            print(f"\n [Error: {e}]\n")


def main():
    clear_screen()
    lang = detect_language()

    print(" Language:")
    print(" 1. English")
    print(" 2. العربية")
    print(" 3. Francais")
    choice = input(" > ").strip()

    if choice == "1":
        lang = "en"
    elif choice == "2":
        lang = "ar"
    elif choice == "3":
        lang = "fr"

    print_banner(lang)
    profile = ask_questions(lang)
    company_dir, decision, verdict = asyncio.run(build_company(profile))
    print_result(profile, company_dir, decision, verdict, lang)
    asyncio.run(chat_mode(profile, {}, lang))


if __name__ == "__main__":
    main()
