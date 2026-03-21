import asyncio

async def test():
    from scheduler import get_scheduler

    s = get_scheduler()
    print('=== Scheduler Status ===')
    status = s.get_status()
    for k, v in status.items():
        print(f'  {k}: {v}')

    print()
    print('=== Running Single Cycle ===')
    print('(This will call CEO.think + GravityEngine + TimeEngine)')
    print('Starting...')

    try:
        result = await s._run_cycle()
        print(f"Cycle {result['cycle']} completed in {result.get('duration_seconds', 0):.1f}s")
        print()

        for phase_name, phase_data in result['phases'].items():
            status_icon = '[OK]' if phase_data.get('status') == 'done' else '[ERR]'
            print(f"  {status_icon} {phase_name}: {phase_data.get('status')}")
            if phase_data.get('error'):
                print(f"     Error: {phase_data['error'][:150]}")
            if phase_data.get('summary'):
                print(f"     Summary: {phase_data['summary'][:150]}...")
    except Exception as e:
        print(f'Cycle failed: {e}')

    print()
    print('=== Heartbeat Check ===')
    health = await s.heartbeat()
    print(f"  Overall: {health['overall']}")
    for check, data in health['checks'].items():
        if isinstance(data, dict):
            print(f"  {check}: {data.get('status', data)}")
        else:
            print(f"  {check}: {data}")

asyncio.run(test())
