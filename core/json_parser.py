import re
import json
import logging

logger = logging.getLogger("svos.json_parser")


def parse_llm_json(text: str) -> dict:
    """
    ينظف ويستخرج JSON من أي رد LLM.
    يتعامل مع: markdown fences, JSON مقطوع, JSON داخل نص, JSON arrays, تعليقات, trailing commas.
    """
    if not text or not isinstance(text, str):
        return {}

    text = text.strip()

    # إزالة markdown fences
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?\s*```$', '', text, flags=re.MULTILINE)
    text = text.strip()

    # إزالة أي نص قبل أول { أو بعد آخر }
    # بعض النماذج تضيف "Here is the JSON:" قبل الـ JSON
    text = re.sub(r'^[^{\[]*(?=[{\[])', '', text, count=1)

    # إزالة trailing commas (مشكلة شائعة مع LLMs)
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # إزالة تعليقات JavaScript-style
    text = re.sub(r'//[^\n]*', '', text)

    # محاولة 1: JSON كامل مباشر
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and result:
            return {"items": result}
        return {}
    except json.JSONDecodeError:
        pass

    # محاولة 2: استخرج من أول { لآخر }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]

        # نظف trailing commas مرة ثانية في الـ candidate
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # محاولة 3: أصلح JSON مقطوع
    if start != -1:
        partial = text[start:]
        partial = re.sub(r',\s*([}\]])', r'\1', partial)

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

        # أزل trailing commas مرة أخيرة
        partial = re.sub(r',\s*([}\]])', r'\1', partial)

        try:
            return json.loads(partial)
        except json.JSONDecodeError:
            pass

    # محاولة 4: حاول تلاقي أي JSON object في النص
    pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(pattern, text)
    for match in reversed(matches):
        clean_match = re.sub(r',\s*([}\]])', r'\1', match)
        try:
            return json.loads(clean_match)
        except Exception:
            continue

    # محاولة 5: key-value extraction كملاذ أخير
    # بعض النماذج ترجع شيء مثل: confidence: 78, is_real: true
    kv_pattern = r'"?(\w+)"?\s*:\s*("[^"]*"|\d+\.?\d*|true|false|null|\[[^\]]*\])'
    kv_matches = re.findall(kv_pattern, text, re.IGNORECASE)
    if len(kv_matches) >= 2:
        reconstructed = {}
        for key, value in kv_matches:
            try:
                reconstructed[key] = json.loads(value)
            except Exception:
                reconstructed[key] = value.strip('"')

        if reconstructed:
            logger.warning(f"json_parser: reconstructed {len(reconstructed)} fields from broken JSON")
            return reconstructed

    logger.warning(f"json_parser: all attempts failed, returning empty dict. Input length: {len(text)}")
    return {}


def extract_field(data: dict, *keys, default=None):
    """
    يبحث عن حقل في أماكن متعددة — لأن LLMs تغير أسماء الحقول.
    يدعم: مفاتيح مباشرة، مسارات منقطة، قوائم داخل dict.
    """
    if not isinstance(data, dict):
        return default

    for key in keys:
        if '.' in key:
            parts = key.split('.')
            val = data
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                elif isinstance(val, list) and p.isdigit():
                    idx = int(p)
                    val = val[idx] if idx < len(val) else None
                else:
                    val = None
                    break
            if val is not None:
                return val

        elif key in data and data[key] is not None:
            # تحقق إنه مو فارغ
            v = data[key]
            if isinstance(v, (list, dict)) and not v:
                continue  # فارغ — جرب المفتاح التالي
            if isinstance(v, str) and not v.strip():
                continue  # string فارغ
            return v

    return default


def safe_parse_number(value, default: float = 0.0) -> float:
    """يحوّل أي قيمة لرقم بأمان — مفيد للثقة والنسب."""
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value = value.strip().rstrip('%')
        try:
            return float(value)
        except ValueError:
            return default

    return default
