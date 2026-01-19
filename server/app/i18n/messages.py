from __future__ import annotations

from typing import Dict, Literal


Dialect = Literal["pal", "egy", "khg"]
# app/i18n/messages.py

MESSAGES = {
    "pal": {
        "not_implemented": "هالميزة لسه مش جاهزة، بس رح نضيفها قريب.",
        "clarify": "ممكن توضّحي/توضح أكتر؟",
    },
    "egy": {
        "not_implemented": "الميزة دي لسه مش جاهزة، بس هنضيفها قريب.",
        "clarify": "ممكن توضحلي أكتر؟",
    },
}

def msg(key: str, dialect: str = "pal") -> str:
    # fallback: لو dialect مش موجود، رجّعي pal
    return MESSAGES.get(dialect, MESSAGES["pal"]).get(key, key)
def msg(dialect: Dialect, key: str, **kwargs) -> str:
    template = MESSAGES.get(dialect, MESSAGES["pal"]).get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template
