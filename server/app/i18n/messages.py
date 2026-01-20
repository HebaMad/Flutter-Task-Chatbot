from __future__ import annotations
from typing import Dict, Literal


Dialect = Literal["pal", "egy", "khg"]

MESSAGES: Dict[str, Dict[str, str]] = {
    "pal": {
        "task_created": "تمام، أضفت المهمة.",
        "tasks_list": "هاي مهامك.",
        "task_updated": "تم تعديل المهمة.",
        "task_deleted": "تم حذف المهمة.",
        "not_found": "ما لقيت هالمهمة.",
        "not_implemented": "هالميزة لسه مش جاهزة، بس رح نضيفها قريب.",
        "clarify": "ممكن توضّحي/توضح أكتر؟",
        "task_completed": "تمام! علّمتها كمُنجزة ✅",

    },
    "egy": {
        "task_created": "تمام، ضفت المهمة.",
        "tasks_list": "دي مهامك.",
        "task_updated": "عدلت المهمة.",
        "task_deleted": "مسحت المهمة.",
        "not_found": "مش لاقي المهمة دي.",
        "not_implemented": "الميزة دي لسه مش جاهزة، بس هنضيفها قريب.",
        "clarify": "ممكن توضحلي أكتر؟",
        "task_completed": "تمام! علّمتها كإنها خلصت ✅",

    },
    "khg": {
        "task_created": "تمام! ضفنا المهمة 👍",
        "task_updated": "تم تعديل المهمة ✅",
        "task_deleted": "انحذفت المهمة 🗑️",
        "task_completed": "تم إنجاز المهمة 👌",
        "clarify": "ممكن توضّحين أكثر؟",
        "not_implemented": "الميزة هذي لسه غير متوفرة",
    },
}

def msg(key: str, dialect: Dialect = "pal", **kwargs) -> str:
    template = MESSAGES.get(dialect, MESSAGES["pal"]).get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template
