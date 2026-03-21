from pathlib import Path
p = Path(r"C:\Users\OMARE\Desktop\svos\engines\gravity_engine.py")
s = p.read_text(encoding='utf-8')
old = '        deep_evals.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)\n'
new = '        # Normalize all confidence values through ConfidenceEngine\n        for opp in deep_evals:\n            opp["confidence"] = ConfidenceEngine.normalize(opp.get("confidence", 0.5))\n\n        deep_evals.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)\n'
if old in s:
    s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')
    print('patched gravity normalize')
else:
    raise SystemExit('target line not found in gravity_engine.py')
