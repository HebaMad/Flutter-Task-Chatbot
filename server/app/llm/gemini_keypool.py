import os
import itertools
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GeminiKeyPool:
    keys: List[str]
    cooldown_seconds: int = 15

    def __post_init__(self):
        self._cycle = itertools.cycle(self.keys)
        self._cooldowns = {k: 0.0 for k in self.keys}  # unix timestamp when key is usable again

    @staticmethod
    def from_env() -> "GeminiKeyPool":
        raw = os.getenv("GEMINI_API_KEYS", "").strip()
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys:
            raise RuntimeError("GEMINI_API_KEYS is not set or empty")
        return GeminiKeyPool(keys=keys)

    def next_key(self) -> str:
        # try at most len(keys) times to find a non-cooled-down key
        for _ in range(len(self.keys)):
            k = next(self._cycle)
            if time.time() >= self._cooldowns.get(k, 0.0):
                return k
        # if all keys are cooling down, just return next (caller can sleep or fallback)
        return next(self._cycle)

    def cool_down(self, key: str, seconds: Optional[int] = None) -> None:
        self._cooldowns[key] = time.time() + float(seconds or self.cooldown_seconds)
