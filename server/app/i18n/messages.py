from __future__ import annotations

from typing import Dict, Literal


Dialect = Literal["pal", "egy", "khg"]

MESSAGES: Dict[Dialect, Dict[str, str]] = {
    "pal": {
        "STUB_OK": "تمام، استلمت رسالتك. (لسا شغّالين على التنفيذ)",
        "AMBIGUOUS_PICK_ONE": "أي وحدة قصدك؟ اختار وحدة من القائمة.",
        "ERR_UNAUTHORIZED": "بدنا تفويض قبل ما نكمل.",
        "ERR_INVALID_REQUEST": "في نقص بالطلب. ابعث المعلومات المطلوبة.",
        "ERR_INTERNAL": "صار خطأ غير متوقع. جرّب كمان مرة.",
        "ERR_RATE_LIMITED": "في ضغط عالي. جرّب بعد شوي.",
        "PAYWALL_NO_TOKENS": "رصيد التوكنز خلص. اشحن عشان نكمل.",
    },
    "egy": {
        "STUB_OK": "تمام، وصلتني رسالتك. (لسه بنجهّز التنفيذ)",
        "AMBIGUOUS_PICK_ONE": "تقصد أنهي واحدة؟ اختار من اللي ظاهر.",
        "ERR_UNAUTHORIZED": "لازم تفويض قبل ما نكمل.",
        "ERR_INVALID_REQUEST": "فيه بيانات ناقصة في الطلب.",
        "ERR_INTERNAL": "حصل خطأ غير متوقع. جرّب تاني.",
        "ERR_RATE_LIMITED": "في ضغط عالي. جرّب بعد شوية.",
        "PAYWALL_NO_TOKENS": "رصيد التوكنز خلص. اشحن عشان نكمل.",
    },
    "khg": {
        "STUB_OK": "تم، وصلتني رسالتك. (جاري تجهيز التنفيذ)",
        "AMBIGUOUS_PICK_ONE": "أي مهمة تقصد؟ اختر وحدة من القائمة.",
        "ERR_UNAUTHORIZED": "يلزم تفويض قبل المتابعة.",
        "ERR_INVALID_REQUEST": "الطلب ناقص بيانات.",
        "ERR_INTERNAL": "صار خطأ غير متوقع. جرّب مرة ثانية.",
        "ERR_RATE_LIMITED": "في ضغط عالي. جرّب بعد شوي.",
        "PAYWALL_NO_TOKENS": "رصيد التوكنز انتهى. اشحن عشان نكمل.",
    },
}


def msg(dialect: Dialect, key: str, **kwargs) -> str:
    template = MESSAGES.get(dialect, MESSAGES["pal"]).get(key, key)
    try:
        return template.format(**kwargs)
    except Exception:
        return template
