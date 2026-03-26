from __future__ import annotations

import threading
import time
from queue import Queue

from pynput import keyboard, mouse

from macro_recorder.app.events import AppEvent, ev
from macro_recorder.domain.models import MacroAction


HOTKEY_KEYS = {"<cmd>", "<shift>", "r", "p", "<esc>"}


def _to_key_name(key: keyboard.Key | keyboard.KeyCode) -> str:
    if isinstance(key, keyboard.KeyCode):
        return key.char or ""
    return str(key)


def _button_name(button: mouse.Button) -> str:
    value = str(button).replace("Button.", "")
    return value if value in {"left", "right", "middle"} else "left"


class PynputRecordingBackend:
    def __init__(self, event_queue: Queue[AppEvent]):
        self.queue = event_queue
        self._start_ts = 0.0
        self._mouse_listener: mouse.Listener | None = None
        self._keyboard_listener: keyboard.Listener | None = None
        self._running = False

    def start(self) -> None:
        self._start_ts = time.perf_counter()
        self._running = True

        def t_ms() -> int:
            return int((time.perf_counter() - self._start_ts) * 1000)

        def on_move(x: int, y: int) -> None:
            if self._running:
                self.queue.put(ev("record_action", action={"t_ms": t_ms(), "kind": "mouse_move", "x": x, "y": y}))

        def on_click(x: int, y: int, button: mouse.Button, pressed: bool) -> None:
            if self._running:
                self.queue.put(
                    ev(
                        "record_action",
                        action={
                            "t_ms": t_ms(),
                            "kind": "mouse_down" if pressed else "mouse_up",
                            "x": x,
                            "y": y,
                            "button": _button_name(button),
                        },
                    )
                )

        def on_scroll(x: int, y: int, dx: int, dy: int) -> None:
            if self._running:
                self.queue.put(ev("record_action", action={"t_ms": t_ms(), "kind": "scroll", "x": x, "y": y, "dx": dx, "dy": dy}))

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
            if self._running:
                name = _to_key_name(key)
                if name not in HOTKEY_KEYS:
                    self.queue.put(ev("record_action", action={"t_ms": t_ms(), "kind": "key_down", "key": name}))

        def on_release(key: keyboard.Key | keyboard.KeyCode) -> None:
            if self._running:
                name = _to_key_name(key)
                if name not in HOTKEY_KEYS:
                    self.queue.put(ev("record_action", action={"t_ms": t_ms(), "kind": "key_up", "key": name}))

        self._mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        self._keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self) -> None:
        self._running = False
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()


class PynputPlaybackBackend:
    def __init__(self) -> None:
        self._mouse = mouse.Controller()
        self._keyboard = keyboard.Controller()
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def play(self, actions: list[MacroAction], speed: float, event_queue: Queue[AppEvent]) -> None:
        self._stop.clear()

        def run() -> None:
            previous_t = 0
            for idx, action in enumerate(actions, start=1):
                if self._stop.is_set():
                    event_queue.put(ev("play_stopped"))
                    return
                delay_ms = max(0, int((action["t_ms"] - previous_t) / speed))
                time.sleep(delay_ms / 1000)
                previous_t = action["t_ms"]
                self._exec(action)
                event_queue.put(ev("play_progress", index=idx, total=len(actions)))
            event_queue.put(ev("play_done"))

        threading.Thread(target=run, daemon=True).start()

    def _exec(self, action: MacroAction) -> None:
        kind = action["kind"]
        if kind == "mouse_move":
            self._mouse.position = (action["x"], action["y"])
        elif kind == "mouse_down":
            self._mouse.position = (action["x"], action["y"])
            self._mouse.press(getattr(mouse.Button, action.get("button", "left")))
        elif kind == "mouse_up":
            self._mouse.position = (action["x"], action["y"])
            self._mouse.release(getattr(mouse.Button, action.get("button", "left")))
        elif kind == "scroll":
            self._mouse.position = (action["x"], action["y"])
            self._mouse.scroll(action.get("dx", 0), action.get("dy", 0))
        elif kind == "key_down":
            self._keyboard.press(action.get("key", ""))
        elif kind == "key_up":
            self._keyboard.release(action.get("key", ""))


def keyboard_monitoring_trusted() -> bool:
    try:
        listener = keyboard.Listener(on_press=lambda _: None)
        listener.start()
        listener.stop()
        return True
    except Exception:
        return False
