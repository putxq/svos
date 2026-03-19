import asyncio

from agents.ceo.agent import CEOAgent
from agents.cfo.agent import CFOAgent
from agents.cmo.agent import CMOAgent
from agents.radar.agent import RadarAgent
from engine.discussion_engine import DiscussionEngine
from sovereign_kernel.smart_constitution import SmartConstitution
from sovereign_kernel.confidence_engine import ConfidenceEngine
from sovereign_kernel.trust_safety import TrustSafetyKernel
from sovereign_kernel.learning_laws import LearningLaws


async def test_first_live_decision():
    print("=" * 60)
    print(" SVOS — أول شركة رقمية حية تتخذ قراراً")
    print("=" * 60)

    # تهيئة
    ceo = CEOAgent()
    cfo = CFOAgent()
    cmo = CMOAgent()
    radar = RadarAgent()
    safety = TrustSafetyKernel()
    laws = LearningLaws()

    # --- الخطوة 1: فحص أمان العملية ---
    print("\n[1/6] فحص الأمان...")
    safety_check = safety.evaluate_action(
        action="قرار دخول سوق المطاعم",
        agent_name="CEO",
        action_type="general",
    )
    print(f" آمن: {safety_check.safe}")
    print(f" درجة الخطر: {safety_check.risk_score:.0%}")
    print(f" الإجراء: {safety_check.action}")

    if not safety_check.safe:
        print(" ⛔ العملية محظورة لأسباب أمنية")
        return

    # --- الخطوة 2: CEO يفكر ---
    print("\n[2/6] CEO يفكر في الفرصة...")
    ceo_think = await ceo.think(
        task="هل يجب أن نستهدف قطاع المطاعم بخدمات التسويق الرقمي في السعودية؟",
        context={"market": "السعودية", "current_clients": 0, "budget": "$5,000"},
    )
    print(f" خطة CEO: {ceo_think.plan}")
    print(f" ثقة CEO: {ceo_think.confidence:.0%}")
    print(f" يحتاج نقاش: {ceo_think.needs_discussion}")
    print(f" يحتاج تصعيد: {ceo_think.needs_escalation}")

    # --- الخطوة 3: نقاش الفريق ---
    print("\n[3/6] نقاش الفريق التنفيذي...")
    discussion = DiscussionEngine()
    disc_result = await discussion.open_discussion(
        topic="دخول سوق المطاعم بخدمات التسويق الرقمي في السعودية",
        initiator="CEO",
        participants=["CEO", "CFO", "CMO", "Radar"],
        context={
            "market": "السعودية",
            "sector": "مطاعم",
            "service": "تسويق رقمي",
            "budget": "$5,000",
        },
        max_rounds=2,
    )
    print(f" القرار: {disc_result.decision[:200]}")
    print(f" الإجماع: {disc_result.consensus:.0%}")
    if disc_result.dissents:
        print(f" اعتراضات: {len(disc_result.dissents)}")

    # --- الخطوة 4: درجة الثقة ---
    print("\n[4/6] حساب درجة الثقة (منطق تسلا)...")
    conf_engine = ConfidenceEngine()
    confidence = conf_engine.calculate(
        task_clarity=0.8,
        data_availability=0.6,
        past_success_rate=0.0,  # أول مرة — لا تجارب سابقة
        constitution_alignment=0.9,
        market_volatility=0.4,
    )
    print(f" الدرجة: {confidence.score:.0%}")
    print(f" المستوى: {confidence.level}")
    print(f" العوامل: {confidence.factors}")

    # --- الخطوة 5: التقييم الدستوري ---
    print("\n[5/6] التقييم الدستوري...")
    constitution = SmartConstitution()
    verdict = await constitution.evaluate_decision(
        decision=disc_result.decision[:500] if disc_result.decision else "دخول سوق المطاعم",
        agent_name="Board",
        context={"discussion_consensus": disc_result.consensus},
        business_profile={
            "mission": "تقديم خدمات تسويق رقمي احترافية للشركات السعودية",
            "values": ["الجودة", "الشفافية", "النمو المستدام"],
            "constraints": ["ميزانية أولية $5,000", "فريق من وكلاء فقط"],
            "risk_appetite": "moderate",
        },
    )
    print(f" موافقة: {verdict.approved}")
    print(f" ثقة الدستور: {verdict.confidence:.0%}")
    print(f" التبرير: {verdict.reasoning[:300]}")

    # --- الخطوة 6: القرار النهائي + التعلم ---
    print("\n[6/6] القرار النهائي...")
    print("=" * 60)
    if verdict.approved and confidence.score >= 0.4:
        print("✅ القرار: موافقة — ندخل سوق المطاعم!")
        outcome = True
    else:
        print("❌ القرار: رفض — لا ندخل الآن")
        if verdict.alternatives:
            print(f" بدائل: {verdict.alternatives}")
        outcome = False

    # التعلم
    can_learn = laws.can_learn(trace_exists=True)
    if can_learn:
        await ceo.learn_from_outcome(
            task="قرار دخول سوق المطاعم",
            outcome="موافقة" if outcome else "رفض",
            success=outcome,
        )
        print("\n📚 تم حفظ القرار في الذاكرة الاستراتيجية")
        print(" (قانون التعلم: trace موجود = التعلم مسموح)")
    else:
        print("\n⚠️ لم يُحفظ — لا trace متاح (القانون 1)")

    print("\n" + "=" * 60)
    print(" SVOS — أول قرار لشركة رقمية حية ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_first_live_decision())
