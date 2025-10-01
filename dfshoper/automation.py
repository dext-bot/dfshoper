"""Automation helpers for executing recorded macros and clicks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence, Union

import time

import numpy as np
import pyautogui
from pynput import keyboard, mouse

from .config import Point

pyautogui.FAILSAFE = False


@dataclass
class MacroEvent:
    """Serializable macro event."""

    type: str
    args: tuple
    delay: float

    def execute(self) -> None:
        time.sleep(self.delay)
        if self.type == "move":
            x, y = self.args
            pyautogui.moveTo(x, y)
        elif self.type == "click":
            x, y, button = self.args
            pyautogui.click(x=x, y=y, button=button)
        elif self.type == "press":
            key = self.args[0]
            pyautogui.press(key)
        elif self.type == "hotkey":
            pyautogui.hotkey(*self.args)
        else:
            raise ValueError(f"Unsupported macro event type: {self.type}")

    @classmethod
    def from_dict(cls, data: dict) -> "MacroEvent":
        return cls(type=data["type"], args=tuple(data.get("args", ())), delay=float(data.get("delay", 0.0)))


class MacroRecorder:
    """Record keyboard and mouse events for later playback."""

    def __init__(self, on_complete: Optional[Callable[[List[MacroEvent]], None]] = None) -> None:
        self._start_time = time.monotonic()
        self._events: List[MacroEvent] = []
        self._on_complete = on_complete
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._events.clear()
        self._mouse_listener = mouse.Listener(on_click=self._on_click, on_move=self._on_move)
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self) -> List[MacroEvent]:
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener.join()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener.join()
        if self._on_complete:
            self._on_complete(self._events)
        return list(self._events)

    def _register_event(self, event: MacroEvent) -> None:
        self._events.append(event)

    def _elapsed(self) -> float:
        return time.monotonic() - self._start_time

    # Event callbacks -------------------------------------------------
    def _on_move(self, x: int, y: int) -> None:
        self._register_event(MacroEvent("move", (x, y), self._elapsed()))

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if pressed:
            self._register_event(MacroEvent("click", (x, y, button.name), self._elapsed()))

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        name = getattr(key, "char", None) or getattr(key, "name", None)
        if name:
            self._register_event(MacroEvent("press", (name,), self._elapsed()))


MacroInput = Union[MacroEvent, dict]


def _normalize_events(events: Iterable[MacroInput]) -> List[MacroEvent]:
    normalized: List[MacroEvent] = []
    for event in events:
        if isinstance(event, MacroEvent):
            normalized.append(event)
        elif isinstance(event, dict):
            normalized.append(MacroEvent.from_dict(event))
        else:  # pragma: no cover - defensive branch for unexpected data
            raise TypeError(f"Unsupported event type: {type(event)!r}")
    return normalized


def execute_macro(events: Sequence[MacroInput]) -> None:
    for event in _normalize_events(events):
        event.execute()


def click_point(point: Point) -> None:
    pyautogui.click(x=point.x, y=point.y)


def capture_color(point: Point, screenshot: np.ndarray) -> tuple:
    y = max(point.y, 0)
    x = max(point.x, 0)
    return tuple(int(c) for c in screenshot[y, x, :3])
