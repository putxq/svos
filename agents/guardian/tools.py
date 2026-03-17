def compact(text: str) -> str:
    return (text or '').strip()[:6000]
