from __future__ import annotations

import ctypes
import platform
import threading
import time
from queue import Queue
from typing import Callable

from pynput import keyboard, mouse

from macro_recorder.app.commands import SHORTCUT_DEFINITIONS
from macro_recorder.app.events import AppEvent, ev
from macro_recorder.domain.models import MacroAction


def _to_key_name(key: keyboard.Key | keyboard.KeyCode | str) -> str:
    if isinstance(key, str):
        return key.lower()
    if isinstance(key, keyboard.KeyCode):
        return (key.char or "").lower()
    return str(key).lower()


def _button_name(button: mouse.Button) -> str:
    value = str(button).replace("Button.", "")
    return value if value in {"left", "right", "middle"} else "left"


def keyboard_monitoring_trusted() -> bool:
    trusted_flag = getattr(keyboard.Listener, "IS_TRUSTED", None)
    if trusted_flag is not None:
        return bool(trusted_flag)

    if platform.system() != "Darwin":
        return True

    try:
        hiservices = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        hiservices.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(hiservices.AXIsProcessTrusted())
    except Exception:
        return False


class PynputRecordingBackend:
    def __init__(self, event_queue: Queue[AppEvent]):
        self.queue = event_queue
        self._start_ts = 0.0
        self._mouse_listener: mouse.Listener | None = None
        self._running = False

    def start(self) -> None:
        self._start_ts = time.perf_counter()
        self._running = True

        def t_ms() -> int:
            return self.elapsed_ms()

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

        self._mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        self._mouse_listener.start()

    def stop(self) -> None:
        self._running = False
        if self._mouse_listener:
            self._mouse_listener.stop()

    @property
    def is_running(self) -> bool:
        return self._running

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start_ts) * 1000)


class KeyboardShortcutMonitor:
    def __init__(self, event_queue: Queue[AppEvent], recording_backend: PynputRecordingBackend):
        self.queue = event_queue
        self.recording_backend = recording_backend
        self._listener: keyboard.Listener | MacOSKeyboardListenerAdapter | None = None
        self._pressed: set[str] = set()
        self._shortcut_chords = {item.chord: item.command_id for item in SHORTCUT_DEFINITIONS}
        self._suppressed_keys: set[str] = set()

    def start(self) -> None:
        try:
            if platform.system() == "Darwin":
                self._listener = MacOSKeyboardListenerAdapter(self._on_press, self._on_release)
            else:
                self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self._listener.start()
            self.queue.put(ev("backend_ready", backend="keyboard_monitor"))
        except Exception as exc:
            self.queue.put(ev("backend_error", backend="keyboard_monitor", message=str(exc)))

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | str) -> None:
        key_name = _to_key_name(key)
        if not key_name:
            return
        self._pressed.add(key_name)
        matched = self._match_shortcut(self._pressed)
        if matched:
            self._suppressed_keys.update(matched)
            self.queue.put(ev("shortcut_triggered", command_id=self._shortcut_chords[matched]))
            return
        if self.recording_backend.is_running and key_name not in self._suppressed_keys:
            self.queue.put(ev("record_action", action={"t_ms": self.recording_backend.elapsed_ms(), "kind": "key_down", "key": key_name}))

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | str) -> None:
        key_name = _to_key_name(key)
        if not key_name:
            return
        if self.recording_backend.is_running and key_name not in self._suppressed_keys:
            self.queue.put(ev("record_action", action={"t_ms": self.recording_backend.elapsed_ms(), "kind": "key_up", "key": key_name}))
        self._pressed.discard(key_name)
        if key_name in self._suppressed_keys:
            self._suppressed_keys.discard(key_name)

    def _match_shortcut(self, pressed: set[str]) -> frozenset[str] | None:
        for chord in self._shortcut_chords:
            if chord.issubset(pressed):
                return chord
        return None


class MacOSKeyboardListenerAdapter:
    """Quartz keyboard monitor used on macOS to avoid pynput's darwin keyboard listener init path."""

    def __init__(self, on_press: Callable[[str], None], on_release: Callable[[str], None]):
        self._on_press = on_press
        self._on_release = on_release
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        import Quartz  # type: ignore

        keycode_map = {53: "<esc>", 55: "<cmd>", 54: "<cmd>", 56: "<shift>", 60: "<shift>"}

        def callback(_proxy, event_type, event, _refcon):
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            key_name = keycode_map.get(keycode)
            if key_name is None:
                chars, _ = Quartz.CGEventKeyboardGetUnicodeString(event, 4, None, None)
                key_name = (chars or "").lower()
            if not key_name:
                return event
            if event_type in (Quartz.kCGEventKeyDown, Quartz.kCGEventFlagsChanged):
                self._on_press(key_name)
            elif event_type == Quartz.kCGEventKeyUp:
                self._on_release(key_name)
            return event

        def run() -> None:
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
                | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
                | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged),
                callback,
                None,
            )
            if tap is None:
                raise RuntimeError("Unable to create macOS keyboard event tap")
            run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
            loop = Quartz.CFRunLoopGetCurrent()
            Quartz.CFRunLoopAddSource(loop, run_loop_source, Quartz.kCFRunLoopCommonModes)
            Quartz.CGEventTapEnable(tap, True)
            self._running = True
            while self._running:
                Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 0.1, False)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False


class PynputPlaybackBackend:
    def __init__(self, keyboard_controller: keyboard.Controller | None = None) -> None:
        self._mouse = mouse.Controller()
        self._keyboard = keyboard_controller or keyboard.Controller()
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
