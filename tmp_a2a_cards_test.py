from infrastructure.a2a_protocol import get_a2a_handler
handler = get_a2a_handler()
cards = handler.list_agent_cards()
print(f"A2A agent cards: {len(cards)}")
for c in cards:
    skills = [s['id'] for s in c.get('skills', [])]
    print(f" {c['name']}: skills={skills}")
