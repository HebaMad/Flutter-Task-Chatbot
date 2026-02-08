# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import unicodedata
from typing import Optional

# Units in minutes
UNIT_MINUTES = {
    "دقيقة": 1,
    "دقائق": 1,
    "دقايق": 1,
    "دقيقتين": 2,
    "ساعة": 60,
    "ساعات": 60,
    "ساعتين": 120,
    "يوم": 1440,
    "يومين": 2880,
    "أيام": 1440,
    "ايام": 1440,
    "أسبوع": 10080,
    "اسبوع": 10080,
    "أسبوعين": 20160,
    "اسبوعين": 20160,
    "شهر": 43200,
    "شهرين": 86400,
}

INTRODUCERS = ["لمدة", "مدة", "مدتها", "مدته", "على مدار"]
UNIT_PATTERN = r"دقيقة|دقائق|دقايق|دقيقتين|ساعة|ساعات|ساعتين|يوم|يومين|أيام|ايام|أسبوعين|اسبوعين|أسبوع|اسبوع|شهرين|شهر"


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return text


def parse_duration_to_minutes(text: str) -> Optional[int]:
    """Parse Arabic duration phrase into minutes; never raises."""
    try:
        norm = _normalize(text)
        if not norm:
            return None
        if re.search(r"ساعة\s+ونص|ساعة\s+ونصف", norm):
            return 90
        if re.search(r"نص\s+ساعة", norm):
            return 30
        intro_re = re.compile(rf"(?:{'|'.join(map(re.escape, INTRODUCERS))})\s+([^.,؛\n?!]+)", re.IGNORECASE)
        m = intro_re.search(norm)
        candidate = m.group(1) if m else norm
        num_unit = re.search(rf"(\d+(?:\.\d+)?)\s+({UNIT_PATTERN})", candidate, re.IGNORECASE)
        if num_unit:
            num = float(num_unit.group(1))
            unit = num_unit.group(2)
            return int(num * UNIT_MINUTES.get(unit, 0)) if unit in UNIT_MINUTES else None
        unit_only = re.search(rf"\b({UNIT_PATTERN})\b", candidate, re.IGNORECASE)
        if unit_only:
            unit = unit_only.group(1)
            return UNIT_MINUTES.get(unit)
    except Exception:
        return None
    return None


def strip_duration_phrase(text: str) -> str:
    """Remove duration phrase safely; return original if anything fails."""
    if not text:
        return text
    try:
        norm = _normalize(text)
        intro_re = re.compile(rf"(?:{'|'.join(map(re.escape, INTRODUCERS))})\s+[^\n.,؛?!]+", re.IGNORECASE)
        m = intro_re.search(norm)
        if not m:
            num_re = re.compile(rf"\d+\s+({UNIT_PATTERN})", re.IGNORECASE)
            m = num_re.search(norm)
        if not m:
            return text.strip()
        start, end = m.span()
        return (text[:start] + " " + text[end:]).strip()
    except Exception:
        return text


parse_duration_minutes = parse_duration_to_minutes


def extract_duration_minutes_and_clean(text: str):
    """
    Convenience helper: returns (duration_minutes, cleaned_text).
    If parsing fails, returns (None, original_text).
    """
    minutes = parse_duration_to_minutes(text)
    cleaned = strip_duration_phrase(text)
    return minutes, cleaned
