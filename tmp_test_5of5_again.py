import asyncio

async def test():
    from scheduler import get_scheduler
    s = get_scheduler()
    result = await s._run_cycle()
    print(f"Cycle {result['cycle']} — {result.get('duration_seconds',0):.1f}s")
    passed = 0
    for name, data in result['phases'].items():
        ok = data.get('status') == 'done'
        if ok:
            passed += 1
        icon = '[OK]' if ok else '[ERR]'
        print(f" {icon} {name}")
        if data.get('error'):
            print(f"   {data['error'][:200]}")
    print(f"Result: {passed}/5")
    if passed == 5:
        print('ALL PHASES PASSED — COMMIT NOW')

asyncio.run(test())
