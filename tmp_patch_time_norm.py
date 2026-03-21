from pathlib import Path
p = Path(r"C:\Users\OMARE\Desktop\svos\engines\time_engine.py")
s = p.read_text(encoding='utf-8')
old = '                total_confidence += scenario.get("confidence", 0.5)\n'
new = '                total_confidence += ConfidenceEngine.normalize(scenario.get("confidence", 0.5))\n'
if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')
    print('patched time normalize')
else:
    raise SystemExit('target line not found in time_engine.py')
