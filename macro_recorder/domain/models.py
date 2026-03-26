from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal, TypedDict
import platform


MouseButton = Literal["left", "right", "middle"]
ActionKind = Literal[
    "mouse_move",
    "mouse_down",
    "mouse_up",
    "scroll",
    "key_down",
    "key_up",
    "wait",
]


class MacroAction(TypedDict, total=False):
    t_ms: int
    kind: ActionKind
    x: int
    y: int
    button: MouseButton
    dx: int
    dy: int
    key: str
    duration_ms: int


@dataclass(slots=True)
class MacroDocument:
    name: str = "Untitled Macro"
    actions: list[MacroAction] = field(default_factory=list)
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    platform: str = field(default_factory=platform.platform)
    screen_size: tuple[int, int] = (0, 0)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["screen_size"] = list(self.screen_size)
        return payload

    @property
    def duration_ms(self) -> int:
        if not self.actions:
            return 0
        return max(a["t_ms"] for a in self.actions)


def action_label(action: MacroAction) -> str:
    kind = action["kind"]
    if kind in {"mouse_move", "mouse_down", "mouse_up"}:
        return f"{kind} ({action.get('x', 0)}, {action.get('y', 0)})"
    if kind == "scroll":
        return f"scroll dx={action.get('dx', 0)} dy={action.get('dy', 0)}"
    if kind in {"key_down", "key_up"}:
        return f"{kind} {action.get('key', '')}"
    if kind == "wait":
        return f"wait {action.get('duration_ms', 0)}ms"
    return kind
