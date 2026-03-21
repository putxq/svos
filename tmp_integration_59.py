import asyncio

async def test():
    print('=== Testing GravityEngine with ConfidenceEngine ===')
    from engines.gravity_engine import GravityEngine
    g = GravityEngine()
    result = await g.find_demand_gravity('Saudi restaurant delivery automation AI')
    opps = result.get('opportunities', [])
    print(f'Found {len(opps)} opportunities')
    for o in opps[:3]:
        conf = o.get('confidence', '?')
        name = o.get('name', o.get('opportunity', o.get('title', '?')))
        print(f'  {name}: confidence={conf} (type={type(conf).__name__})')

    print()
    print('=== Testing TimeEngine with ConfidenceEngine ===')
    from engines.time_engine import TimeEngine
    t = TimeEngine()
    result = await t.should_proceed('Launch WhatsApp campaign for 20 restaurants', {'budget': '5000 SAR'})
    print(f"Recommendation: {result.get('recommendation')}")
    print(f"Avg confidence: {result.get('avg_confidence')} (type={type(result.get('avg_confidence')).__name__})")

    conf = result.get('avg_confidence', 0)
    if isinstance(conf, float) and 0.0 <= conf <= 1.0:
        print(f'Confidence is normalized float: {conf:.3f}')
    else:
        print(f'WARNING: confidence not normalized: {conf}')

    print()
    from engines.confidence_engine import ConfidenceEngine
    action = ConfidenceEngine.get_action_level(conf)
    print(f'Action level: {action}')
    print()
    print('INTEGRATION TEST COMPLETE')

asyncio.run(test())
