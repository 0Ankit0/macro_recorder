from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import MacroAction


@dataclass(slots=True)
class MouseMoveCompressor:
    min_interval_ms: int = 25

    def compress(self, actions: Iterable[MacroAction]) -> list[MacroAction]:
        out: list[MacroAction] = []
        last_move: MacroAction | None = None

        for action in actions:
            if action["kind"] == "mouse_move":
                if last_move is not None:
                    same_pos = action.get("x") == last_move.get("x") and action.get("y") == last_move.get("y")
                    close_in_time = action["t_ms"] - last_move["t_ms"] < self.min_interval_ms
                    if same_pos or close_in_time:
                        last_move = action
                        continue
                out.append(action)
                last_move = action
                continue

            if action["kind"] in {"mouse_down", "mouse_up", "scroll"} and last_move is not None:
                if not out or out[-1] is not last_move:
                    out.append(last_move)
            out.append(action)
            if action["kind"] != "mouse_move":
                last_move = None

        return out


def normalize_timestamps(actions: Iterable[MacroAction]) -> list[MacroAction]:
    ordered = sorted(actions, key=lambda a: a["t_ms"])
    if not ordered:
        return []
    start = ordered[0]["t_ms"]
    normalized: list[MacroAction] = []
    for action in ordered:
        copied = dict(action)
        copied["t_ms"] = max(0, int(action["t_ms"] - start))
        normalized.append(copied)
    return normalized


def scale_actions(actions: Iterable[MacroAction], speed: float) -> list[MacroAction]:
    if speed <= 0:
        raise ValueError("speed must be > 0")
    scaled: list[MacroAction] = []
    for action in actions:
        copied = dict(action)
        copied["t_ms"] = int(copied["t_ms"] / speed)
        scaled.append(copied)
    return scaled
