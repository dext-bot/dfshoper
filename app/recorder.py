from __future__ import annotations

import threading
import time
from typing import List

from pynput import keyboard, mouse


class ActionRecorder:
    """Record keyboard and mouse actions using pynput."""

    def __init__(self) -> None:
        self._events: List[dict] = []
        self._lock = threading.Lock()
        self._start_time = 0.0
        self._stop_event = threading.Event()

    def record(self) -> List[dict]:
        self._events.clear()
        self._stop_event.clear()
        self._start_time = time.time()

        with mouse.Listener(on_move=self._on_move, on_click=self._on_click) as m_listener:
            with keyboard.Listener(on_press=self._on_key_press, on_release=self._on_key_release) as k_listener:
                self._stop_event.wait()
                k_listener.stop()
            m_listener.stop()
        with self._lock:
            events = list(self._events)
        return events

    def _timestamp(self) -> float:
        return time.time() - self._start_time

    def _record_event(self, event: dict) -> None:
        with self._lock:
            self._events.append(event)

    def _on_move(self, x: int, y: int) -> None:
        self._record_event({"type": "move", "position": {"x": x, "y": y}, "time": self._timestamp()})

    def _on_click(self, x: int, y: int, button, pressed: bool) -> None:
        event = {
            "type": "click",
            "position": {"x": x, "y": y},
            "button": getattr(button, "name", "left"),
            "pressed": pressed,
            "time": self._timestamp(),
        }
        self._record_event(event)

    def _on_key_press(self, key) -> None:
        name = self._get_key_name(key)
        self._record_event({"type": "keyDown", "key": name, "time": self._timestamp()})

    def _on_key_release(self, key) -> None:
        name = self._get_key_name(key)
        if name == "esc":
            self._stop_event.set()
            return False
        self._record_event({"type": "keyUp", "key": name, "time": self._timestamp()})

    @staticmethod
    def _get_key_name(key) -> str:
        if isinstance(key, keyboard.KeyCode):
            return key.char or ""
        return key.name or ""
