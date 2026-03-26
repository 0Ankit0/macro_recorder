from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


AvailabilityRule = Callable[["CommandContext"], bool]


@dataclass(frozen=True, slots=True)
class ShortcutDefinition:
    command_id: str
    action_label: str
    accelerator: str
    chord: frozenset[str]
    scope: str
    availability: AvailabilityRule


@dataclass(slots=True)
class CommandContext:
    permissions_ok: bool
    backend_ok: bool
    is_recording: bool
    is_playing: bool
    is_looping: bool
    has_actions: bool


SHORTCUT_DEFINITIONS: tuple[ShortcutDefinition, ...] = (
    ShortcutDefinition(
        command_id="toggle_recording",
        action_label="Toggle recording",
        accelerator="Cmd+Shift+R",
        chord=frozenset({"<cmd>", "<shift>", "r"}),
        scope="Global",
        availability=lambda ctx: ctx.permissions_ok and ctx.backend_ok and not ctx.is_playing and not ctx.is_looping,
    ),
    ShortcutDefinition(
        command_id="play_once",
        action_label="Play once",
        accelerator="Cmd+Shift+P",
        chord=frozenset({"<cmd>", "<shift>", "p"}),
        scope="Global",
        availability=lambda ctx: ctx.permissions_ok
        and ctx.backend_ok
        and (not ctx.is_recording)
        and (not ctx.is_looping)
        and ctx.has_actions,
    ),
    ShortcutDefinition(
        command_id="emergency_stop",
        action_label="Emergency stop",
        accelerator="Esc",
        chord=frozenset({"<esc>"}),
        scope="Global",
        availability=lambda _ctx: True,
    ),
)


def command_definitions_by_id() -> dict[str, ShortcutDefinition]:
    return {item.command_id: item for item in SHORTCUT_DEFINITIONS}
