import re
import json


def parse_llm_json(text: str) -> dict:
    """
    ينظف ويستخرج JSON من أي رد Claude.
    يتعامل مع: markdown fences, JSON مقطوع, JSON داخل نص.
    """
    if not text or not isinstance(text, str):
        return {}

    text = text.strip()

    # إزالة markdown fences
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?\s*```$', '', text)
    text = text.strip()

    # محاولة 1: JSON كامل
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # محاولة 2: استخرج من أول { لآخر }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    # محاولة 3: أصلح JSON مقطوع
    if start != -1:
        partial = text[start:]

        # أغلق strings مفتوحة
        in_string = False
        escaped = False
        for ch in partial:
            if escaped:
                escaped = False
                continue
            if ch == '\\':
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string

        if in_string:
            partial += '"'

        # أغلق brackets و braces
        open_brackets = partial.count('[') - partial.count(']')
        open_braces = partial.count('{') - partial.count('}')

        partial += ']' * max(0, open_brackets)
        partial += '}' * max(0, open_braces)

        try:
            return json.loads(partial)
        except json.JSONDecodeError:
            pass

    # محاولة 4: حاول تلاقي أي JSON object في النص
    pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(pattern, text)
    for match in reversed(matches):  # ابدأ بالأكبر
        try:
            return json.loads(match)
        except:
            continue

    return {}


def extract_field(data: dict, *keys, default=None):
    """يبحث عن حقل في أماكن متعددة — لأن Claude يغير أسماء الحقول"""
    for key in keys:
        if '.' in key:
            parts = key.split('.')
            val = data
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
                    break
            if val is not None:
                return val
        elif key in data and data[key]:
            return data[key]
    return default
