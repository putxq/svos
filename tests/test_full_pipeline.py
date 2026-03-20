import asyncio

from agents.ceo.agent import CEOAgent


async def test_ceo_full_pipeline():
    ceo = CEOAgent()
    idea = "Digital marketing agency for restaurants in Riyadh"

    print("=" * 60)
    print(" SVOS Full Pipeline Test")
    print("=" * 60)

    # 1. CEO scans market
    print("\n[1/4] Scanning market...")
    market = await ceo.scan_market("restaurants", "Riyadh", "digital marketing")
    opps = market.get("opportunities", [])
    print(f" Found {len(opps)} opportunities")
    for o in opps[:2]:
        print(f" - {o.get('title', '?')} ({o.get('confidence', 0):.0%})")

    # 2. CEO simulates future
    print("\n[2/4] Simulating future...")
    future = await ceo.simulate_future(idea, {"budget": "$5000"})
    print(f" Recommendation: {future.get('recommendation', '?')}")
    print(f" Confidence: {future.get('avg_confidence', 0):.0%}")

    # 3. CEO compiles idea
    print("\n[3/4] Compiling idea to execution package...")
    package = await ceo.compile_idea(idea, {"budget": "$5000"})
    print(f" Product: {package.get('prd', {}).get('product_name', '?')}")
    print(f" Headline: {str(package.get('landing_page', {}).get('headline', '?'))[:80]}")

    # 4. CEO thinks about it all
    print("\n[4/4] CEO final decision...")
    decision = await ceo.think(
        task=f"Based on market scan ({len(opps)} opportunities found) and future simulation ({future.get('recommendation')}), should we launch: {idea}?",
        context={
            "opportunities": len(opps),
            "recommendation": future.get("recommendation"),
            "product_name": package.get("prd", {}).get("product_name"),
        },
    )

    print(f" Plan: {decision.plan}")
    print(f" Confidence: {decision.confidence:.0%}")
    print(f" Needs discussion: {decision.needs_discussion}")

    print("\n" + "=" * 60)
    print(" Full pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ceo_full_pipeline())
