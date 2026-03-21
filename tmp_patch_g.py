from pathlib import Path
p = Path(r"C:\Users\OMARE\Desktop\svos\engines\gravity_engine.py")
s = p.read_text(encoding='utf-8')
needle = 'from core.json_parser import parse_llm_json, extract_field'
ins = needle + '\nfrom engines.confidence_engine import ConfidenceEngine\nfrom core.response_schemas import validate_response, OpportunitySchema, GravityResult'
if needle in s and 'from engines.confidence_engine import ConfidenceEngine' not in s:
    s = s.replace(needle, ins)
marker = 'def _extract_confidence(obj: dict, scale_hint: str = "auto") -> float:'
if marker in s and '# Use centralized ConfidenceEngine for normalization' not in s:
    s = s.replace(marker, marker + '\n        # Use centralized ConfidenceEngine for normalization')
p.write_text(s, encoding='utf-8')
print('patched gravity')
