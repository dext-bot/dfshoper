from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import pyautogui
from pynput import keyboard, mouse

Coordinate = tuple[int, int]


@dataclass
class RecordedEvent:
    timestamp: float
    event_type: str
    payload: dict


@dataclass
class OperationScript:
    events: List[RecordedEvent]

    def to_dict(self) -> dict:
        return {
            "events": [
                {
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "payload": event.payload,
                }
                for event in self.events
            ]
        }

    @classmethod
    def from_path(cls, path: Path) -> "OperationScript":
        data = json.loads(path.read_text(encoding="utf-8"))
        events = [
            RecordedEvent(
                timestamp=item["timestamp"],
                event_type=item["event_type"],
                payload=item.get("payload", {}),
            )
            for item in data.get("events", [])
        ]
        return cls(events=events)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


class ActionExecutor:
    def __init__(self, sleep: Callable[[float], None] = time.sleep) -> None:
        self._sleep = sleep

    def move_and_click(self, coordinate: Coordinate, button: str = "left", duration: float = 0.1) -> None:
        pyautogui.moveTo(coordinate[0], coordinate[1], duration=duration)
        pyautogui.click(button=button)

    def execute(self, script: OperationScript) -> None:
        if not script.events:
            return
        start = script.events[0].timestamp
        for event in script.events:
            wait = max(event.timestamp - start, 0)
            self._sleep(wait)
            if event.event_type == "mouse_move":
                pyautogui.moveTo(event.payload["x"], event.payload["y"], duration=0)
            elif event.event_type == "mouse_click":
                pyautogui.click(event.payload["x"], event.payload["y"], button=event.payload.get("button", "left"))
            elif event.event_type == "keyboard":
                key = event.payload.get("key")
                if key:
                    pyautogui.press(key)
            start = event.timestamp


class ActionRecorder:
    def __init__(self) -> None:
        self._events: List[RecordedEvent] = []
        self._recording = False
        self._lock = threading.Lock()
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._start_time = 0.0

    def start(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._events.clear()
            self._recording = True
            self._start_time = time.time()
            self._mouse_listener = mouse.Listener(on_move=self._on_move, on_click=self._on_click)
            self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
            self._mouse_listener.start()
            self._keyboard_listener.start()

    def stop(self) -> OperationScript:
        with self._lock:
            self._recording = False
            if self._mouse_listener:
                self._mouse_listener.stop()
                self._mouse_listener.join()
                self._mouse_listener = None
            if self._keyboard_listener:
                self._keyboard_listener.stop()
                self._keyboard_listener.join()
                self._keyboard_listener = None
        return OperationScript(events=list(self._events))

    def _timestamp(self) -> float:
        return time.time() - self._start_time

    def _on_move(self, x: int, y: int) -> None:
        if not self._recording:
            return
        self._events.append(RecordedEvent(self._timestamp(), "mouse_move", {"x": x, "y": y}))

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if not self._recording or not pressed:
            return
        self._events.append(
            RecordedEvent(
                self._timestamp(),
                "mouse_click",
                {"x": x, "y": y, "button": button.name},
            )
        )

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if not self._recording:
            return
        self._events.append(
            RecordedEvent(
                self._timestamp(),
                "keyboard",
                {"key": getattr(key, "char", None) or getattr(key, "name", str(key))},
            )
        )


__all__ = ["ActionExecutor", "ActionRecorder", "OperationScript", "RecordedEvent"]
