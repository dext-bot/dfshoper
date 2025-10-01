from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Tuple

import pyautogui

ActionType = Literal["click", "double_click", "right_click", "move", "press", "write", "sleep"]


@dataclass
class Action:
    type: ActionType
    params: Dict[str, float | str | Tuple[int, int]]


class Automation:
    def __init__(self) -> None:
        pyautogui.FAILSAFE = True

    def _normalize_position(self, value):
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return int(value[0]), int(value[1])
        return value

    def execute(self, action: Action) -> None:
        if action.type == "click":
            pos = self._normalize_position(action.params.get("position", (None, None)))
            if isinstance(pos, tuple):
                x, y = pos
            else:
                x = y = None
            if x is not None and y is not None:
                pyautogui.click(x=x, y=y)
            else:
                pyautogui.click()
        elif action.type == "double_click":
            pos = self._normalize_position(action.params.get("position", (None, None)))
            x, y = pos if isinstance(pos, tuple) else (None, None)
            pyautogui.doubleClick(x=x, y=y)
        elif action.type == "right_click":
            pos = self._normalize_position(action.params.get("position", (None, None)))
            x, y = pos if isinstance(pos, tuple) else (None, None)
            pyautogui.rightClick(x=x, y=y)
        elif action.type == "move":
            pos = self._normalize_position(action.params.get("position", (0, 0)))
            x, y = pos if isinstance(pos, tuple) else (0, 0)
            duration = float(action.params.get("duration", 0))
            pyautogui.moveTo(x, y, duration=duration)
        elif action.type == "press":
            key = str(action.params.get("key"))
            pyautogui.press(key)
        elif action.type == "write":
            text = str(action.params.get("text", ""))
            interval = float(action.params.get("interval", 0.0))
            pyautogui.write(text, interval=interval)
        elif action.type == "sleep":
            duration = float(action.params.get("duration", 0.0))
            time.sleep(duration)
        else:  # pragma: no cover - defensive programming
            raise ValueError(f"Unknown action type: {action.type}")

    def execute_many(self, actions: List[Action]) -> None:
        for action in actions:
            self.execute(action)


RecorderCallback = Callable[[Action], None]


class Recorder:
    def __init__(self, callback: RecorderCallback) -> None:
        self.callback = callback

    def record_click(self, x: int, y: int, button: str = "left") -> None:
        action_type: ActionType = "click"
        if button == "right":
            action_type = "right_click"
        elif button == "double":
            action_type = "double_click"
        action = Action(type=action_type, params={"position": (x, y)})
        self.callback(action)

    def record_key(self, key: str) -> None:
        action = Action(type="press", params={"key": key})
        self.callback(action)

    def record_text(self, text: str, interval: float = 0.0) -> None:
        action = Action(type="write", params={"text": text, "interval": interval})
        self.callback(action)

    def record_sleep(self, duration: float) -> None:
        action = Action(type="sleep", params={"duration": duration})
        self.callback(action)
