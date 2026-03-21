from pathlib import Path
p = Path(r"C:\Users\OMARE\Desktop\svos\scheduler.py")
s = p.read_text(encoding='utf-8')
old = '''            result = await ceo.think(
                "Generate a morning briefing for the SVOS system. "
                "Summarize system status, pending priorities, and recommended focus areas for today."
            )
'''
new = '''            result = await ceo.think(
                task="Generate a morning briefing for the SVOS system. "
                "Summarize system status, pending priorities, and recommended focus areas for today.",
                context="You are the CEO of a sovereign AI company called SVOS. "
                "The system has 9 C-suite agents, 4 execution tools, and runs autonomous cycles.",
            )
'''
if old in s:
    s = s.replace(old, new)
else:
    raise SystemExit('target block not found')
p.write_text(s, encoding='utf-8')
print('patched')
