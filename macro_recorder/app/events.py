from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AppEvent:
    type: str
    payload: dict[str, Any]


def ev(event_type: str, **payload: Any) -> AppEvent:
    return AppEvent(type=event_type, payload=payload)
