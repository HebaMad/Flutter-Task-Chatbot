# -*- coding: utf-8 -*-
from __future__ import annotations
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional, Tuple

try:
    import pytz
except ImportError:  # pragma: no cover
    pytz = None

# ---- Helpers ----
STOPWORDS = {"بدي", "بدى", "بدي", "ممكن", "لو", "سمحت"}
REL_DAY = {
    "اليوم": 0,
    "بكرة": 1,
    "غداً": 1,
    "غدا": 1,
    "بعد بكرة": 2,
    "بعدبكرة": 2,
    "لبكرة": 1,
    "لبكرا": 1,
}
REL_DAY_NORM = { }
for k, v in REL_DAY.items():
    try:
        REL_DAY_NORM[_normalize(k)] = v
    except Exception:
        REL_DAY_NORM[k] = v
TIME_RE = re.compile(r"(?:الساعة\s*)?(\d{1,2})(?::(\d{1,2}))?\s*(ص|صباحاً|صباحا|م|مساءً|مساء|am|pm)?", re.IGNORECASE)

DURATION_UNITS = {
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
INTRO = ["لمدة", "مدة", "مدتها", "مدته", "خلال", "مهلة", "على مدار"]
UNIT_PATTERN = r"دقيقة|دقائق|دقايق|دقيقتين|ساعة|ساعات|ساعتين|يوم|يومين|أيام|ايام|أسبوعين|اسبوعين|أسبوع|اسبوع|شهرين|شهر"

# ---- Normalization ----

def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return text

# ---- Duration ----

def extract_duration_minutes_and_clean(text: str) -> Tuple[Optional[int], str]:
    try:
        norm = _normalize(text)
        if not norm:
            return None, text
        # special cases
        if re.search(r"ساعة\s+ونص|ساعة\s+ونصف", norm):
            span = re.search(r"ساعة\s+ونص|ساعة\s+ونصف", norm).span()
            return 90, _remove_span(text, span)
        if re.search(r"نص\s+ساعة", norm):
            span = re.search(r"نص\s+ساعة", norm).span()
            return 30, _remove_span(text, span)

        intro_re = re.compile(rf"(?:{'|'.join(map(re.escape, INTRO))})\s+([^\n.,؛?!]+)", re.IGNORECASE)
        m = intro_re.search(norm)
        candidate = m.group(1) if m else norm
        candidate_span = m.span() if m else None

        num_unit = re.search(rf"(\d+(?:\.\d+)?)\s+({UNIT_PATTERN})", candidate, re.IGNORECASE)
        if num_unit:
            minutes = int(float(num_unit.group(1)) * DURATION_UNITS.get(num_unit.group(2), 0))
            if minutes > 0:
                span = _offset_span(candidate_span, num_unit.span()) if candidate_span else num_unit.span()
                return minutes, _remove_span(text, span)

        unit_only = re.search(rf"\b({UNIT_PATTERN})\b", candidate, re.IGNORECASE)
        if unit_only:
            minutes = DURATION_UNITS.get(unit_only.group(1), 0)
            if minutes > 0:
                span = _offset_span(candidate_span, unit_only.span()) if candidate_span else unit_only.span()
                return minutes, _remove_span(text, span)
    except Exception:
        return None, text
    return None, text


def _offset_span(parent_span, inner_span):
    if not parent_span:
        return inner_span
    return (parent_span[0] + inner_span[0], parent_span[0] + inner_span[1])


def _remove_span(text: str, span: Tuple[int, int]) -> str:
    start, end = span
    cleaned = text[:start] + " " + text[end:]
    return re.sub(r"\s+", " ", cleaned).strip()


# ---- Due datetime ----

def _tz_now(tzname: str, now: datetime) -> datetime:
    if pytz:
        try:
            return now.astimezone(pytz.timezone(tzname))
        except Exception:
            return now
    return now


def extract_due_datetime_and_clean(text: str, timezone: str, now_dt: datetime) -> Tuple[Optional[datetime], str]:
    """Parse relative Arabic day/time. Default time when date-only: 09:00 local.
    Never raises; returns (due_dt, cleaned_text)."""
    try:
        norm = _normalize(text)
        base = _tz_now(timezone, now_dt)
        due = None
        removal_spans = []

        for phrase, delta in REL_DAY_NORM.items():
            idx = norm.find(phrase)
            if idx >= 0:
                due_date = (base + timedelta(days=delta)).date()
                removal_spans.append((idx, idx + len(phrase)))
                due = datetime.combine(due_date, datetime.min.time()).replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=base.tzinfo)
                break

        m = TIME_RE.search(norm)
        if m:
            hour = int(m.group(1)); minute = int(m.group(2) or 0); mer = (m.group(3) or "").lower()
            if mer in {"م", "pm", "مساء", "مساءً"} and hour < 12:
                hour += 12
            if mer in {"ص", "am", "صباحا", "صباحاً"} and hour == 12:
                hour = 0
            removal_spans.append(m.span())
            if due is None:
                due_time = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if due_time < base:
                    due_time += timedelta(days=1)
                due = due_time
            else:
                due = due.replace(hour=hour, minute=minute, second=0, microsecond=0)

        cleaned = text
        for s, e in sorted(removal_spans, reverse=True):
            cleaned = cleaned[:s] + " " + cleaned[e:]
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return due, cleaned
    except Exception:
        return None, text

