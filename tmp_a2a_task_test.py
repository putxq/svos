import asyncio
from infrastructure.a2a_protocol import get_a2a_handler

async def test():
    handler = get_a2a_handler()
    task = await handler.create_task('CTO', 'Evaluate MCP protocol adoption for SVOS')
    print(f"Task ID: {task.id}")
    print(f"State: {task.state}")
    print(f"Messages: {len(task.messages)}")
    if task.messages:
        last = task.messages[-1]
        print(f"Last message ({last['role']}): {last['parts'][0]['text'][:200]}...")

asyncio.run(test())
