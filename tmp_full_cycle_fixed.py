import asyncio

async def test():
    from scheduler import get_scheduler

    s = get_scheduler()
    print('=== Running Full Cycle (Fixed) ===')
    print()

    result = await s._run_cycle()
    print(f"Cycle {result['cycle']} completed in {result.get('duration_seconds', 0):.1f}s")
    print()

    all_ok = True
    for name, data in result['phases'].items():
        icon = '[OK]' if data.get('status') == 'done' else '[ERR]'
        if data.get('status') != 'done':
            all_ok = False
        print(f"  {icon} {name}: {data.get('status')}")
        if data.get('error'):
            print(f"     Error: {data['error'][:200]}")
        if data.get('summary'):
            print(f"     {data['summary'][:200]}")
        if data.get('opportunities'):
            print(f"     {data['opportunities'][:200]}")
        if data.get('decision'):
            print(f"     {data['decision'][:200]}")

    print()
    health = await s.heartbeat()
    print(f"Heartbeat: {health['overall']}")
    print(f"Agents: {health['checks']['agents']}")
    print()

    if all_ok:
        print('ALL 5 PHASES PASSED - AutonomousLoop is OPERATIONAL')
    else:
        print('Some phases need attention')

asyncio.run(test())
