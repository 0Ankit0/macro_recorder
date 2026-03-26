from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from macro_recorder.domain.models import MacroAction, MacroDocument
from macro_recorder.domain.normalize import normalize_timestamps


class StorageService:
    def load(self, path: str) -> MacroDocument:
        payload = json.loads(Path(path).read_text())
        if isinstance(payload, list):
            return self._load_legacy_actions(payload)
        if isinstance(payload, dict) and payload.get("version") == 1:
            actions = [self._validate_action(a) for a in payload.get("actions", [])]
            doc = MacroDocument(
                name=payload.get("name", "Untitled Macro"),
                actions=normalize_timestamps(actions),
                version=1,
                created_at=payload.get("created_at", MacroDocument().created_at),
                platform=payload.get("platform", "unknown"),
                screen_size=tuple(payload.get("screen_size", [0, 0])),
            )
            return doc
        raise ValueError("Unsupported macro file format")

    def save(self, path: str, document: MacroDocument) -> None:
        Path(path).write_text(json.dumps(document.to_dict(), indent=2))

    def _load_legacy_actions(self, legacy_actions: list[dict[str, Any]]) -> MacroDocument:
        mapped: list[MacroAction] = []
        for item in legacy_actions:
            t_ms = int(float(item.get("time", 0)) * 1000)
            action_type = item.get("type")
            if action_type == "mouse_move":
                mapped.append({"t_ms": t_ms, "kind": "mouse_move", "x": int(item["x"]), "y": int(item["y"])})
            elif action_type == "mouse_click":
                kind = "mouse_down" if bool(item.get("pressed")) else "mouse_up"
                button = str(item.get("button", "Button.left")).replace("Button.", "")
                mapped.append(
                    {
                        "t_ms": t_ms,
                        "kind": kind,
                        "x": int(item.get("x", 0)),
                        "y": int(item.get("y", 0)),
                        "button": button,
                    }
                )
            elif action_type == "key_press":
                mapped.append({"t_ms": t_ms, "kind": "key_down", "key": str(item.get("key", ""))})
            elif action_type == "key_release":
                mapped.append({"t_ms": t_ms, "kind": "key_up", "key": str(item.get("key", ""))})
            elif action_type == "scroll":
                mapped.append(
                    {
                        "t_ms": t_ms,
                        "kind": "scroll",
                        "x": int(item.get("x", 0)),
                        "y": int(item.get("y", 0)),
                        "dx": int(item.get("dx", 0)),
                        "dy": int(item.get("dy", 0)),
                    }
                )
        return MacroDocument(actions=normalize_timestamps(mapped))

    def _validate_action(self, action: dict[str, Any]) -> MacroAction:
        return dict(action)
